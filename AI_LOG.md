\# AI Development Log



This document records how AI agents were used during the development of IRIS Maintenance Copilot, including prompts, decisions, validation steps, mistakes, and corrections.



\## 2026-08-31 — Environment bootstrap



\### Goal

Prepare a local InterSystems IRIS development environment and establish the first Python-to-IRIS connection.



\### AI assistance

ChatGPT was used to guide:

\- InterSystems account and Open Exchange setup

\- GitHub repository initialization

\- WSL 2 and Docker Desktop setup

\- InterSystems IRIS Community Edition deployment

\- Creation of the MAINTENANCE namespace and database



\### Validation strategy

AI instructions were validated through:

\- actual command execution;

\- InterSystems official documentation;

\- Docker runtime tests;

\- direct inspection in the IRIS Management Portal.



\### AI error identified

The AI initially suggested that an icon in the IRIS database directory selector could create a new directory. Manual inspection showed that this assumption was incorrect.



\### Correction

Instead of relying on the UI icon, the database directory was explicitly entered as:



`/usr/irissys/mgr/maintenance`



IRIS then handled the database directory creation correctly.



\### Lesson

AI-generated infrastructure instructions must be validated against the actual product interface and official documentation before execution.

### Result

The environment bootstrap was successfully completed.

A Python 3.13 application running on Windows successfully connected to the
InterSystems IRIS Community Edition container through port 1972 and executed
SQL against the MAINTENANCE namespace.

Successful output:

```text
Connected to InterSystems IRIS successfully!
Namespace: MAINTENANCE
IRIS timestamp: 2026-09-02 02:28:10
```

## 2026-09-04 — First structured operational-data layer

### Goal

Add a small, reusable SQL data layer for equipment and synthetic maintenance
events without introducing an ORM, web framework, or AI/RAG functionality.

### AI assistance

AI was asked to add environment-based IRIS connection handling, idempotent
table initialization, repeatable synthetic seed data, and readable validation
queries including an equipment-to-maintenance-event join.

### Files changed

- `src/__init__.py`
- `src/iris_connection.py`
- `src/init_db.py`
- `src/seed_data.py`
- `src/validate_data.py`
- `AI_LOG.md`

### Validation executed

- Python bytecode compilation of every module under `src/`: passed.
- The initialization, seed, and validation modules were each run without
  `IRIS_PASSWORD`; each failed as intended with the explicit missing-password
  message before attempting a connection.
- Initialization with a temporary password value and a non-numeric
  `IRIS_PORT` failed with the intended port-validation message.
- `git diff --check`: passed.

### Uncertainty and limitation

The IRIS container was running, but `IRIS_PASSWORD` was not available in the
process environment. Table creation, seeding, repeat execution, and live JOIN
results could therefore not be tested in this iteration. The SQL catalog,
`TIMESTAMP`, `VARCHAR`, primary-key, and foreign-key approach was checked
against the InterSystems IRIS SQL documentation, but still requires the live
credentialed validation commands documented in the handoff.

## 2026-09-04 — First semantic retrieval layer

### Goal

Add semantic retrieval over a small synthetic industrial-maintenance knowledge
base, with vector storage and cosine similarity calculation performed by
InterSystems IRIS.

### Embedding and retrieval design

The required `sentence-transformers/all-MiniLM-L6-v2` model was selected as a
compact general-purpose sentence embedding model suitable for this first
retrieval proof. It produces 384-dimensional embeddings and is loaded once per
Python process through a cached helper.

The external Python application serializes each real model embedding as a
comma-separated string because the DB-API transports vector input as text.
IRIS converts that parameter with `TO_VECTOR(?, FLOAT, 384)` and stores it in a
native `VECTOR(FLOAT, 384)` column. Query embeddings use the same conversion,
and IRIS computes and orders similarity with `VECTOR_COSINE(... ) DESC`.
Cosine similarity is not calculated in Python.

### Files changed

- `requirements.txt`
- `src/init_db.py`
- `src/embedding_model.py`
- `src/knowledge_base.py`
- `src/ingest_knowledge.py`
- `src/semantic_search.py`
- `src/validate_vector_search.py`
- `AI_LOG.md`

### Commands and validation actually executed

