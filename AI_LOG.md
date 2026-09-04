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

    