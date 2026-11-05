import json
import os
import shutil
import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_DIR = ROOT / "evidence"
DEMO_DB = EVIDENCE_DIR / "bookkeeper-demo.sqlite3"

sys.path.insert(0, str(ROOT))


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def api_call(response):
    if response.status_code >= 400:
        raise RuntimeError(f"{response.request.method} {response.request.url} failed: {response.text}")
    return response


def save_response(path, response):
    api_call(response)
    path.write_bytes(response.content)


def generate_proof_pdf(path, dashboard, attention_rows):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=34, leftMargin=34, topMargin=32, bottomMargin=32)
    story = [
        Paragraph("Bookkeeper Client Ops Dashboard", styles["Title"]),
        Paragraph(
            "Proof pack for outreach: who owes what, which documents are missing, and what needs attention today.",
            styles["BodyText"],
        ),
        Spacer(1, 14),
    ]

    metric_rows = [
        ["Metric", "Demo Result"],
        ["Total paid income", f"R{dashboard['total_income']:,.2f}"],
        ["Outstanding invoices", f"R{dashboard['outstanding_invoices']:,.2f}"],
        ["Overdue invoices", f"{dashboard['overdue_invoices']} invoices worth R{dashboard['overdue_invoice_total']:,.2f}"],
        ["Missing receipt/doc items", str(sum(1 for row in attention_rows if 'missing' in row[1].lower()))],
        ["Estimated VAT/tax", f"R{dashboard['tax_estimate']:,.2f}"],
    ]
    story.append(styled_table(metric_rows, header_color="#0b6b58"))
    story.append(Spacer(1, 16))
    story.append(Paragraph("What The Bookkeeper Sees Today", styles["Heading2"]))
    story.append(styled_table([["Client/Supplier", "Issue", "Amount", "Next Action"], *attention_rows], header_color="#235c7a"))
    story.append(Spacer(1, 16))

    screenshots = [
        ROOT / "frontend" / "assets" / "fiverr-dashboard-screenshot.png",
        ROOT / "frontend" / "assets" / "fiverr-report-screenshot.png",
    ]
    for screenshot in screenshots:
        if screenshot.exists():
            story.append(Image(str(screenshot), width=480, height=260))
            story.append(Spacer(1, 10))

    story.append(Paragraph("MVP Scope", styles["Heading2"]))
    story.append(
        Paragraph(
            "The first sellable version stays narrow: client list, invoice status, missing document flags, "
            "daily attention list, exports, and bank CSV reconciliation.",
            styles["BodyText"],
        )
    )
    doc.build(story)