- `python -m pip install -r requirements.txt`: passed; installed
  `sentence-transformers==6.0.1` and its dependencies.
- `python -m compileall -q src`: passed.
- Loaded `sentence-transformers/all-MiniLM-L6-v2` and embedded two real text
  samples: passed with shape `(2, 384)` and finite numeric values.
- Called the model helper twice in one process: passed; the same cached model
  object was returned.
- Checked the 12 chunks for unique IDs and required content, and checked that
  vector serialization retained all 384 values: passed.
- `python -m pip check`: passed with no broken requirements.
- `python -m src.init_db`, `python -m src.ingest_knowledge`, and
  `python -m src.validate_vector_search`: each stopped with the expected
  `IRIS_PASSWORD environment variable is required` error.
- `git diff --check`: passed.

### Failures, warnings, and corrections

The model download emitted a non-fatal Hugging Face warning that Windows could
not use symlinks in its external user cache; model loading and embedding still
succeeded. No project setting was added to suppress the warning.

`IRIS_PASSWORD` was not present in this process. Consequently, creation of
`SQLUser.DocumentChunk`, vector ingestion, repeat-safe ingestion, execution of
`VECTOR_COSINE`, returned rankings, and semantic relevance assertions were not
live-tested. Live IRIS vector search is therefore **not yet validated** by this
AI session and must not be reported as successful until the credentialed
commands pass.

### Live IRIS compatibility correction

Subsequent live validation exposed SQLCODE `-1`: IRIS expected an identifier
but found the reserved word `SECTION`. Because `section` was used as a column
name, creation of `SQLUser.DocumentChunk` failed. The ingestion and semantic
search failures were downstream consequences of that table not existing.

The column and all directly related SQL and Python references were renamed to
the unambiguous identifier `document_section`; the reserved identifier was not
quoted. Later live validation confirmed table creation, embedding ingestion,
`TO_VECTOR`, and `VECTOR_COSINE` retrieval after this correction.

## 2026-09-04 — Hybrid retrieval with IRIS SQL Search and RRF

### Goal and rationale

Add lexical retrieval alongside the live-validated semantic vector retrieval.
Semantic search helps retrieve conceptually related wording, while lexical
search rewards exact maintenance terms such as `cavitation` and `misalignment`.
Hybrid retrieval combines their complementary ranked evidence without adding
an answer-generating LLM.

### Lexical retrieval in IRIS

Initialization now checks `INFORMATION_SCHEMA.INDEXES` before creating
`DocumentChunkContentIdx` on `SQLUser.DocumentChunk.content` as a supported
`%iFind.Index.Basic` index with English language processing and lowercase
normalization. Existing tables, chunks, and embeddings are left unchanged.

The external application deterministically extracts lowercase alphanumeric or
hyphenated terms, removes a small fixed stopword set, removes duplicates, and
joins the terms with `OR`. IRIS performs candidate matching with
`%ID %FIND search_index(...)` and calculates lexical TF-IDF rank using
`%iFind.Rank`. The table's generated IRIS class name is read from
`INFORMATION_SCHEMA.TABLES` rather than assumed.

### Reciprocal Rank Fusion

Python combines the two rankings using
`RRF_score(d) = sum(1 / (k + rank_i(d)))`, with default `k = 60`. RRF was used
instead of adding raw cosine and TF-IDF values because those scores have
different, non-comparable scales. Vector similarity and lexical retrieval both
execute inside IRIS; only rank fusion executes in Python.

### Files changed

- `src/init_db.py`
- `src/semantic_search.py`
- `src/lexical_search.py`
- `src/hybrid_search.py`
- `src/validate_hybrid_search.py`
- `AI_LOG.md`

### Validation executed

- `python -m compileall -q src`: passed.
- Deterministic preparation of the first validation query produced
  `high OR vibration OR motor OR drive-end OR bearing`: passed.
- A focused RRF check verified that a document at semantic rank 1 and lexical
  rank 2 receives `1/61 + 1/62`: passed.
- `python -m src.init_db`: stopped at the required missing-password guard.
- `python -m src.validate_hybrid_search`: loaded the real embedding model, then
  stopped at the required missing-password guard.
- `git diff --check`: passed.

### Live validation backfill

