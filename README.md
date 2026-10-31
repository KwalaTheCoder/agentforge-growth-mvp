# AgentForge Growth MVP

A local-first growth operations workspace for researching opportunities, qualifying leads, reviewing evidence, drafting proposals, and tracking follow-ups from a Streamlit dashboard.

AgentForge combines public-source research, a local SQLite CRM, transparent prioritization rules, and optional local Ollama-assisted drafting. High-impact actions remain human-controlled: public signals are never treated as proof of buying intent, and the application does not authorize outreach automatically.

## Highlights

- Discover and review public company and project signals
- Research GitHub organizations and official websites with bounded, read-only workflows
- Check evidence freshness, relevance, and opportunity quality
- Qualify leads through explicit verification gates
- Generate proposal drafts with an optional local Ollama model
- Track pipeline stages, follow-ups, daily operations, and conversion snapshots
- Keep operational data local in SQLite
- Run release, backup, and security checks from the command line

## Demo

[**Watch AgentForge in Action — GitHub Release Demo**](https://github.com/KwalaTheCoder/agentforge-growth-mvp/releases/tag/demo-v1)

This is an illustrative product walkthrough, not a recording of the live application.

## Tech stack

- Python 3
- Streamlit
- SQLite
- Requests
- Optional: Ollama for local draft generation
- Optional: Gmail API dependencies for reviewed delivery workflows

## Quick start

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run AgentForge_Hub.py --server.address 127.0.0.1
```

Open the local URL shown by Streamlit. The project is configured to bind to `127.0.0.1` by default.

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run AgentForge_Hub.py --server.address 127.0.0.1
```

## Optional integrations

For Gmail-related workflows, install the additional packages:

```bash
python -m pip install -r requirements_gmail.txt
```

Keep OAuth client files and generated tokens local. They are excluded by `.gitignore` and must never be committed.

Ollama-assisted features expect a locally running Ollama service and a compatible model. The core research and CRM workflows do not require Ollama.

## Tests and checks

Run the automated suite:

```bash
python -m unittest discover -s tests -v
```

Run the read-only release checks:

```bash
python -m release_tools.final_integration audit
python -m release_tools.security_audit
python -m release_tools.maintenance doctor
```

## Data and security

The repository intentionally excludes:

- SQLite databases and their journal files
- CRM and operations backups
- OAuth credentials and tokens
- Streamlit secrets
- Local caches and virtual environments
- Historical release archives and test logs

Before contacting anyone, independently verify the buyer, the request, payment terms, and the permitted contact channel. Scores and classifications in this project are research aids—not proof of commercial intent, authorization, or factual accuracy.

## Project structure

```text
AgentForge_Hub.py          Main Streamlit launcher
pages/                     Streamlit workflow pages
release_tools/             Maintenance, backup, and security checks
tests/                     Automated test suite
*_research.py              Public-source research modules
*_qualification.py         Verification and qualification logic
*_pipeline.py              Pipeline and operational workflows
```

## Status

This is an MVP intended for local, human-reviewed use. It is not a hosted outreach service, a source of verified buyer intent, or a substitute for legal, privacy, or platform-policy review.
