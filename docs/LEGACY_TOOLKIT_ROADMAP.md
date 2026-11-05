# Legacy Toolkit Roadmap

This document turns the pasted "Backend Dev Legacy Toolkit" idea into a practical path for this project.

## The Big Lesson

Do not try to become wealthy by building a random CRUD app.

CRUD means create, read, update, and delete records. CRUD is useful, but it is easy to copy.

Long-term wealth comes from owning a layer that affects:

- money
- time
- trust
- decisions

Our current bookkeeper dashboard can become valuable because it touches all four.

## Where This Project Fits

Current offer:

"A simple client dashboard for bookkeepers and accountants that shows who owes what, which documents are missing, and what needs attention today."

This is the money-now offer.

Long-term direction:

"A financial operations toolkit for small firms that turns invoices, documents, reports, audit logs, and bank transactions into trusted workflows."

That is the legacy direction.

## Do Not Jump Too Far Yet

Do not start by trying to build a huge "financial nervous system."

Start with the painful, sellable workflow:

1. Bookkeepers chase clients.
2. Clients miss receipts and documents.
3. Invoices become overdue.
4. Reports are messy.
5. Bank CSVs need matching.
6. Everyone needs proof of what happened.

That is where the first money is.

## The Four Legacy Layers

### 1. Money Layer

What it means:

- invoices
- expenses
- VAT/tax
- bank transactions
- payment status
- reconciliation

Current project pieces:

- invoices
- expenses
- dashboard totals
- report exports
- bank CSV import
- reconciliation matching

Future primitives:

- double-entry ledger
- account balances
- transaction rules
- audit-safe corrections
- payment status history

### 2. Time Layer

What it means:

- due dates
- overdue workflows
- recurring client tasks
- reminders
- monthly close process
- follow-up queues

Current project pieces:

- due dates
- overdue invoices
- daily attention list
- missing document flags

Future primitives:

- recurring workflows
- task states
- automatic reminders
- escalation rules
- month-end close checklist

### 3. Trust Layer

What it means:

- audit trail
- who changed what
- when records changed
- proof that reports are based on records
- tamper-evident activity

Current project pieces:

- audit logs
- created/edited/deleted records
- timestamps
- user/business access checks

Future primitives:

- immutable event log
- report version history
- record approval flow
- client-safe proof pack generation
- tamper-evident hashes

### 4. Decision Layer

What it means:

- what needs attention first
- which clients are risky
- which invoices are urgent
- which missing records block reports
- which bank transactions need review

Current project pieces:

- client health score
- overdue invoice count
- missing receipt flags
- bank transaction match confidence

Future primitives:

- explainable client risk score
- rule-based prioritisation
- workflow recommendations
- backtesting on historical client data
- decision history

## The Correct Build Order

### Phase 1: Sellable Dashboard

Goal:

Close paid pilots.

Build:

- simple dashboard
- invoices
- expenses
- missing document flags
- report exports
- bank CSV import
- proof PDF

This is where we are now.

### Phase 2: Workflow Engine

Goal:

Make it useful every week.

Build:

- tasks
- reminders
- statuses
- recurring monthly workflows
- "attention today" queue

This turns the dashboard into an operating tool.

### Phase 3: Trust And Audit

Goal:

Make it safe for accountants.

Build:

- stronger audit trail
- approval states
- report versioning
- immutable activity log
- user roles

This makes it harder to replace.

### Phase 4: Financial Primitives

Goal:

Move toward real financial infrastructure.

Build:

- ledger entries
- account categories
- reconciliation rules
- correction/reversal flows
- audit-safe transaction history

This is where the "financial nervous system" starts.

### Phase 5: Decision Infrastructure

Goal:

Make the app smarter and more defensible.

Build:

- client health scoring
- explainable rules
- risk flags
- workflow simulations
- close-readiness scoring

This is where data and usage make the product stronger.

## What To Say To Clients Now

Say:

"I build a simple client dashboard for bookkeepers. It helps track overdue invoices, missing receipts, missing documents, and what needs attention today."

Do not say:

"I am building financial nervous system infrastructure."

That is too abstract for a first buyer.

## What To Learn First

Learn in this order:

1. Frontend basics
2. Backend endpoints
3. Database tables
4. Authentication and authorization
5. Audit logs
6. File uploads
7. CSV import
8. PDF exports
9. Workflow states
10. Security hardening

## The Strategic Decision

The category we should choose is:

Money + Time + Trust for bookkeepers/accountants.

That is better than chasing a brand-new abstract toolkit today.

The route is:

Bookkeeper dashboard -> client workflow system -> audit-safe financial operations toolkit.

First we sell.

Then we deepen the infrastructure.
