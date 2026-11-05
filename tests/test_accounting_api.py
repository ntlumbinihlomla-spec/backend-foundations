import os
import shutil
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from calculator import accounting_api, accounting_db, api


def make_test_dir():
    path = Path(f".test-accounting-{uuid4().hex}")
    path.mkdir()
    return path


class TestAccountingApi(unittest.TestCase):
    def setUp(self):
        self.temp_dir = make_test_dir()
        self.db_path = self.temp_dir / "accounting.sqlite3"
        self.original_database_url = os.environ.get("ACCOUNTING_DATABASE_URL")
        self.original_receipt_folder = accounting_api.RECEIPT_FOLDER
        os.environ["ACCOUNTING_DATABASE_URL"] = f"sqlite:///{self.db_path.resolve().as_posix()}"
        accounting_api.RECEIPT_FOLDER = self.temp_dir / "receipts"
        accounting_db.reset_accounting_engine_for_tests()
        self.client = TestClient(api.app)

    def tearDown(self):
        self.client.close()
        accounting_db.reset_accounting_engine_for_tests()
        accounting_api.RECEIPT_FOLDER = self.original_receipt_folder
        if self.original_database_url is None:
            os.environ.pop("ACCOUNTING_DATABASE_URL", None)
        else:
            os.environ["ACCOUNTING_DATABASE_URL"] = self.original_database_url
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def register_user(self, email="owner@example.com", business_name="Hlomla Books"):
        response = self.client.post(
            "/accounting/auth/register",
            json={
                "email": email,
                "password": "StrongPass123!",
                "name": "Hlomla",
                "business_name": business_name,
                "tax_rate": 15,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        return payload, {"Authorization": f"Bearer {payload['token']}"}

    def test_accounting_crud_exports_receipts_and_reports(self):
        registration, headers = self.register_user()
        business_id = registration["business"]["id"]

        client_response = self.client.post(
            f"/accounting/businesses/{business_id}/clients",
            headers=headers,
            json={
                "name": "Thabo Owner",
                "email": "thabo@example.com",
                "business_name": "Thabo Trading",
                "tax_number": "VAT123",
            },
        )
        self.assertEqual(client_response.status_code, 200, client_response.text)
        client_id = client_response.json()["id"]

        supplier_response = self.client.post(
            f"/accounting/businesses/{business_id}/suppliers",
            headers=headers,
            json={"name": "Cloud Vendor", "email": "accounts@cloud.test"},
        )
        self.assertEqual(supplier_response.status_code, 200, supplier_response.text)
        supplier_id = supplier_response.json()["id"]

        invoice_response = self.client.post(
            f"/accounting/businesses/{business_id}/invoices",
            headers=headers,
            json={
                "client_id": client_id,
                "number": "INV-1001",
                "issue_date": "2026-06-01",
                "due_date": "2026-06-15",
                "status": "unpaid",
                "label": "review-needed",
                "items": [
                    {
                        "description": "Monthly bookkeeping",
                        "quantity": 2,
                        "price": 500,
                        "tax_rate": 15,
                    }
                ],
            },
        )
        self.assertEqual(invoice_response.status_code, 200, invoice_response.text)
        invoice = invoice_response.json()
        self.assertEqual(invoice["totals"]["total"], 1150.0)

        paid_response = self.client.patch(
            f"/accounting/businesses/{business_id}/invoices/{invoice['id']}/status",
            headers=headers,
            json={"status": "paid", "paid_at": "2026-06-02"},
        )
        self.assertEqual(paid_response.status_code, 200, paid_response.text)
        self.assertEqual(paid_response.json()["status"], "paid")

        expense_response = self.client.post(
            f"/accounting/businesses/{business_id}/expenses",
            headers=headers,
            json={
                "supplier_id": supplier_id,
                "date": "2026-06-02",
                "category": "Software",
                "amount": 230,
                "tax_rate": 15,
                "payment_method": "card",
                "deductible": "false",
                "label": "approved",
            },
        )
        self.assertEqual(expense_response.status_code, 200, expense_response.text)
        expense = expense_response.json()
        self.assertFalse(expense["deductible"])

        receipt_response = self.client.post(
            f"/accounting/businesses/{business_id}/expenses/{expense['id']}/receipt",
            headers=headers,
            files={"file": ("receipt.png", b"receipt-bytes", "image/png")},
        )
        self.assertEqual(receipt_response.status_code, 200, receipt_response.text)
        self.assertEqual(receipt_response.json()["filename"], "receipt.png")

        dashboard_response = self.client.get(f"/accounting/businesses/{business_id}/dashboard", headers=headers)
        self.assertEqual(dashboard_response.status_code, 200, dashboard_response.text)
        dashboard = dashboard_response.json()
        self.assertEqual(dashboard["total_income"], 1150.0)
        self.assertEqual(dashboard["total_expenses"], 230.0)
        self.assertEqual(dashboard["net_profit"], 920.0)
        self.assertEqual(dashboard["tax_estimate"], 150.0)
        self.assertEqual(dashboard["monthly_revenue"][0]["month"], "2026-06")
        self.assertEqual(dashboard["expense_category_breakdown"][0]["category"], "Software")

        report_response = self.client.get(
            f"/accounting/businesses/{business_id}/reports/profit-loss",
            headers=headers,
        )
        self.assertEqual(report_response.status_code, 200, report_response.text)
        self.assertEqual(report_response.json()["title"], "Profit & Loss Report")

        csv_response = self.client.get(
            f"/accounting/businesses/{business_id}/reports/profit-loss.csv",
            headers=headers,
        )
        self.assertEqual(csv_response.status_code, 200, csv_response.text)
        self.assertIn("Income", csv_response.text)

        invoice_pdf_response = self.client.get(
            f"/accounting/businesses/{business_id}/invoices/{invoice['id']}/pdf",
            headers=headers,
        )
        self.assertEqual(invoice_pdf_response.status_code, 200, invoice_pdf_response.text)
        self.assertTrue(invoice_pdf_response.content.startswith(b"%PDF"))

        report_pdf_response = self.client.get(
            f"/accounting/businesses/{business_id}/reports/cash-flow.pdf",
            headers=headers,
        )
        self.assertEqual(report_pdf_response.status_code, 200, report_pdf_response.text)
        self.assertTrue(report_pdf_response.content.startswith(b"%PDF"))

        audit_response = self.client.get(f"/accounting/businesses/{business_id}/audit-logs", headers=headers)
        self.assertEqual(audit_response.status_code, 200, audit_response.text)
        audit_entities = {log["entity"] for log in audit_response.json()["audit_logs"]}
        self.assertIn("invoice", audit_entities)
        self.assertIn("receipt", audit_entities)

    def test_user_cannot_access_another_users_business(self):
        owner_registration, owner_headers = self.register_user("owner@example.com", "Owner Business")
        second_registration, second_headers = self.register_user("other@example.com", "Other Business")

        owner_business_id = owner_registration["business"]["id"]
        second_business_id = second_registration["business"]["id"]

        owner_response = self.client.get(f"/accounting/businesses/{owner_business_id}", headers=owner_headers)
        self.assertEqual(owner_response.status_code, 200, owner_response.text)

        blocked_response = self.client.get(f"/accounting/businesses/{owner_business_id}", headers=second_headers)
        self.assertEqual(blocked_response.status_code, 404, blocked_response.text)

        second_response = self.client.get(f"/accounting/businesses/{second_business_id}", headers=second_headers)
        self.assertEqual(second_response.status_code, 200, second_response.text)

    def test_bank_import_auto_matches_and_manual_match_is_scoped(self):
        registration, headers = self.register_user()
        business_id = registration["business"]["id"]

        invoice_response = self.client.post(
            f"/accounting/businesses/{business_id}/invoices",
            headers=headers,
            json={
                "number": "INV-2001",
                "issue_date": "2026-06-03",
                "due_date": "2026-06-10",
                "status": "unpaid",
                "items": [{"description": "Dashboard setup", "quantity": 1, "price": 100, "tax_rate": 15}],
            },
        )
        self.assertEqual(invoice_response.status_code, 200, invoice_response.text)
        invoice = invoice_response.json()

        bank_csv = "Date,Description,Amount,Reference\n2026-06-03,Payment INV-2001,115,TRX1\n"
        import_response = self.client.post(
            f"/accounting/businesses/{business_id}/bank-import",
            headers=headers,
            files={"file": ("bank.csv", bank_csv.encode("utf-8"), "text/csv")},
        )
        self.assertEqual(import_response.status_code, 200, import_response.text)
        transaction = import_response.json()["transactions"][0]
        self.assertEqual(transaction["status"], "matched")
        self.assertEqual(transaction["matched_entity_type"], "invoice")
        self.assertEqual(transaction["matched_entity_id"], invoice["id"])

        manual_response = self.client.patch(
            f"/accounting/businesses/{business_id}/bank-transactions/{transaction['id']}/match",
            headers=headers,
            json={"matched_entity_type": "invoice", "matched_entity_id": "inv_missing"},
        )
        self.assertEqual(manual_response.status_code, 404, manual_response.text)
