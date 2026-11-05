# CLI Explained Simply

CLI means Command Line Interface.

It is a way to control software by typing commands in a terminal instead of clicking buttons.

## Simple Example

This is a command:

```bash
python -m pytest tests
```

It means:

- run Python
- run the pytest testing tool
- test the `tests` folder

## CLI vs UI vs API

UI:

- what humans click
- examples: buttons, forms, dashboards

API:

- how software talks to software
- examples: `/accounting/auth/login`, `/accounting/businesses`

CLI:

- how humans or scripts control software using text commands
- examples: `git status`, `uvicorn calculator.api:app`, `python tools/generate_bookkeeper_evidence.py`

## Why Backend Developers Like CLIs

CLIs are useful because they are:

- fast
- scriptable
- easy to automate
- good for servers
- good for repeatable workflows

That is why serious backend tools often have CLIs:

- Git
- Docker
- AWS CLI
- Terraform
- Kubernetes `kubectl`

## Commands In This Project

Run tests:

```bash
python -m pytest tests
```

Start the backend API:

```bash
uvicorn calculator.api:app --reload
```

Generate bookkeeper proof evidence:

```bash
python tools/generate_bookkeeper_evidence.py
```

Run the old calculator CLI:

```bash
python -m calculator.app --help
```

## What A Command Is Made Of

Example:

```bash
uvicorn calculator.api:app --host 127.0.0.1 --port 8000
```

Parts:

- `uvicorn` is the program
- `calculator.api:app` is the app to run
- `--host 127.0.0.1` is a flag saying where to run it
- `--port 8000` is a flag saying which port to use

## Why A CLI Matters For Our Future

Right now this project has:

- frontend pages
- backend API
- evidence generator script

In the future, a CLI could let a bookkeeper or developer run commands like:

```bash
ledgerlite import-bank bank.csv --business demo
ledgerlite generate-report --type cash-flow
ledgerlite find-overdue --days 14
ledgerlite proof-pack --client demo
```

That would make the tool more powerful because it could be automated.

## Client-Safe Explanation

If a client asks what a CLI is, say:

"A CLI is a text-based way to run actions. It is useful for automating repeatable backend tasks like imports, reports, tests, and deployments."

## Your First CLI Practice

Open a terminal in this project and run:

```bash
python tools/generate_bookkeeper_evidence.py
```

If it works, it creates files in the `evidence/` folder.

That means you used a CLI command to make proof assets from the backend.