The project owner subsequently completed live validation against IRIS. The
`DocumentChunkContentIdx` iFind index was created successfully. All five
validation queries executed successfully, and the hybrid relevance assertions
passed. A second initialization run skipped the existing `Equipment`,
`MaintenanceEvent`, and `DocumentChunk` tables and the existing lexical index,
then completed successfully, confirming repeat-safe index initialization.

Observed hybrid leaders were the motor drive-end bearing and motor vibration
chunks for the bearing query; centrifugal pump cavitation and pump suction-side
chunks for both pump queries; fan blade buildup and fan rotor imbalance chunks
for the fan query; and shaft/coupling misalignment for the coupling query.

### Technical observation

RRF appropriately favors documents present in both rankings, but cross-signal
agreement does not guarantee contextual relevance. For the motor drive-end
bearing query, `Fan blade buildup and imbalance` reached hybrid rank 3 because
it appeared in both candidate lists. This was accepted as a rank-fusion
trade-off, not treated as an implementation failure, and should be considered
when curating evidence for later generation.

Current IRIS documentation uses `%ID %FIND search_index(...)` for
`%iFind.Index.Basic`; deprecated iFind Semantic and Analytic index types were
not used.

## 2026-09-04 — First grounded RAG generation layer

### Goal

Add structured maintenance assessment generation grounded in a small curated
set of evidence returned by the existing IRIS hybrid retrieval layer.

### AI task

The coding agent was instructed to select and format retrieved evidence,
isolate one OpenAI-compatible HTTP provider behind an interface, require JSON
output with evidence citations, validate generated output in Python, provide a
readable CLI, and demonstrate safe behavior for an unsupported `ZX-991` code.

### Design decisions

- `hybrid_search` remains the only retrieval entry point used by generation;
  semantic search, iFind lexical search, and RRF were not reimplemented.
- Evidence selection defaults to three chunks and retains chunk metadata,
  retrieval scores, and both source ranks under stable `E1`, `E2`, and `E3`
  identifiers.
- Context formatting is deterministic. Every prompt states that the synthetic,
  general evidence may be incomplete.
- Weak evidence is flagged without a numeric score threshold when no selected
  item has both retrieval signals, no evidence exists, or a code-like query
  identifier such as `ZX-991` is absent from retrieved content. Missing
  identifiers are explicitly listed with an instruction not to infer meaning.
- Core generation depends on an `LLMProvider` protocol. The single concrete
  provider uses the OpenAI-compatible `/chat/completions` HTTP shape through
  Python's standard library, keeping vendor transport isolated and avoiding a
  new framework dependency.
- `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` are required. No credential is
  defaulted, printed, or logged. Provider configuration is checked before
  retrieval when generation is requested; retrieval modules remain usable
  independently without LLM configuration.
- The system prompt permits only evidence-grounded technical claims, requires
  citations for every possible cause and recommended check, prohibits invented
  specifications, measurements, inspections, and confirmed failures, and
  requests JSON only without hidden reasoning.
- Python rejects invalid JSON, missing fields, invalid coverage values,
  malformed field types, empty citations, and citations to evidence IDs not in
  the supplied context. It never adds missing citations automatically.

### Files changed

- `src/evidence_context.py`
- `src/llm_provider.py`
- `src/rag_service.py`
- `src/rag_cli.py`
- `src/validate_rag.py`
- `AI_LOG.md`

### Validation performed

- `python -m compileall -q src`: passed.
- `python -m src.validate_rag --components-only`: passed using explicitly
  controlled fixtures. It verified evidence IDs and formatting, detection of
  unsupported `ZX-991`, acceptance of a valid low-coverage JSON object, and
  rejection of invalid JSON, missing fields, invalid coverage, unknown
  evidence IDs, and empty evidence citations.
- `python -m src.rag_cli --help`: passed.
- `python -m src.rag_cli` without LLM configuration: after the correction
  below, failed clearly with `LLM_BASE_URL environment variable is required`.
- `python -m src.validate_rag` without LLM configuration: failed clearly on
  the first case with the same required-variable message; no live result was
  produced.
- A focused prompt-contract check confirmed the required grounding rules and
  all seven top-level response fields are present: passed.
- `git diff --check`: passed.

### Failures and corrections