def styled_table(rows, header_color):
    table = Table(rows, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8e0e6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7faf9")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def generate_html(path, dashboard, attention_rows):
    rows = "\n".join(
        f"<tr><td>{client}</td><td>{issue}</td><td>{amount}</td><td>{action}</td></tr>"
        for client, issue, amount, action in attention_rows
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Bookkeeper Client Ops Dashboard Proof</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; color: #17212b; background: #f4f7f5; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 28px; }}
    .hero {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; align-items: center; }}
    h1 {{ margin: 0 0 10px; font-size: 38px; line-height: 1.08; }}
    p {{ line-height: 1.55; }}
    img {{ max-width: 100%; border: 1px solid #d8e0e6; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 24px 0; }}
    .metric {{ background: white; border: 1px solid #d8e0e6; padding: 14px; }}
    .metric strong {{ display: block; font-size: 22px; margin-top: 6px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; }}
    th, td {{ text-align: left; border-bottom: 1px solid #d8e0e6; padding: 12px; vertical-align: top; }}
    th {{ background: #0b6b58; color: white; }}
    .assets {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 24px; }}
    @media (max-width: 760px) {{ .hero, .assets, .metrics {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div>
        <h1>Simple client dashboard for bookkeepers</h1>
        <p>Shows who owes what, which documents are missing, and what needs attention today.</p>
      </div>
      <img src="../frontend/assets/fiverr-dashboard-screenshot.png" alt="Dashboard screenshot">
    </section>
    <section class="metrics">
      <div class="metric">Paid income<strong>R{dashboard['total_income']:,.2f}</strong></div>
      <div class="metric">Outstanding<strong>R{dashboard['outstanding_invoices']:,.2f}</strong></div>
      <div class="metric">Overdue<strong>{dashboard['overdue_invoices']}</strong></div>
      <div class="metric">VAT estimate<strong>R{dashboard['tax_estimate']:,.2f}</strong></div>
    </section>
    <h2>Attention Today</h2>
    <table>
      <thead><tr><th>Client/Supplier</th><th>Issue</th><th>Amount</th><th>Next Action</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <section class="assets">
      <img src="../frontend/assets/fiverr-dashboard-screenshot.png" alt="Dashboard proof">
      <img src="../frontend/assets/fiverr-report-screenshot.png" alt="Report proof">
    </section>
  </main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def main():
    EVIDENCE_DIR.mkdir(exist_ok=True)
    if DEMO_DB.exists():
        DEMO_DB.unlink()
    receipts = EVIDENCE_DIR / "receipts"
    if receipts.exists():
        shutil.rmtree(receipts)

    os.environ["ACCOUNTING_DATABASE_URL"] = f"sqlite:///{DEMO_DB.resolve().as_posix()}"

    from calculator import accounting_api, accounting_db, api

    accounting_api.RECEIPT_FOLDER = receipts
    accounting_db.reset_accounting_engine_for_tests()

    client = TestClient(api.app)
    email = f"demo-{uuid4().hex[:8]}@example.com"
    registration = api_call(
        client.post(
            "/accounting/auth/register",
            json={
                "email": email,
                "password": "DemoPass123!",
                "name": "Hlomla",
                "business_name": "Client Ops Demo Books",
                "tax_rate": 15,
            },
        )
    ).json()
    headers = {"Authorization": f"Bearer {registration['token']}"}
    business_id = registration["business"]["id"]

    client_payloads = [
        {"name": "Moko Trading", "email": "owner@moko.example", "business_name": "Moko Trading"},
        {"name": "Nkosi Logistics", "email": "finance@nkosi.example", "business_name": "Nkosi Logistics"},
        {"name": "Bloom Cafe", "email": "admin@bloom.example", "business_name": "Bloom Cafe"},
        {"name": "Kwezi Consulting", "email": "ops@kwezi.example", "business_name": "Kwezi Consulting"},
    ]
    created_clients = [
        api_call(client.post(f"/accounting/businesses/{business_id}/clients", headers=headers, json=payload)).json()
        for payload in client_payloads
    ]

    suppliers = [
        api_call(
            client.post(
                f"/accounting/businesses/{business_id}/suppliers",
                headers=headers,
                json={"name": "CloudSuite", "email": "billing@cloudsuite.example"},
            )
        ).json(),
        api_call(
            client.post(
                f"/accounting/businesses/{business_id}/suppliers",
                headers=headers,
                json={"name": "OfficeMart", "email": "accounts@officemart.example"},
            )
        ).json(),
    ]

    invoices = []
    invoice_specs = [
        (created_clients[0], "INV-3001", "2026-05-01", "2026-05-15", "paid", 5000),
        (created_clients[1], "INV-3002", "2026-05-08", "2026-05-24", "unpaid", 3000),
        (created_clients[2], "INV-3003", "2026-06-01", "2026-06-15", "unpaid", 1900),
        (created_clients[3], "INV-3004", "2026-05-18", "2026-05-30", "unpaid", 700),
    ]
    for record, number, issue_date, due_date, status, price in invoice_specs:
        invoice = api_call(
            client.post(
                f"/accounting/businesses/{business_id}/invoices",
                headers=headers,
                json={
                    "client_id": record["id"],
                    "number": number,
                    "issue_date": issue_date,
                    "due_date": due_date,
                    "status": status,
                    "label": "approved" if status == "paid" else "review-needed",
                    "items": [{"description": "Monthly bookkeeping dashboard support", "quantity": 1, "price": price, "tax_rate": 15}],
                },
            )
        ).json()
        if status == "paid":
            invoice = api_call(
                client.patch(
                    f"/accounting/businesses/{business_id}/invoices/{invoice['id']}/status",
                    headers=headers,
                    json={"status": "paid", "paid_at": "2026-05-14"},
                )
            ).json()
        invoices.append(invoice)

    expense_specs = [
        (suppliers[0], "2026-06-01", "Software", 575, True, "missing-info"),
        (suppliers[1], "2026-05-25", "Office", 420, True, "approved"),
        (None, "2026-06-02", "Bank Fees", 120, False, "approved"),
    ]
    expenses = []
    for supplier, expense_date, category, amount, deductible, label in expense_specs:
        expenses.append(
            api_call(
                client.post(
                    f"/accounting/businesses/{business_id}/expenses",
                    headers=headers,
                    json={
                        "supplier_id": supplier["id"] if supplier else None,
                        "supplier_name": supplier["name"] if supplier else "Bank",
                        "date": expense_date,
                        "category": category,
                        "amount": amount,
                        "tax_rate": 15 if deductible else 0,
                        "payment_method": "card",
                        "deductible": deductible,
                        "label": label,
                        "notes": "Receipt still needed." if label == "missing-info" else "",
                    },
                )
            ).json()
        )

    api_call(
        client.post(
            f"/accounting/businesses/{business_id}/expenses/{expenses[1]['id']}/receipt",
            headers=headers,
            files={"file": ("officemart-receipt.pdf", b"receipt-demo", "application/pdf")},
        )
    )

    bank_csv = (
        "Date,Description,Amount,Reference\n"
        "2026-05-14,Payment INV-3001,5750,TRX-001\n"
        "2026-06-02,Bank service fee,-120,TRX-002\n"
        "2026-06-03,Unknown client deposit,850,TRX-003\n"
    )
    bank_import = api_call(
        client.post(
            f"/accounting/businesses/{business_id}/bank-import",
            headers=headers,
            files={"file": ("bank-demo.csv", bank_csv.encode("utf-8"), "text/csv")},
        )
    ).json()

    dashboard = api_call(client.get(f"/accounting/businesses/{business_id}/dashboard", headers=headers)).json()
    write_json(EVIDENCE_DIR / "bookkeeper-dashboard-metrics.json", dashboard)
    write_json(EVIDENCE_DIR / "bookkeeper-bank-import-result.json", bank_import)
    write_json(
        EVIDENCE_DIR / "bookkeeper-demo-records.json",
        {"business": registration["business"], "clients": created_clients, "suppliers": suppliers, "invoices": invoices, "expenses": expenses},
    )

    save_response(
        EVIDENCE_DIR / "bookkeeper-profit-loss-report.csv",
        client.get(f"/accounting/businesses/{business_id}/reports/profit-loss.csv", headers=headers),
    )
    save_response(
        EVIDENCE_DIR / "bookkeeper-cash-flow-report.pdf",
        client.get(f"/accounting/businesses/{business_id}/reports/cash-flow.pdf", headers=headers),
    )
    save_response(
        EVIDENCE_DIR / "bookkeeper-sample-invoice.pdf",
        client.get(f"/accounting/businesses/{business_id}/invoices/{invoices[1]['id']}/pdf", headers=headers),
    )

    attention_rows = [
        ["Nkosi Logistics", "Overdue invoice", "R3,450.00", "Send payment reminder"],
        ["Kwezi Consulting", "Overdue invoice", "R805.00", "Call or email decision maker"],
        ["CloudSuite", "Missing receipt", "R575.00", "Ask client for receipt"],
        ["Bank import", "Unmatched transaction", "R850.00", "Match to invoice or mark as unknown"],
    ]
    generate_proof_pdf(EVIDENCE_DIR / "bookkeeper-client-dashboard-proof.pdf", dashboard, attention_rows)
    generate_html(EVIDENCE_DIR / "bookkeeper-client-dashboard-proof.html", dashboard, attention_rows)

    print("Generated evidence pack:")
    for path in sorted(EVIDENCE_DIR.iterdir()):
        if path.is_file():
            print(f"- {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
