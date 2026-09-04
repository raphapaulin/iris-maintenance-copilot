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
quoted. Live vector search has not yet been re-validated after this correction.

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

### Live-validation status and uncertainties

The previously corrected vector layer is now reported by the project owner as
live-validated against IRIS. This process did not have `IRIS_PASSWORD`, so it
could not create or inspect the iFind index, execute lexical SQL, verify index
repeat safety, or run hybrid retrieval against IRIS. No live hybrid results are
claimed. Any IRIS-specific runtime error from index creation, `%FIND`, or
`%iFind.Rank` must be captured and corrected during credentialed re-validation.

Current IRIS documentation uses `%ID %FIND search_index(...)` for
`%iFind.Index.Basic`; deprecated iFind Semantic and Analytic index types were
not used.
