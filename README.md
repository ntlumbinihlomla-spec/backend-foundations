# Backend Foundations — Python Automation & CLI Toolkit

A modular backend-style command-line toolkit focused on **automation, business data processing, and Python script fixing**.

This project is built as a production-style backend system — not a single script — and serves both as a **portfolio project** and a **real utility toolkit**.

---

##  Project Purpose

Backend Foundations is designed to:

* Build professional backend engineering habits
* Create real automation tools for business use
* Provide a foundation for custom Python utilities
* Demonstrate clean structure, testing, and CLI design
* Serve as proof-of-work for freelance and automation projects

---

##  What This Toolkit Can Do

###  Project #1: Calculator & CLI Toolkit

* Add, subtract, multiply, divide from the command line
* Defensive error handling
* Modular business-logic layer

###  Project #2: Task API Backend

* JSON REST API for task tracking
* Create, list, update, and delete tasks
* File-backed persistence using JSON storage
* Health-check endpoint for backend monitoring

###  Project #3: Workspace Audit & Reporting

* Scan a project folder and generate a consolidated audit report
* Count total files and total lines across supported text files
* Summarize CSV structure, JSON key counts, and log error totals
* Export the audit report to a text file from the CLI

###  Project #4: Financial API & Dashboard

* FastAPI upload and CSV summary endpoints
* Batch financial summaries across folders of CSV files
* Health-check endpoint for deployment monitoring
* Simple frontend dashboard for upload and summary inspection

###  System Utilities

* Display system time

###  File & Automation Tools

* Count lines in files
* Count words in files
* Count total lines across folders

###  Data & Business Tools

* JSON pretty printer
* JSON key counter
* CSV row counter
* CSV column counter
* Financial CSV summaries (sum, average, min, max)

###  Log & Audit Tools

* Scan log files and count errors

---

##  Example Usage

```bash
# Calculator
python -m calculator.app calc add 5 7

# System
python -m calculator.app time

# File tools
python -m calculator.app lines sample.txt
python -m calculator.app words sample.txt
python -m calculator.app lines-dir ./tests

# JSON tools
python -m calculator.app json pretty data.json
python -m calculator.app json keys data.json

# CSV tools
python -m calculator.app csv rows sales.csv
python -m calculator.app csv cols sales.csv

# Finance tools
python -m calculator.app finance summary sales.csv amount

# Log tools
python -m calculator.app log errors app.log

# Workspace audit project
python -m calculator.app report audit examples
python -m calculator.app report audit examples --out audit_report.txt

# Financial API
uvicorn calculator.api:app --reload

# Task API backend
python -m task_api.server --host 127.0.0.1 --port 8000
```

Task API routes:

```text
GET    /health
GET    /tasks
POST   /tasks
GET    /tasks/{id}
PATCH  /tasks/{id}
DELETE /tasks/{id}
```

Financial API routes:

```text
POST   /upload
GET    /summary
GET    /batch-summary
GET    /health
```

## Deploy To Render

This repo now includes a [render.yaml](/C:/Users/Mathiwe/backend-foundations/render.yaml) file for a simple web-service deployment.

1. Push the repo to GitHub.
2. Create a new Render Web Service from the repo.
3. Render can use the included config automatically, or you can use:

```bash
Build Command: pip install -r requirements.txt
Start Command: uvicorn calculator.api:app --host 0.0.0.0 --port $PORT
```

After deploy, open:

```text
https://your-app.onrender.com/docs
```

To point the dashboard at production, update `API_URL` in [index.html](/C:/Users/Mathiwe/backend-foundations/frontend/index.html) to your Render URL.

---

##  Testing

Automated unit tests cover the CLI, calculator logic, file tools, CSV tools, JSON tools, log tools, and finance summaries.

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

GitHub Actions also runs the full test suite on every push to `main` and on pull requests.

---

##  Project Structure

```
backend-foundations/
├── calculator/
│   ├── app.py
│   ├── core.py
│   ├── operations.py
│   ├── file_tools.py
│   ├── json_tools.py
│   ├── csv_tools.py
│   ├── finance_tools.py
│   ├── log_tools.py
│   └── utils.py
├── tests/
├── examples/
├── logs/
└── README.md
```

---

##  Demo Scenarios

* Sales CSV → instant financial summary
* Folder → total file audit
* Log file → error report
* JSON → clean formatted output
* Broken script → fixed backend logic
* Project folder → audit summary report

Sample files are available in the `/examples` folder.

---

##  Services I Offer

I build custom Python automation tools and fix broken scripts, especially for business and data workflows.

Examples of what I can help with:

* Fixing Python errors and exceptions
* Automating CSV and Excel reports
* Building custom command-line tools
* Cleaning and restructuring Python projects
* Financial data processing
* Internal business utilities
## Demo

Example financial report generation:

```bash
python -m calculator.app finance summary examples/sales_demo.csv amount
```

Example output:

```text
=============================================
        SALES SUMMARY REPORT
=============================================
Transactions : 4
Total Revenue: R790.00
Average Sale : R197.50
Highest Sale : R330.00
Lowest Sale  : R90.00
=============================================
```
---

##  Need Something Similar?

If you need a custom automation script, backend utility, or help fixing a Python program, feel free to reach out.

This project is actively developed and extended.

---

##  Long-Term Vision

This toolkit is evolving into a full **backend automation framework** supporting:

* Business process automation
* Financial data systems
* Internal company tooling
* Custom backend services

---

##  License

MIT License