The first missing-configuration CLI test attempted hybrid retrieval before
validating LLM configuration. It loaded the embedding model and then failed on
the missing `IRIS_PASSWORD`, obscuring the absent provider configuration. The
provider is now constructed and validated first. Repeating the test produced
the intended `LLM_BASE_URL environment variable is required` error without
accessing IRIS.

### Limitations / observations

No `IRIS_PASSWORD` or LLM provider variables were available to this coding
session. The controlled response fixture tests only context and validation
logic; it is not presented as model output. Static validation cannot prove that
a provider follows the grounding prompt. Unsupported-identifier detection is a
small transparent safeguard, not a general factuality detector, and numeric
retrieval thresholds remain intentionally unintroduced pending empirical
evaluation.

### Live LLM validation attempt

The project owner configured the Gemini OpenAI-compatible endpoint with model
`gemini-3.8-flash`. An initial environment-variable setup issue was detected
because the API-key value had not loaded correctly. After correcting the
environment variable, a minimal direct `/chat/completions` request succeeded
and returned `{"ok":true}`. This confirmed the API key, endpoint, model, and
OpenAI-compatible request format.

The full `python -m src.validate_rag` run then reached its first generation
call but failed with HTTP 503. No grounded RAG response was accepted as
live-validated.

### Result

- Implemented: yes.
- Locally validated: yes, for compilation, context construction, schema and
  citation enforcement, CLI configuration failure, and diff integrity.
- Live IRIS validated: the pre-existing retrieval layer is live-validated per
  the project owner; this new RAG orchestration was not rerun against IRIS in
  this coding session.
- Live LLM validated: no; provider connectivity was proven by the direct
  request, but full grounded generation stopped on HTTP 503.

## 2026-09-04 — LLM provider retry reliability

### Goal

Improve the reliability and diagnostics of the existing OpenAI-compatible HTTP
provider when a configured service is temporarily unavailable or overloaded.

### AI task

The coding agent was instructed to add bounded exponential backoff for HTTP
429, 500, 502, 503, and 504 responses; expose concise retry notices; preserve
safe provider error details; prevent credential disclosure; and add controlled
tests without changing retrieval, prompts, schemas, IRIS code, or UI.

### Design decisions

- Retry settings are module-level defaults and constructor options: three
  attempts total and an initial two-second delay.
- Delays grow exponentially, producing two seconds before attempt 2 and four
  seconds before attempt 3. There is no indefinite retry loop.
- HTTP 400, 401, 403, and all other statuses outside the explicit transient set
  fail immediately.
- A retry notice contains only status, delay, and attempt count. It does not
  include credentials, prompts, headers, or request payloads.
- Final HTTP errors include status, attempts made, and at most 300 characters
  of concise provider detail. JSON `error.message` is preferred when present.
  The configured API key and bearer authorization text are redacted.
- The URL opener, sleep function, and retry notifier are injectable so retry
  behavior can be tested deterministically without network calls or delays.

### Files changed

- `src/llm_provider.py`
- `src/validate_llm_provider.py`
- `AI_LOG.md`

### Validation performed

- `python -m compileall -q src`: passed.
- `python -m src.validate_llm_provider`: passed all four controlled cases:
  HTTP 503 followed by success, three repeated HTTP 503 responses, immediate
  HTTP 400 failure, and credential redaction from final errors.
- The repeated-503 fixture verified exactly three calls and delays of two and
  four seconds; no real waiting was performed in the controlled test.
- `python -m src.validate_rag --components-only`: passed, preserving the
  existing context, schema, and citation checks.
- `git diff --check`: passed.

### Failures and corrections

Live validation had first exposed an incorrectly loaded API-key environment
variable; correcting it allowed the minimal Gemini request to succeed. Full
grounded-RAG validation then encountered the transient HTTP 503 that motivated
this change. No implementation failure occurred during the controlled retry
tests performed after the provider update.

### Limitations / observations

Retrying improves resilience to temporary overload but cannot guarantee
provider availability. Three exhausted transient attempts still fail clearly.
Network errors outside the specified HTTP-status policy remain immediate
failures. Provider error text is untrusted and therefore truncated and
credential-redacted before display.

### Result

