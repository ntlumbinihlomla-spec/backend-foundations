# Project Explained Simply

## What This Project Is

Backend Foundations is a small software project that started as CSV/report automation and is now becoming a bookkeeping dashboard.

The current business offer is:

"I build a simple client dashboard for bookkeepers and accountants that shows who owes what, which documents are missing, and what needs attention today."

## What A Client Sees

A client sees a web page or dashboard.

They can use it to view:

- clients
- suppliers
- invoices
- expenses
- overdue items
- missing receipts/documents
- reports
- exports

## What The Frontend Does

The frontend is what people see and click.

In this project, the frontend includes:

- pages
- buttons
- forms
- tables
- dashboard cards
- charts or bars
- screenshots/proof pages

Important frontend files:

- `frontend/bookkeeper.html`
- `frontend/index.html`
- `frontend/src/app.js`
- `frontend/styles/accounting.css`

Client-safe explanation:

"The frontend is the screen the bookkeeper uses to manage clients, invoices, missing documents, and reports."

## What The Backend Does

The backend is the engine behind the screen.

It handles:

- user registration
- login
- saving businesses
- saving clients
- saving suppliers
- saving invoices
- saving expenses
- uploading receipts
- creating reports
- creating PDFs
- importing bank CSV files
- matching bank transactions

Important backend files:

- `calculator/api.py`
- `calculator/accounting_api.py`
- `calculator/accounting_db.py`

Client-safe explanation:

"The backend stores the records, protects access, and generates reports and exports."

## What The Database Does

The database stores the information.

Examples:

- user accounts
- business records
- client records
- invoices
- expenses
- audit logs
- bank transactions

Local demo database:

- SQLite
- stored as a file
- good for demos and development

Deployment database:

- Postgres
- better for hosted apps
- used when clients need production hosting

Client-safe explanation:

"For the pilot I can use sanitized data locally. For production, the app should use a hosted database with proper access controls and backups."

## What Authentication Means

Authentication means proving who the user is.

In this app:

1. A user registers with email and password.
2. The backend hashes the password.
3. The user logs in.
4. The backend returns a token.
5. The frontend uses the token when requesting private data.

Client-safe explanation:

"The backend supports login and user-specific business access. For production, I would also configure secure hosting, HTTPS, and proper secrets."

## What Authorization Means

Authorization means deciding what a logged-in user can access.

In this app:

- a user belongs to one or more businesses
- the backend checks business membership
- a user cannot access another user's business records

Client-safe explanation:

"Each business is separated, so users only access records connected to their account."

## What CRUD Means

CRUD means:

- Create
- Read
- Update
- Delete

Examples:

- create an invoice
- read a list of clients
- update an expense
- delete a supplier

Client-safe explanation:

"The dashboard can add, view, edit, and remove records."

## What An API Endpoint Means

An endpoint is a backend URL that does one job.

Examples:

- `POST /accounting/auth/register` creates a user
- `GET /accounting/businesses` lists businesses
- `POST /accounting/businesses/{business_id}/invoices` creates an invoice
- `GET /accounting/businesses/{business_id}/reports/profit-loss.pdf` exports a report

Client-safe explanation:

"The app has backend routes for login, records, uploads, reports, and exports."

## What Cybersecurity Means Here

Cybersecurity is about reducing risk.

Important risks:

- storing real client data too early
- weak passwords
- exposed API keys
- missing HTTPS
- bad file uploads
- poor backups
- users seeing another user's data

What this project already has:

- hashed passwords
- bearer tokens
- per-business access checks
- sanitized demo proof pack

What production still needs:

- HTTPS
- stronger secrets handling
- backups
- file upload limits and scanning
- better logging
- privacy policy and data retention rules

Honest client-safe explanation:

"For a pilot, I recommend sanitized data. For production, I would scope secure hosting, backups, HTTPS, access controls, and data handling rules separately."

## How To Explain The MVP

Say this:

"The MVP is a simple client-control dashboard for bookkeepers. It shows overdue invoices, missing documents or receipts, and the tasks that need attention today. It can also export simple reports and work from sanitized CSV data."

Do not say:

"It is a full accounting platform."

Do not say:

"It replaces Xero, Sage, or QuickBooks."

Say:

"It can support the follow-up work around those tools."

## Your Current Job

Your job is not to become a senior engineer overnight.

Your job is to:

1. Understand the offer.
2. Sell the first pilot.
3. Learn the project piece by piece.
4. Ask for explanations until you can explain it yourself.

That is enough for now.
