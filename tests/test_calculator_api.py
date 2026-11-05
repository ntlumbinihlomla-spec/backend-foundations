import asyncio
import json
import os
import shutil
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException
from starlette.datastructures import UploadFile

from calculator import api


def make_test_dir():
    path = Path(f".test-artifacts-{uuid4().hex}")
    path.mkdir()
    return path


class TestCalculatorApi(unittest.TestCase):
    def setUp(self):
        self.original_upload_folder = api.UPLOAD_FOLDER
        self.original_data_folder = api.DATA_FOLDER
        self.original_api_keys_file = api.API_KEYS_FILE
        self.original_upload_index_file = api.UPLOAD_INDEX_FILE
        self.original_billing_claims_file = api.BILLING_CLAIMS_FILE
        self.temp_dir = make_test_dir()
        self.upload_dir = self.temp_dir / "uploads"
        self.upload_dir.mkdir()
        self.data_dir = self.temp_dir / "data"
        self.data_dir.mkdir()
        api.UPLOAD_FOLDER = self.upload_dir
        api.DATA_FOLDER = self.data_dir
        api.API_KEYS_FILE = self.data_dir / "api_keys.json"
        api.UPLOAD_INDEX_FILE = self.data_dir / "upload_index.json"
        api.BILLING_CLAIMS_FILE = self.data_dir / "billing_claims.json"
        api.RATE_LIMIT_STORAGE.clear()
        self.request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))

    def tearDown(self):
        api.UPLOAD_FOLDER = self.original_upload_folder
        api.DATA_FOLDER = self.original_data_folder
        api.API_KEYS_FILE = self.original_api_keys_file
        api.UPLOAD_INDEX_FILE = self.original_upload_index_file
        api.BILLING_CLAIMS_FILE = self.original_billing_claims_file
        api.RATE_LIMIT_STORAGE.clear()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_health_returns_ok(self):
        self.assertEqual(api.health(), {"status": "ok"})

    def test_root_returns_service_info(self):
        self.assertEqual(
            api.root(),
            {
                "service": "backend-foundations-api",
                "status": "ok",
                "version": api.API_VERSION,
                "docs": "/docs",
                "status_url": "/status",
            },
        )

    def test_status_returns_runtime_metadata_without_secrets(self):
        api.record_upload("sales.csv", 12, "default")

        with patch.dict(
            os.environ,
            {
                "ENV": "production",
                "MAX_UPLOAD_BYTES": "12345",
                "RATE_LIMIT_MAX_REQUESTS": "7",
                "RATE_LIMIT_WINDOW_SECONDS": "30",
                "STRIPE_SECRET_KEY": "sk_test_secret",
                "STRIPE_PRICE_ID": "price_123",
            },
            clear=True,
        ):
            response = api.status()

        self.assertEqual(response["service"], "backend-foundations-api")
        self.assertEqual(response["version"], api.API_VERSION)
        self.assertEqual(response["storage"]["uploaded_file_count"], 1)
        self.assertEqual(response["limits"]["max_upload_bytes"], 12345)
        self.assertEqual(response["limits"]["rate_limit_max_requests"], 7)
        self.assertEqual(response["limits"]["rate_limit_window_seconds"], 30)
        self.assertEqual(response["limits"]["local_folder_batch_enabled"], False)
        self.assertEqual(response["billing"]["checkout_configured"], True)
        self.assertNotIn("sk_test_secret", json.dumps(response))

    def test_ensure_api_key_store_creates_hashed_default_key(self):
        api.ensure_api_key_store()

        payload = json.loads(api.API_KEYS_FILE.read_text(encoding="utf-8"))

        self.assertEqual(payload["keys"][0]["name"], "default")
        self.assertEqual(payload["keys"][0]["hash"], api.hash_api_key(api.DEFAULT_API_KEY))

    def test_list_uploaded_files_returns_persisted_records(self):
        api.record_upload("sales.csv", 12, "default")

        response = api.list_uploaded_files(self.request, api.DEFAULT_API_KEY)

        self.assertEqual(response["files"][0]["filename"], "sales.csv")
        self.assertEqual(response["files"][0]["uploaded_by"], "default")

    def test_dashboard_summary_returns_totals_and_recent_files(self):
        api.record_upload("a.csv", 12, "default")
        api.record_upload("b.csv", 8, "client-a")

        response = api.dashboard_summary(self.request, api.DEFAULT_API_KEY)

        self.assertEqual(response["file_count"], 2)
        self.assertEqual(response["total_size"], 20)
        self.assertEqual(len(response["recent_files"]), 2)
        self.assertEqual(response["uploaders"], ["client-a", "default"])

    def test_summary_returns_error_for_missing_file(self):
        response = api.get_summary(self.request, "missing.csv", "amount", api.DEFAULT_API_KEY)
        self.assertEqual(response, {"error": "File not found"})

    def test_summary_returns_stats_for_uploaded_file(self):
        sample = self.upload_dir / "sales.csv"
        sample.write_text("amount\n10\n20\n", encoding="utf-8")

        response = api.get_summary(self.request, "sales.csv", "amount", api.DEFAULT_API_KEY)

        self.assertEqual(response["rows"], 2)
        self.assertEqual(response["sum"], 30.0)
        self.assertEqual(response["average"], 15.0)

    def test_summary_returns_error_for_missing_column(self):
        sample = self.upload_dir / "sales.csv"
        sample.write_text("price\n10\n", encoding="utf-8")

        response = api.get_summary(self.request, "sales.csv", "amount", api.DEFAULT_API_KEY)

        self.assertEqual(response, {"error": "Column not found in CSV"})

    def test_uploaded_file_columns_returns_csv_headers(self):
        sample = self.upload_dir / "sales.csv"
        sample.write_text("client,amount,region\nAcme,10,West\n", encoding="utf-8")

        response = api.get_uploaded_file_columns(
            "sales.csv",
            self.request,
            api.DEFAULT_API_KEY,
        )

        self.assertEqual(response["filename"], "sales.csv")
        self.assertEqual(response["columns"], ["client", "amount", "region"])

    def test_uploaded_file_columns_returns_error_for_missing_file(self):
        response = api.get_uploaded_file_columns(
            "missing.csv",
            self.request,
            api.DEFAULT_API_KEY,
        )

        self.assertEqual(response, {"error": "File not found"})

    def test_batch_summary_returns_totals_for_folder(self):
        batch_dir = self.temp_dir / "batch"
        batch_dir.mkdir()
        (batch_dir / "sales_a.csv").write_text("amount\n10\n20\n", encoding="utf-8")
        (batch_dir / "sales_b.csv").write_text("amount\n5\n", encoding="utf-8")

        response = api.batch_summary_endpoint(
            self.request,
            "amount",
            str(batch_dir),
            None,
            api.DEFAULT_API_KEY,
        )

        self.assertEqual(response["grand_total"], 35.0)
        self.assertEqual(response["source"], str(batch_dir))
        self.assertEqual(response["file_count"], 2)
        self.assertEqual(response["average_total_per_file"], 17.5)

    def test_batch_summary_returns_totals_for_selected_uploaded_files(self):
        (self.upload_dir / "sales_a.csv").write_text("amount\n10\n20\n", encoding="utf-8")
        (self.upload_dir / "sales_b.csv").write_text("amount\n5\n", encoding="utf-8")

        response = api.batch_summary_endpoint(
            self.request,
            "amount",
            None,
            "sales_a.csv,sales_b.csv",
            api.DEFAULT_API_KEY,
        )

        self.assertEqual(response["grand_total"], 35.0)
        self.assertEqual(response["source"], "uploaded-files")
        self.assertEqual(response["file_count"], 2)
        self.assertEqual(response["average_total_per_file"], 17.5)
        self.assertEqual(
            response["files"],
            [
                {"file": "sales_a.csv", "total": 30.0, "rows": 2},
                {"file": "sales_b.csv", "total": 5.0, "rows": 1},
            ],
        )

    def test_batch_summary_returns_error_for_missing_folder(self):
        response = api.batch_summary_endpoint(
            self.request,
            "amount",
            "missing-folder",
            None,
            api.DEFAULT_API_KEY,
        )
        self.assertEqual(response, {"error": "Folder not found"})

    def test_batch_summary_blocks_explicit_folder_in_production_by_default(self):
        batch_dir = self.temp_dir / "batch"
        batch_dir.mkdir()
        (batch_dir / "sales.csv").write_text("amount\n10\n", encoding="utf-8")

        with patch.dict(os.environ, {"ENV": "production"}, clear=True):
            response = api.batch_summary_endpoint(
                self.request,
                "amount",
                str(batch_dir),
                None,
                api.DEFAULT_API_KEY,
            )

        self.assertEqual(
            response,
            {
                "error": (
                    "Local folder batch summaries are disabled in this environment. "
                    "Upload files and use the files parameter instead."
                )
            },
        )

    def test_batch_summary_allows_explicit_folder_when_configured(self):
        batch_dir = self.temp_dir / "batch"
        batch_dir.mkdir()
        (batch_dir / "sales.csv").write_text("amount\n10\n", encoding="utf-8")

        with patch.dict(
            os.environ,
            {"ENV": "production", "ALLOW_LOCAL_FOLDER_BATCH": "true"},
            clear=True,
        ):
            response = api.batch_summary_endpoint(
                self.request,
                "amount",
                str(batch_dir),
                None,
                api.DEFAULT_API_KEY,
            )

        self.assertEqual(response["grand_total"], 10.0)
        self.assertEqual(response["file_count"], 1)

    def test_client_report_returns_exportable_html_for_selected_files(self):
        (self.upload_dir / "sales_a.csv").write_text("amount\n10\n20\n", encoding="utf-8")
        (self.upload_dir / "sales_b.csv").write_text("amount\n5\n", encoding="utf-8")

        response = api.client_report(
            self.request,
            "amount",
            "sales_a.csv,sales_b.csv",
            api.DEFAULT_API_KEY,
        )

        body = response.body.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Financial CSV Summary Report", body)
        self.assertIn("sales_a.csv", body)
        self.assertIn("R35.00", body)
        self.assertIn("Print or Save PDF", body)

    def test_client_report_returns_not_found_for_missing_file(self):
        response = api.client_report(
            self.request,
            "amount",
            "missing.csv",
            api.DEFAULT_API_KEY,
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("File not found", response.body.decode("utf-8"))

    def test_upload_file_saves_contents_and_records_metadata(self):
        upload = UploadFile(
            filename="sales.csv",
            file=(self.temp_dir / "source.csv").open("w+b"),
        )
        upload.file.write(b"amount\n10\n")
        upload.file.seek(0)

        response = asyncio.run(api.upload_file(self.request, upload, api.DEFAULT_API_KEY))

        saved = self.upload_dir / "sales.csv"
        self.assertEqual(response["filename"], "sales.csv")
        self.assertEqual(response["uploaded_by"], "default")
        self.assertTrue(saved.exists())
        self.assertEqual(saved.read_text(encoding="utf-8"), "amount\n10\n")
        upload_records = api.get_upload_records()
        self.assertEqual(upload_records[0]["filename"], "sales.csv")
        upload.file.close()

    def test_import_csv_source_saves_fetched_csv(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self, size):
                return b"amount\n10\n20\n"

        with patch.object(api, "validate_source_url"):
            with patch.object(api.urllib.request, "urlopen", return_value=FakeResponse()):
                response = api.import_csv_source(
                    self.request,
                    {
                        "url": "https://example.com/monthly.csv",
                        "filename": "client-monthly.csv",
                    },
                    api.DEFAULT_API_KEY,
                )

        saved = self.upload_dir / "client-monthly.csv"
        self.assertEqual(response["filename"], "client-monthly.csv")
        self.assertEqual(response["message"], "CSV source imported.")
        self.assertTrue(saved.exists())
        self.assertEqual(saved.read_text(encoding="utf-8"), "amount\n10\n20\n")
        upload_record = api.get_upload_records()[0]
        self.assertEqual(upload_record["filename"], "client-monthly.csv")
        self.assertEqual(upload_record["source_type"], "csv_url")
        self.assertEqual(upload_record["source_url"], "https://example.com/monthly.csv")
        self.assertIn("refreshed_at", upload_record)

    def test_refresh_csv_sources_updates_connected_source_files(self):
        original = b"amount\n1\n"
        refreshed = b"amount\n30\n40\n"
        (self.upload_dir / "client-monthly.csv").write_bytes(original)
        api.record_upload(
            "client-monthly.csv",
            len(original),
            "default",
            source_url="https://example.com/monthly.csv",
            source_type="csv_url",
            refreshed_at=100,
        )

        with patch.object(api, "fetch_csv_source", return_value=refreshed):
            with patch.object(api.time, "time", return_value=200):
                response = api.refresh_csv_sources(
                    self.request,
                    {},
                    api.DEFAULT_API_KEY,
                )

        saved = self.upload_dir / "client-monthly.csv"
        upload_record = api.get_upload_records()[0]
        self.assertEqual(response["message"], "Refreshed 1 connected CSV source(s).")
        self.assertEqual(response["refreshed"][0]["filename"], "client-monthly.csv")
        self.assertEqual(response["refreshed"][0]["size"], len(refreshed))
        self.assertEqual(saved.read_bytes(), refreshed)
        self.assertEqual(upload_record["size"], len(refreshed))
        self.assertEqual(upload_record["uploaded_by"], "default")
        self.assertEqual(upload_record["source_url"], "https://example.com/monthly.csv")
        self.assertEqual(upload_record["refreshed_at"], 200)

    def test_refresh_csv_sources_reports_missing_connected_source(self):
        response = api.refresh_csv_sources(
            self.request,
            {"filenames": ["manual.csv"]},
            api.DEFAULT_API_KEY,
        )

        self.assertEqual(response["refreshed"], [])
        self.assertEqual(
            response["failed"],
            [
                {
                    "filename": "manual.csv",
                    "error": "No connected CSV source is saved for this file.",
                }
            ],
        )
        self.assertEqual(response["message"], "No connected CSV sources were refreshed.")

    def test_refresh_csv_sources_returns_message_when_no_sources_exist(self):
        response = api.refresh_csv_sources(self.request, {}, api.DEFAULT_API_KEY)

        self.assertEqual(response["refreshed"], [])
        self.assertEqual(response["failed"], [])
        self.assertEqual(response["message"], "No connected CSV sources are saved yet.")

    def test_import_csv_source_rejects_missing_url(self):
        with self.assertRaises(HTTPException) as exc_info:
            api.import_csv_source(self.request, {"filename": "sales.csv"}, api.DEFAULT_API_KEY)

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertEqual(exc_info.exception.detail, "Provide a CSV source URL.")

    def test_validate_source_url_rejects_private_hosts(self):
        with patch.object(
            api.socket,
            "getaddrinfo",
            return_value=[
                (
                    api.socket.AF_INET,
                    api.socket.SOCK_STREAM,
                    6,
                    "",
                    ("127.0.0.1", 80),
                )
            ],
        ):
            with self.assertRaises(HTTPException) as exc_info:
                api.validate_source_url("https://example.com/report.csv")

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertEqual(exc_info.exception.detail, "Private or local source URLs are not allowed.")

    def test_validate_source_url_rejects_unsupported_scheme(self):
        with self.assertRaises(HTTPException) as exc_info:
            api.validate_source_url("file:///tmp/report.csv")

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertEqual(exc_info.exception.detail, "Source URL must use http or https.")

    def test_delete_uploaded_file_removes_file_and_metadata(self):
        sample = self.upload_dir / "sales.csv"
        sample.write_text("amount\n10\n", encoding="utf-8")
        api.record_upload("sales.csv", 10, "default")

        response = api.delete_uploaded_file("sales.csv", self.request, api.DEFAULT_API_KEY)

        self.assertEqual(response["deleted"], True)
        self.assertFalse(sample.exists())
        self.assertEqual(api.get_upload_records(), [])

    def test_delete_uploaded_file_returns_error_for_missing_file(self):
        response = api.delete_uploaded_file("missing.csv", self.request, api.DEFAULT_API_KEY)
        self.assertEqual(response, {"error": "File not found"})

    def test_upload_file_rejects_invalid_api_key(self):
        upload = UploadFile(
            filename="sales.csv",
            file=(self.temp_dir / "source.csv").open("w+b"),
        )
        upload.file.write(b"amount\n10\n")
        upload.file.seek(0)

        with self.assertRaises(HTTPException) as exc_info:
            asyncio.run(api.upload_file(self.request, upload, "wrong-key"))

        self.assertEqual(exc_info.exception.status_code, 401)
        upload.file.close()

    def test_upload_file_rejects_non_csv_uploads(self):
        upload = UploadFile(
            filename="notes.txt",
            file=(self.temp_dir / "source.txt").open("w+b"),
        )
        upload.file.write(b"hello\n")
        upload.file.seek(0)

        with self.assertRaises(HTTPException) as exc_info:
            asyncio.run(api.upload_file(self.request, upload, api.DEFAULT_API_KEY))

        self.assertEqual(exc_info.exception.status_code, 400)
        upload.file.close()

    def test_upload_file_rejects_oversized_uploads(self):
        upload = UploadFile(
            filename="sales.csv",
            file=(self.temp_dir / "source.csv").open("w+b"),
        )
        upload.file.write(b"amount\n123456\n")
        upload.file.seek(0)

        with patch.dict(os.environ, {"MAX_UPLOAD_BYTES": "8"}):
            with self.assertRaises(HTTPException) as exc_info:
                asyncio.run(api.upload_file(self.request, upload, api.DEFAULT_API_KEY))

        self.assertEqual(exc_info.exception.status_code, 413)
        self.assertFalse((self.upload_dir / "sales.csv").exists())
        upload.file.close()

    def test_upload_file_rejects_non_utf8_csv_uploads(self):
        upload = UploadFile(
            filename="sales.csv",
            file=(self.temp_dir / "source.csv").open("w+b"),
        )
        upload.file.write(b"\xff\xfe\x00\x00")
        upload.file.seek(0)

        with self.assertRaises(HTTPException) as exc_info:
            asyncio.run(api.upload_file(self.request, upload, api.DEFAULT_API_KEY))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertIn("UTF-8", exc_info.exception.detail)
        self.assertFalse((self.upload_dir / "sales.csv").exists())
        upload.file.close()

    def test_upload_file_rejects_csv_without_headers(self):
        upload = UploadFile(
            filename="sales.csv",
            file=(self.temp_dir / "source.csv").open("w+b"),
        )
        upload.file.write(b"\n\n")
        upload.file.seek(0)

        with self.assertRaises(HTTPException) as exc_info:
            asyncio.run(api.upload_file(self.request, upload, api.DEFAULT_API_KEY))

        self.assertEqual(exc_info.exception.status_code, 400)
        self.assertEqual(exc_info.exception.detail, "CSV uploads must include a header row.")
        self.assertFalse((self.upload_dir / "sales.csv").exists())
        upload.file.close()

    def test_require_api_key_uses_environment_override_for_new_store(self):
        with patch.dict(os.environ, {"API_KEY": "secret-key"}):
            api.ensure_api_key_store()
            api.require_api_key("secret-key")

            with self.assertRaises(HTTPException) as exc_info:
                api.require_api_key(api.DEFAULT_API_KEY)

        self.assertEqual(exc_info.exception.status_code, 401)

    def test_require_api_key_accepts_persisted_hash(self):
        api.write_json_file(
            api.API_KEYS_FILE,
            {
                "keys": [
                    {"name": "client-a", "hash": api.hash_api_key("client-secret")}
                ]
            },
        )

        self.assertEqual(api.require_api_key("client-secret"), "client-a")

    def test_provision_paid_api_key_hashes_key_and_claims_once(self):
        with patch.object(api, "generate_paid_api_key", return_value="bf_live_test"):
            response = api.provision_paid_api_key(
                "buyer@example.com",
                "cs_test_123",
                "cus_123",
                "sub_123",
                now=100,
            )

        self.assertEqual(response["status"], "provisioned")
        self.assertEqual(api.require_api_key("bf_live_test"), "paid:buyer@example.com")
        paid_records = [
            record
            for record in api.get_api_key_records()
            if record.get("source") == "stripe"
        ]
        self.assertEqual(len(paid_records), 1)
        self.assertEqual(paid_records[0]["hash"], api.hash_api_key("bf_live_test"))
        self.assertEqual(paid_records[0]["stripe_subscription_id"], "sub_123")

        claim = api.claim_paid_api_key("cs_test_123", now=120)
        self.assertEqual(claim["status"], "ready")
        self.assertEqual(claim["api_key"], "bf_live_test")
        self.assertEqual(api.claim_paid_api_key("cs_test_123", now=130)["status"], "claimed")

    def test_duplicate_paid_api_key_provision_is_idempotent(self):
        with patch.object(api, "generate_paid_api_key", return_value="bf_live_first"):
            first = api.provision_paid_api_key("buyer@example.com", "cs_test_123")

        with patch.object(api, "generate_paid_api_key", return_value="bf_live_second"):
            second = api.provision_paid_api_key("buyer@example.com", "cs_test_123")

        paid_records = [
            record
            for record in api.get_api_key_records()
            if record.get("source") == "stripe"
        ]
        self.assertEqual(first["status"], "provisioned")
        self.assertEqual(second["status"], "already_provisioned")
        self.assertEqual(len(paid_records), 1)
        self.assertEqual(api.claim_paid_api_key("cs_test_123")["api_key"], "bf_live_first")

    def test_deactivate_paid_api_keys_revokes_subscription_key(self):
        with patch.object(api, "generate_paid_api_key", return_value="bf_live_test"):
            api.provision_paid_api_key(
                "buyer@example.com",
                "cs_test_123",
                "cus_123",
                "sub_123",
            )

        updated_count = api.deactivate_paid_api_keys(stripe_subscription_id="sub_123")

        self.assertEqual(updated_count, 1)
        with self.assertRaises(HTTPException) as exc_info:
            api.require_api_key("bf_live_test")
        self.assertEqual(exc_info.exception.status_code, 401)

    def test_handle_stripe_checkout_event_provisions_key(self):
        event = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "payment_status": "paid",
                    "customer": "cus_123",
                    "subscription": "sub_123",
                    "customer_details": {"email": "buyer@example.com"},
                }
            },
        }

        with patch.object(api, "generate_paid_api_key", return_value="bf_live_test"):
            response = api.handle_stripe_event(event)

        self.assertEqual(response["provisioned"], True)
        self.assertEqual(api.require_api_key("bf_live_test"), "paid:buyer@example.com")

    def test_handle_stripe_subscription_deleted_deactivates_key(self):
        with patch.object(api, "generate_paid_api_key", return_value="bf_live_test"):
            api.provision_paid_api_key(
                "buyer@example.com",
                "cs_test_123",
                "cus_123",
                "sub_123",
            )

        response = api.handle_stripe_event(
            {
                "type": "customer.subscription.deleted",
                "data": {"object": {"id": "sub_123", "customer": "cus_123"}},
            }
        )

        self.assertEqual(response["deactivated_keys"], 1)
        with self.assertRaises(HTTPException):
            api.require_api_key("bf_live_test")

    def test_create_checkout_session_requires_stripe_config(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as exc_info:
                api.create_checkout_session({})

        self.assertEqual(exc_info.exception.status_code, 503)

    def test_create_checkout_session_returns_stripe_url(self):
        created_payload = {}

        class FakeCheckoutSession:
            @staticmethod
            def create(**kwargs):
                created_payload.update(kwargs)
                return {"id": "cs_test_123", "url": "https://checkout.stripe.test/session"}

        fake_stripe = SimpleNamespace(
            checkout=SimpleNamespace(Session=FakeCheckoutSession),
            api_key=None,
        )

        with patch.object(api, "stripe", fake_stripe):
            with patch.dict(
                os.environ,
                {
                    "STRIPE_SECRET_KEY": "sk_test_123",
                    "STRIPE_PRICE_ID": "price_123",
                    "PUBLIC_BASE_URL": "https://api.example.com",
                },
                clear=True,
            ):
                response = api.create_checkout_session({"email": "buyer@example.com"})

        self.assertEqual(response["checkout_url"], "https://checkout.stripe.test/session")
        self.assertEqual(response["session_id"], "cs_test_123")
        self.assertEqual(fake_stripe.api_key, "sk_test_123")
        self.assertEqual(created_payload["mode"], "subscription")
        self.assertEqual(created_payload["line_items"], [{"price": "price_123", "quantity": 1}])
        self.assertEqual(created_payload["customer_email"], "buyer@example.com")
        self.assertEqual(
            created_payload["success_url"],
            "https://api.example.com/billing/success?session_id={CHECKOUT_SESSION_ID}",
        )

    def test_enforce_rate_limit_blocks_excess_requests(self):
        with patch.dict(
            os.environ,
            {"RATE_LIMIT_WINDOW_SECONDS": "60", "RATE_LIMIT_MAX_REQUESTS": "2"},
        ):
            api.enforce_rate_limit("client-1", now=100.0)
            api.enforce_rate_limit("client-1", now=110.0)

            with self.assertRaises(HTTPException) as exc_info:
                api.enforce_rate_limit("client-1", now=120.0)

        self.assertEqual(exc_info.exception.status_code, 429)


if __name__ == "__main__":
    unittest.main()
