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