- Implemented: yes.
- Locally validated: yes, including bounded retries, non-retry behavior,
  diagnostics, redaction, and the preserved RAG component suite.
- Live IRIS validated: unchanged; retrieval was outside this correction.
- Live LLM validated: no; the Gemini-backed full validation must be rerun after
  this correction.

## 2026-09-04 — Grounded RAG live-validation reconciliation

### Goal

Reconcile the project record with the completed end-to-end grounded-RAG and
provider-retry validation, and strengthen generic regression coverage for
unsupported code-like identifiers.

### AI task

The coding agent was instructed to record the real live results without
redesigning the validated retrieval or generation layers, and to make only a
small deterministic regression-test improvement if directly justified.

### Design decisions

- The successful maintenance responses are recorded by observed grounding
  behavior rather than by reproducing or inventing full model output.
- Live provider behavior is distinguished from controlled retry fixtures.
- The existing generic unsupported-identifier implementation was unchanged.
  Its controlled test now uses multiple unrelated code-like identifiers rather
  than depending only on the live `ZX-991` adversarial example.

### Files changed

- `src/validate_rag.py`
- `AI_LOG.md`

### Validation performed

The project owner reported three successful live maintenance cases through the
complete pipeline: IRIS hybrid retrieval, evidence selection, Gemini 3.8 Flash,
structured JSON parsing, grounding validation, and evidence-citation
validation.

- Motor drive-end bearing query: returned multiple possible causes without
  claiming confirmed failure; recommended checks cited E1/E2/E3; coverage was
  medium; limitations identified missing field measurements, vibration
  spectrum, and inspection data; no fabricated measurement or manufacturer
  specification was observed.
- Cooling-water pump query: associated crackling-gravel noise and unstable
  discharge pressure with possible cavitation and suction-side issues; required
  physical verification before determining root cause; checks cited supplied
  evidence; coverage was medium; no confirmed diagnosis was claimed.
- Exhaust-fan query: associated uneven blade buildup with possible rotor
  imbalance; cleaning and inspection checks cited supplied evidence; coverage
  was high; physical verification remained explicit.

The live `ZX-991` adversarial test also passed. The retrieval note identified
the code as absent from all supplied evidence and instructed the model not to
infer its meaning. The response stated that its meaning could not be inferred
and the evidence was insufficient, produced no likely causes or recommended
technical checks, assigned low evidence coverage, and explicitly listed the
missing code knowledge as a limitation.

Live retry validation observed HTTP 503 followed by a two-second wait and a
successful second request. An earlier live run observed HTTP 503, a two-second
wait, another HTTP 503, a four-second wait, a third HTTP 503, and controlled
failure after three total attempts. Provider diagnostics exposed only the
concise temporary-high-demand message; no credential was exposed.

Local regression commands executed in this reconciliation:

- `python -m compileall -q src`: passed.
- `python -m src.validate_rag --components-only`: passed after testing two
  unrelated absent code-like identifiers.
- `python -m src.validate_llm_provider`: passed all existing controlled retry,
  bounded-failure, immediate-400, and credential-redaction cases.
- `git diff --check`: passed.

### Failures and corrections

The first full adversarial live run exhausted all three attempts because Gemini
returned HTTP 503 each time; it produced no accepted grounded response. A later
single-query CLI run received HTTP 503 on its first request, then recovered on
the built-in retry after two seconds and completed successfully. No application
code correction was required during this reconciliation.

### Limitations / observations

Bounded retries reduce the impact of transient overload but do not guarantee
provider availability, as demonstrated by both exhausted and recovered live
runs. The knowledge base remains synthetic and intentionally does not define
`ZX-991`. The new local identifier checks validate the deterministic safeguard,
not the behavior of a live model.

### Result

- Implemented: the grounded-RAG and bounded-retry layers remain unchanged;
  generic unsupported-identifier regression coverage was strengthened.
- Locally validated: yes, for compilation, component grounding checks,
  controlled provider retries, bounded failure, and credential redaction.
- Live IRIS validated: yes, as part of the reported full hybrid retrieval path.
- Live LLM validated: yes. Three maintenance cases and the adversarial
  `ZX-991` case completed end-to-end with structured output and valid evidence
  citations. Grounded RAG is now live-validated end-to-end.
