import csv
import hashlib
import html
import hmac
import io
import json
import os
import secrets
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import ipaddress
from pathlib import Path

from fastapi import Body, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from calculator.accounting_api import router as accounting_router
from calculator.finance_tools import batch_summarize, get_csv_columns, summarize_csv_column

try:
    import stripe
except ImportError:  # pragma: no cover - exercised when optional billing deps are absent.
    stripe = None


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)
DATA_FOLDER = BASE_DIR / "data"
DATA_FOLDER.mkdir(exist_ok=True)
API_KEYS_FILE = DATA_FOLDER / "api_keys.json"
UPLOAD_INDEX_FILE = DATA_FOLDER / "upload_index.json"
BILLING_CLAIMS_FILE = DATA_FOLDER / "billing_claims.json"
DEFAULT_API_KEY = "backend-foundations-demo-key"
API_VERSION = "0.4.0"
DEFAULT_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
DEFAULT_SOURCE_FETCH_TIMEOUT_SECONDS = 12
RATE_LIMIT_STORAGE = {}

app = FastAPI(title="Backend Foundations API", version=API_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(accounting_router)


def get_configured_api_key():
    return os.getenv("API_KEY", DEFAULT_API_KEY)


def get_env_int(name, default, minimum=1):
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    if value < minimum:
        return default
    return value


def get_rate_limit_window_seconds():
    return get_env_int("RATE_LIMIT_WINDOW_SECONDS", 60)


def get_rate_limit_max_requests():
    return get_env_int("RATE_LIMIT_MAX_REQUESTS", 10)


def get_max_upload_bytes():
    return get_env_int("MAX_UPLOAD_BYTES", DEFAULT_MAX_UPLOAD_BYTES)


def get_source_fetch_timeout_seconds():
    return get_env_int(
        "SOURCE_FETCH_TIMEOUT_SECONDS",
        DEFAULT_SOURCE_FETCH_TIMEOUT_SECONDS,
    )


def is_production():
    return os.getenv("ENV", "development").strip().lower() == "production"


def is_enabled(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def allow_local_folder_batch():
    configured_value = os.getenv("ALLOW_LOCAL_FOLDER_BATCH")
    if configured_value is not None:
        return is_enabled(configured_value)
    return not is_production()


def allow_private_source_urls():
    return is_enabled(os.getenv("ALLOW_PRIVATE_SOURCE_URLS", "false"))


def hash_api_key(raw_key):
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def read_json_file(path, default_value):
    if not path.exists():
        return default_value

    with path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def write_json_file(path, payload):
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, indent=2)


def ensure_api_key_store():
    if API_KEYS_FILE.exists():
        return

    write_json_file(
        API_KEYS_FILE,
        {
            "keys": [
                {
                    "name": "default",
                    "hash": hash_api_key(get_configured_api_key()),
                }
            ]
        },
    )


def ensure_upload_index():
    if not UPLOAD_INDEX_FILE.exists():
        write_json_file(UPLOAD_INDEX_FILE, {"files": []})


def ensure_billing_claims():
    if not BILLING_CLAIMS_FILE.exists():
        write_json_file(BILLING_CLAIMS_FILE, {"claims": []})


def get_api_key_records():
    ensure_api_key_store()
    payload = read_json_file(API_KEYS_FILE, {"keys": []})
    return payload.get("keys", [])


def save_api_key_records(records):
    write_json_file(API_KEYS_FILE, {"keys": records})


def get_upload_records():
    ensure_upload_index()
    payload = read_json_file(UPLOAD_INDEX_FILE, {"files": []})
    return payload.get("files", [])


def get_billing_claim_records():
    ensure_billing_claims()
    payload = read_json_file(BILLING_CLAIMS_FILE, {"claims": []})
    return payload.get("claims", [])


def save_billing_claim_records(records):
    write_json_file(BILLING_CLAIMS_FILE, {"claims": records})


def save_upload_records(records):
    write_json_file(UPLOAD_INDEX_FILE, {"files": records})


def record_upload(
    filename,
    size,
    uploaded_by,
    source_url=None,
    source_type="upload",
    refreshed_at=None,
):
    records = [item for item in get_upload_records() if item.get("filename") != filename]
    uploaded_at = int(time.time())
    record = {
        "filename": filename,
        "size": size,
        "uploaded_at": uploaded_at,
        "uploaded_by": uploaded_by,
        "source_type": source_type,
    }
    if source_url:
        record["source_type"] = "csv_url"
        record["source_url"] = source_url
        record["refreshed_at"] = int(refreshed_at or uploaded_at)

    records.append(record)
    records.sort(key=lambda item: item["filename"])
    save_upload_records(records)


def remove_upload_record(filename):
    records = [item for item in get_upload_records() if item.get("filename") != filename]
    save_upload_records(records)


def build_dashboard_summary():
    files = get_upload_records()
    total_size = sum(item.get("size", 0) for item in files)
    source_files = [
        item
        for item in files
        if item.get("source_type") == "csv_url" and item.get("source_url")
    ]
    last_source_refresh = max(
        (
            item.get("refreshed_at") or item.get("uploaded_at") or 0
            for item in source_files
        ),
        default=None,
    )
    recent_files = sorted(
        files,
        key=lambda item: item.get("uploaded_at", 0),
        reverse=True,
    )[:5]
    uploaders = sorted({item.get("uploaded_by", "unknown") for item in files})

    return {
        "file_count": len(files),
        "total_size": total_size,
        "recent_files": recent_files,
        "uploaders": uploaders,
        "source_count": len(source_files),
        "last_source_refresh": last_source_refresh,
    }


def validate_csv_upload(content):
    max_upload_bytes = get_max_upload_bytes()
    if len(content) > max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds the {max_upload_bytes} byte limit.",
        )

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="CSV uploads must be UTF-8 text files.",
        ) from exc

    try:
        reader = csv.DictReader(io.StringIO(text))
        columns = [column.strip() for column in (reader.fieldnames or []) if column.strip()]
    except csv.Error as exc:
        raise HTTPException(
            status_code=400,
            detail=f"CSV upload could not be parsed: {exc}",
        ) from exc

    if not columns:
        raise HTTPException(
            status_code=400,
            detail="CSV uploads must include a header row.",
        )

    return columns


def validate_source_url(source_url):
    parsed = urllib.parse.urlparse(source_url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Source URL must use http or https.")

    if not parsed.hostname:
        raise HTTPException(status_code=400, detail="Source URL must include a host.")

    if allow_private_source_urls():
        return parsed

    try:
        resolved_addresses = socket.getaddrinfo(parsed.hostname, parsed.port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail="Source URL host could not be resolved.") from exc

    for address_info in resolved_addresses:
        ip_address = ipaddress.ip_address(address_info[4][0])
        if (
            ip_address.is_private
            or ip_address.is_loopback
            or ip_address.is_link_local
            or ip_address.is_reserved
            or ip_address.is_multicast
        ):
            raise HTTPException(
                status_code=400,
                detail="Private or local source URLs are not allowed.",
            )

    return parsed


def build_source_filename(source_url, requested_filename=None):
    if requested_filename:
        safe_name = Path(requested_filename).name
    else:
        parsed = urllib.parse.urlparse(source_url)
        safe_name = Path(urllib.parse.unquote(parsed.path)).name or "source.csv"

    if not safe_name.lower().endswith(".csv"):
        safe_name = f"{safe_name}.csv"

    return safe_name


def parse_filename_list(value):
    if not value:
        return []

    if isinstance(value, str):
        raw_names = value.split(",")
    elif isinstance(value, list):
        raw_names = value
    else:
        return []

    return [
        Path(str(item).strip()).name
        for item in raw_names
        if str(item).strip()
    ]


def get_connected_source_records(filenames=None):
    selected_names = set(filenames or [])
    records = []

    for record in get_upload_records():
        filename = Path(str(record.get("filename", ""))).name
        has_saved_source = (
            record.get("source_type") == "csv_url"
            and record.get("source_url")
        )
        if not filename or not has_saved_source:
            continue
        if selected_names and filename not in selected_names:
            continue
        records.append(record)

    return records


def fetch_csv_source(source_url):
    validate_source_url(source_url)
    max_upload_bytes = get_max_upload_bytes()
    request = urllib.request.Request(
        source_url,
        headers={"User-Agent": "backend-foundations-csv-source/1.0"},
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=get_source_fetch_timeout_seconds(),
        ) as response:
            content = response.read(max_upload_bytes + 1)
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=400, detail=f"Source URL could not be fetched: {exc.reason}") from exc

    if not content:
        raise HTTPException(status_code=400, detail="Source URL returned an empty file.")

    validate_csv_upload(content)
    return content


def refresh_connected_csv_source(record, client_name, refreshed_at=None):
    filename = Path(str(record.get("filename", ""))).name
    source_url = str(record.get("source_url", "")).strip()
    if not filename or not source_url:
        raise ValueError("Connected source record is missing a filename or source URL.")

    content = fetch_csv_source(source_url)
    destination = UPLOAD_FOLDER / filename
    with destination.open("wb") as file_handle:
        file_handle.write(content)

    refresh_time = int(refreshed_at or time.time())
    record_upload(
        filename,
        len(content),
        client_name,
        source_url=source_url,
        source_type="csv_url",
        refreshed_at=refresh_time,
    )

    return {
        "filename": filename,
        "size": len(content),
        "refreshed_at": refresh_time,
        "source_url": source_url,
    }


def require_api_key(provided_api_key):
    if not provided_api_key:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized. Provide a valid x-api-key header.",
        )

    provided_hash = hash_api_key(provided_api_key)
    for record in get_api_key_records():
        stored_hash = record.get("hash", "")
        is_active = record.get("status", "active") == "active"
        if is_active and hmac.compare_digest(provided_hash, stored_hash):
            return record.get("name", "client")

    raise HTTPException(
        status_code=401,
        detail="Unauthorized. Provide a valid x-api-key header.",
    )


def get_client_id(request):
    if request.client and request.client.host:
        return request.client.host
    return "anonymous"


def enforce_rate_limit(client_id, now=None):
    current_time = now if now is not None else time.time()
    window_seconds = get_rate_limit_window_seconds()
    max_requests = get_rate_limit_max_requests()
    window_start = current_time - window_seconds
    recent_requests = [
        timestamp
        for timestamp in RATE_LIMIT_STORAGE.get(client_id, [])
        if timestamp > window_start
    ]

    if len(recent_requests) >= max_requests:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait before trying again.",
        )

    recent_requests.append(current_time)
    RATE_LIMIT_STORAGE[client_id] = recent_requests


def protect_request(request, provided_api_key):
    client_name = require_api_key(provided_api_key)
    enforce_rate_limit(f"{get_client_id(request)}:{client_name}")
    return client_name


def get_public_base_url():
    return os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def get_checkout_success_url():
    default_url = f"{get_public_base_url()}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    return os.getenv("CHECKOUT_SUCCESS_URL", default_url)


def get_checkout_cancel_url():
    default_url = f"{get_public_base_url()}/billing/cancel"
    return os.getenv("CHECKOUT_CANCEL_URL", default_url)


def get_billing_claim_ttl_seconds():
    return get_env_int("BILLING_CLAIM_TTL_SECONDS", 86400)


def require_stripe_config():
    if stripe is None:
        raise HTTPException(
            status_code=503,
            detail="Stripe support is not installed. Install the stripe package.",
        )

    secret_key = os.getenv("STRIPE_SECRET_KEY")
    price_id = os.getenv("STRIPE_PRICE_ID")
    if not secret_key or not price_id:
        raise HTTPException(
            status_code=503,
            detail="Stripe billing is not configured. Set STRIPE_SECRET_KEY and STRIPE_PRICE_ID.",
        )

    stripe.api_key = secret_key
    return price_id


def object_get(item, key, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def generate_paid_api_key():
    return f"bf_live_{secrets.token_urlsafe(24)}"


def make_paid_key_name(email, stripe_session_id):
    identifier = (email or stripe_session_id or "client").strip().lower()
    return f"paid:{identifier}"


def provision_paid_api_key(
    email,
    stripe_session_id,
    stripe_customer_id=None,
    stripe_subscription_id=None,
    now=None,
):
    if not stripe_session_id:
        raise ValueError("Stripe session id is required")

    records = get_api_key_records()
    existing_record = next(
        (
            record
            for record in records
            if record.get("stripe_session_id") == stripe_session_id
        ),
        None,
    )
    if existing_record:
        return {
            "status": "already_provisioned",
            "name": existing_record.get("name", "paid:client"),
        }

    created_at = int(now if now is not None else time.time())
    raw_api_key = generate_paid_api_key()
    name = make_paid_key_name(email, stripe_session_id)
    records.append(
        {
            "name": name,
            "hash": hash_api_key(raw_api_key),
            "status": "active",
            "source": "stripe",
            "email": email or "",
            "stripe_session_id": stripe_session_id,
            "stripe_customer_id": stripe_customer_id or "",
            "stripe_subscription_id": stripe_subscription_id or "",
            "created_at": created_at,
        }
    )
    save_api_key_records(records)

    claims = [
        claim
        for claim in get_billing_claim_records()
        if claim.get("session_id") != stripe_session_id
    ]
    claims.append(
        {
            "session_id": stripe_session_id,
            "api_key": raw_api_key,
            "email": email or "",
            "created_at": created_at,
            "claimed_at": None,
        }
    )
    save_billing_claim_records(claims)

    return {
        "status": "provisioned",
        "name": name,
        "api_key": raw_api_key,
    }


def claim_paid_api_key(stripe_session_id, now=None):
    if not stripe_session_id:
        return {"status": "missing_session"}

    current_time = int(now if now is not None else time.time())
    ttl_seconds = get_billing_claim_ttl_seconds()
    claims = get_billing_claim_records()
    result = {"status": "pending"}
    changed = False

    for claim in claims:
        if claim.get("session_id") != stripe_session_id:
            continue

        if claim.get("claimed_at"):
            result = {"status": "claimed"}
            break

        created_at = int(claim.get("created_at", 0))
        if current_time - created_at > ttl_seconds:
            claim["api_key"] = None
            claim["expired_at"] = current_time
            result = {"status": "expired"}
            changed = True
            break

        api_key = claim.get("api_key")
        claim["claimed_at"] = current_time
        result = {
            "status": "ready",
            "api_key": api_key,
            "email": claim.get("email", ""),
        }
        changed = True
        break

    if changed:
        save_billing_claim_records(claims)

    return result


def deactivate_paid_api_keys(stripe_subscription_id=None, stripe_customer_id=None, now=None):
    if not stripe_subscription_id and not stripe_customer_id:
        return 0

    current_time = int(now if now is not None else time.time())
    records = get_api_key_records()
    updated_count = 0

    for record in records:
        subscription_matches = (
            stripe_subscription_id
            and record.get("stripe_subscription_id") == stripe_subscription_id
        )
        customer_matches = (
            stripe_customer_id
            and record.get("stripe_customer_id") == stripe_customer_id
        )
        if record.get("source") == "stripe" and (subscription_matches or customer_matches):
            if record.get("status", "active") != "inactive":
                record["status"] = "inactive"
                record["deactivated_at"] = current_time
                updated_count += 1

    if updated_count:
        save_api_key_records(records)

    return updated_count


def get_checkout_session_email(session):
    customer_details = object_get(session, "customer_details", {}) or {}
    return (
        object_get(customer_details, "email")
        or object_get(session, "customer_email")
        or ""
    )


def handle_stripe_event(event):
    event_type = object_get(event, "type")
    data = object_get(event, "data", {}) or {}
    stripe_object = object_get(data, "object", {}) or {}

    if event_type == "checkout.session.completed":
        payment_status = object_get(stripe_object, "payment_status")
        if payment_status not in ("paid", "no_payment_required"):
            return {
                "received": True,
                "handled": True,
                "provisioned": False,
                "reason": "checkout_not_paid",
            }

        provisioned = provision_paid_api_key(
            email=get_checkout_session_email(stripe_object),
            stripe_session_id=object_get(stripe_object, "id"),
            stripe_customer_id=object_get(stripe_object, "customer"),
            stripe_subscription_id=object_get(stripe_object, "subscription"),
        )
        return {
            "received": True,
            "handled": True,
            "provisioned": provisioned.get("status") == "provisioned",
        }

    if event_type == "customer.subscription.deleted":
        updated_count = deactivate_paid_api_keys(
            stripe_subscription_id=object_get(stripe_object, "id"),
            stripe_customer_id=object_get(stripe_object, "customer"),
        )
        return {
            "received": True,
            "handled": True,
            "deactivated_keys": updated_count,
        }

    return {"received": True, "handled": False}


def get_summary_for_files(file_paths, column):
    results = []
    grand_total = 0.0

    for file_path in file_paths:
        summary = summarize_csv_column(file_path, column)
        total = summary["sum"]
        grand_total += total
        results.append(
            {
                "file": Path(file_path).name,
                "total": total,
                "rows": summary["rows"],
            }
        )

    return results, grand_total


def format_report_money(value):
    return f"R{float(value):,.2f}"


def build_client_report_payload(file_paths, column, source):
    files, grand_total = get_summary_for_files(file_paths, column)
    file_count = len(files)
    average_total = grand_total / file_count if file_count else 0
    max_total = max((item["total"] for item in files), default=0)

    return {
        "title": "Financial CSV Summary Report",
        "column": column,
        "source": source,
        "generated_at": int(time.time()),
        "file_count": file_count,
        "grand_total": grand_total,
        "average_total_per_file": average_total,
        "max_total": max_total,
        "files": files,
    }


def render_client_report_html(report):
    generated_at = time.strftime(
        "%Y-%m-%d %H:%M UTC",
        time.gmtime(report["generated_at"]),
    )
    rows = []
    bars = []
    max_total = report["max_total"]

    for item in report["files"]:
        file_name = html.escape(item["file"])
        total = float(item["total"])
        width = (total / max_total) * 100 if max_total else 0
        rows.append(
            "<tr>"
            f"<td>{file_name}</td>"
            f"<td>{int(item['rows'])}</td>"
            f"<td>{format_report_money(total)}</td>"
            "</tr>"
        )
        bars.append(
            "<div class=\"bar-row\">"
            f"<span>{file_name}</span>"
            "<div class=\"bar-track\">"
            f"<div class=\"bar-fill\" style=\"width:{width:.2f}%\"></div>"
            "</div>"
            f"<strong>{format_report_money(total)}</strong>"
            "</div>"
        )

    return f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{html.escape(report["title"])}</title>
        <style>
            :root {{
                --ink: #172633;
                --muted: #5c6974;
                --line: #d9e1df;
                --green: #0d6f57;
                --blue: #235c7a;
                --paper: #fffdf8;
                --wash: #eef7f4;
            }}
            * {{ box-sizing: border-box; }}
            body {{
                margin: 0;
                color: var(--ink);
                background: #f4f2ec;
                font-family: Georgia, "Times New Roman", serif;
                line-height: 1.5;
            }}
            main {{
                width: min(980px, calc(100% - 32px));
                margin: 24px auto;
                background: var(--paper);
                border: 1px solid var(--line);
                border-radius: 8px;
                overflow: hidden;
            }}
            header {{
                background: var(--ink);
                color: white;
                padding: 28px;
            }}
            h1, h2, p {{ margin-top: 0; }}
            h1 {{ font-size: clamp(2rem, 4vw, 3.4rem); line-height: 1; margin-bottom: 12px; }}
            section {{ padding: 26px 28px; border-top: 1px solid var(--line); }}
            .meta, .stats {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 12px;
            }}
            .stat {{
                background: var(--wash);
                border: 1px solid var(--line);
                border-radius: 8px;
                padding: 14px;
            }}
            .stat strong {{ display: block; color: var(--muted); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.08em; }}
            .stat span {{ display: block; font-size: 1.4rem; margin-top: 4px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 12px; border-bottom: 1px solid var(--line); text-align: left; }}
            th {{ color: var(--muted); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.08em; }}
            .bar-row {{ display: grid; grid-template-columns: minmax(150px, 1fr) 2fr auto; gap: 12px; align-items: center; margin-bottom: 12px; }}
            .bar-track {{ height: 12px; background: #dce8e4; border-radius: 999px; overflow: hidden; }}
            .bar-fill {{ height: 100%; background: linear-gradient(90deg, var(--green), var(--blue)); border-radius: 999px; }}
            .actions {{ display: flex; gap: 12px; flex-wrap: wrap; }}
            button {{
                border: 0;
                border-radius: 6px;
                padding: 12px 16px;
                color: white;
                background: var(--green);
                font: inherit;
                cursor: pointer;
            }}
            @media (max-width: 760px) {{
                .meta, .stats, .bar-row {{ grid-template-columns: 1fr; }}
            }}
            @media print {{
                body {{ background: white; }}
                main {{ width: 100%; margin: 0; border: 0; }}
                .actions {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <main>
            <header>
                <h1>{html.escape(report["title"])}</h1>
                <p>Clean summary and batch analytics for uploaded CSV financial data.</p>
                <div class="meta">
                    <div><strong>Generated</strong><br>{generated_at}</div>
                    <div><strong>Column</strong><br>{html.escape(report["column"])}</div>
                    <div><strong>Source</strong><br>{html.escape(report["source"])}</div>
                </div>
            </header>
            <section class="stats">
                <div class="stat"><strong>Files</strong><span>{report["file_count"]}</span></div>
                <div class="stat"><strong>Grand Total</strong><span>{format_report_money(report["grand_total"])}</span></div>
                <div class="stat"><strong>Average Per File</strong><span>{format_report_money(report["average_total_per_file"])}</span></div>
            </section>
            <section>
                <h2>Batch Contribution</h2>
                {''.join(bars)}
            </section>
            <section>
                <h2>File Detail</h2>
                <table>
                    <thead><tr><th>File</th><th>Numeric Rows</th><th>Total</th></tr></thead>
                    <tbody>{''.join(rows)}</tbody>
                </table>
            </section>
            <section class="actions">
                <button type="button" onclick="window.print()">Print or Save PDF</button>
            </section>
        </main>
    </body>
    </html>
    """


@app.get("/")
def root():
    return {
        "service": "backend-foundations-api",
        "status": "ok",
        "version": API_VERSION,
        "docs": "/docs",
        "status_url": "/status",
    }


@app.get("/status")
def status():
    checkout_configured = bool(os.getenv("STRIPE_SECRET_KEY") and os.getenv("STRIPE_PRICE_ID"))
    return {
        "service": "backend-foundations-api",
        "status": "ok",
        "version": API_VERSION,
        "environment": os.getenv("ENV", "development"),
        "storage": {
            "upload_folder_ready": UPLOAD_FOLDER.exists(),
            "data_folder_ready": DATA_FOLDER.exists(),
            "uploaded_file_count": len(get_upload_records()),
        },
        "limits": {
            "max_upload_bytes": get_max_upload_bytes(),
            "rate_limit_max_requests": get_rate_limit_max_requests(),
            "rate_limit_window_seconds": get_rate_limit_window_seconds(),
            "local_folder_batch_enabled": allow_local_folder_batch(),
        },
        "billing": {
            "stripe_installed": stripe is not None,
            "checkout_configured": checkout_configured,
            "webhook_configured": bool(os.getenv("STRIPE_WEBHOOK_SECRET")),
        },
    }


@app.post("/billing/checkout")
def create_checkout_session(payload: dict | None = Body(default=None)):
    price_id = require_stripe_config()
    payload = payload or {}
    email = str(payload.get("email", "")).strip()

    checkout_payload = {
        "success_url": get_checkout_success_url(),
        "cancel_url": get_checkout_cancel_url(),
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "allow_promotion_codes": True,
        "metadata": {
            "product": "backend-foundations",
            "provision": "api_key",
        },
    }
    if email:
        checkout_payload["customer_email"] = email
        checkout_payload["client_reference_id"] = email

    try:
        session = stripe.checkout.Session.create(**checkout_payload)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Stripe checkout session could not be created: {exc}",
        ) from exc

    return {
        "checkout_url": object_get(session, "url"),
        "session_id": object_get(session, "id"),
    }


@app.post("/billing/webhook")
async def stripe_billing_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
):
    if stripe is None:
        raise HTTPException(
            status_code=503,
            detail="Stripe support is not installed. Install the stripe package.",
        )

    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(
            status_code=503,
            detail="Stripe webhook verification is not configured. Set STRIPE_WEBHOOK_SECRET.",
        )
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe webhook signature.")

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload,
            stripe_signature,
            webhook_secret,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook payload.") from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature.") from exc

    return handle_stripe_event(event)


@app.get("/billing/api-key")
def get_claimed_billing_api_key(session_id: str):
    result = claim_paid_api_key(session_id)
    messages = {
        "pending": "Payment succeeded, but access is still being provisioned. Try again in a moment.",
        "claimed": "This checkout session's API key has already been claimed.",
        "expired": "This checkout session's API key claim has expired. Contact support to reissue access.",
        "missing_session": "Missing checkout session id.",
    }
    if result["status"] == "ready":
        return result
    return {
        "status": result["status"],
        "message": messages.get(result["status"], "API key is not available yet."),
    }


@app.get("/billing/success", response_class=HTMLResponse)
def billing_success(session_id: str):
    result = get_claimed_billing_api_key(session_id)
    title = "Backend Foundations access"
    if result["status"] == "ready":
        api_key = html.escape(result["api_key"])
        body = (
            "<p>Your paid access is active. Copy this API key now; it is only shown once.</p>"
            f"<code>{api_key}</code>"
            "<p>Paste it into the dashboard API key field and save it.</p>"
        )
    else:
        message = html.escape(result.get("message", "Access is not ready yet."))
        body = f"<p>{message}</p><p>Refresh this page after the webhook finishes.</p>"

    return HTMLResponse(
        f"""
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{title}</title>
            <style>
                body {{ font-family: Georgia, serif; margin: 0; padding: 40px; color: #1b2b39; background: #f8f5ee; }}
                main {{ max-width: 720px; margin: 0 auto; background: white; border: 1px solid #ddd7cc; border-radius: 18px; padding: 28px; }}
                code {{ display: block; overflow-wrap: anywhere; background: #e4f4ed; padding: 16px; border-radius: 10px; }}
            </style>
        </head>
        <body><main><h1>{title}</h1>{body}</main></body>
        </html>
        """
    )


@app.get("/billing/cancel", response_class=HTMLResponse)
def billing_cancel():
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="en">
        <head><meta charset="utf-8"><title>Checkout cancelled</title></head>
        <body style="font-family: Georgia, serif; padding: 40px;">
            <main style="max-width: 720px; margin: 0 auto;">
                <h1>Checkout cancelled</h1>
                <p>No payment was completed and no API key was created.</p>
            </main>
        </body>
        </html>
        """
    )


@app.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None),
):
    client_name = protect_request(request, x_api_key)

    safe_name = Path(file.filename or "upload.csv").name
    if not safe_name.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV uploads are supported.")

    destination = UPLOAD_FOLDER / safe_name
    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    validate_csv_upload(content)

    with destination.open("wb") as file_handle:
        file_handle.write(content)

    record_upload(safe_name, len(content), client_name)

    return {
        "filename": safe_name,
        "path": str(destination),
        "size": len(content),
        "message": "Upload complete.",
        "uploaded_by": client_name,
    }


@app.post("/sources/csv-url")
def import_csv_source(
    request: Request,
    payload: dict = Body(...),
    x_api_key: str | None = Header(default=None),
):
    client_name = protect_request(request, x_api_key)
    source_url = str(payload.get("url", "")).strip()

    if not source_url:
        raise HTTPException(status_code=400, detail="Provide a CSV source URL.")

    safe_name = build_source_filename(source_url, payload.get("filename"))
    content = fetch_csv_source(source_url)
    destination = UPLOAD_FOLDER / safe_name

    with destination.open("wb") as file_handle:
        file_handle.write(content)

    record_upload(
        safe_name,
        len(content),
        client_name,
        source_url=source_url,
        source_type="csv_url",
        refreshed_at=int(time.time()),
    )

    return {
        "filename": safe_name,
        "path": str(destination),
        "size": len(content),
        "message": "CSV source imported.",
        "uploaded_by": client_name,
        "source_url": source_url,
    }


@app.post("/sources/refresh")
def refresh_csv_sources(
    request: Request,
    payload: dict | None = Body(default=None),
    x_api_key: str | None = Header(default=None),
):
    client_name = protect_request(request, x_api_key)
    payload = payload or {}
    requested_names = parse_filename_list(
        payload.get("filenames") or payload.get("files")
    )
    source_records = get_connected_source_records(requested_names)
    found_names = {Path(record["filename"]).name for record in source_records}
    failed = [
        {
            "filename": filename,
            "error": "No connected CSV source is saved for this file.",
        }
        for filename in requested_names
        if filename not in found_names
    ]

    refreshed = []
    refresh_time = int(time.time())
    for record in source_records:
        try:
            refreshed.append(
                refresh_connected_csv_source(record, client_name, refresh_time)
            )
        except HTTPException as exc:
            failed.append(
                {
                    "filename": Path(str(record.get("filename", ""))).name,
                    "error": exc.detail,
                }
            )
        except Exception as exc:
            failed.append(
                {
                    "filename": Path(str(record.get("filename", ""))).name,
                    "error": str(exc),
                }
            )

    if refreshed:
        message = f"Refreshed {len(refreshed)} connected CSV source(s)."
    elif failed:
        message = "No connected CSV sources were refreshed."
    else:
        message = "No connected CSV sources are saved yet."

    return {
        "refreshed": refreshed,
        "failed": failed,
        "source_count": len(source_records),
        "message": message,
    }


@app.get("/files")
def list_uploaded_files(
    request: Request,
    x_api_key: str | None = Header(default=None),
):
    protect_request(request, x_api_key)
    return {"files": get_upload_records()}


@app.get("/dashboard-summary")
def dashboard_summary(
    request: Request,
    x_api_key: str | None = Header(default=None),
):
    protect_request(request, x_api_key)
    return build_dashboard_summary()


@app.get("/summary")
def get_summary(
    request: Request,
    file: str,
    column: str,
    x_api_key: str | None = Header(default=None),
):
    protect_request(request, x_api_key)
    path = os.path.join(UPLOAD_FOLDER, Path(file).name)

    if not os.path.exists(path):
        return {"error": "File not found"}

    try:
        return summarize_csv_column(path, column)
    except Exception as exc:
        return {"error": str(exc)}


@app.get("/files/{filename}/columns")
def get_uploaded_file_columns(
    filename: str,
    request: Request,
    x_api_key: str | None = Header(default=None),
):
    protect_request(request, x_api_key)
    safe_name = Path(filename).name
    path = UPLOAD_FOLDER / safe_name

    if not path.exists():
        return {"error": "File not found"}

    try:
        return {
            "filename": safe_name,
            "columns": get_csv_columns(path),
        }
    except Exception as exc:
        return {"error": str(exc)}


@app.get("/batch-summary")
def batch_summary_endpoint(
    request: Request,
    column: str,
    folder: str | None = None,
    files: str | None = None,
    x_api_key: str | None = Header(default=None),
):
    protect_request(request, x_api_key)

    try:
        if files:
            selected_names = [item.strip() for item in files.split(",") if item.strip()]
            if not selected_names:
                return {"error": "No files selected"}

            selected_paths = []
            for name in selected_names:
                path = UPLOAD_FOLDER / Path(name).name
                if not path.exists():
                    return {"error": f"File not found: {Path(name).name}"}
                selected_paths.append(path)

            results, total = get_summary_for_files(selected_paths, column)
            source = "uploaded-files"
        else:
            if folder and not allow_local_folder_batch():
                return {
                    "error": (
                        "Local folder batch summaries are disabled in this environment. "
                        "Upload files and use the files parameter instead."
                    )
                }

            target_folder = folder or str(UPLOAD_FOLDER)
            if not os.path.exists(target_folder):
                return {"error": "Folder not found"}

            folder_results, total = batch_summarize(target_folder, column)
            results = [
                {"file": file_name, "total": total_value}
                for file_name, total_value in folder_results
            ]
            source = target_folder
    except Exception as exc:
        return {"error": str(exc)}

    return {
        "files": results,
        "grand_total": total,
        "source": source,
        "file_count": len(results),
        "average_total_per_file": total / len(results) if results else 0,
    }


@app.get("/reports/client", response_class=HTMLResponse)
def client_report(
    request: Request,
    column: str,
    files: str | None = None,
    x_api_key: str | None = Header(default=None),
):
    protect_request(request, x_api_key)

    try:
        if files:
            selected_names = [item.strip() for item in files.split(",") if item.strip()]
            if not selected_names:
                return HTMLResponse("<p>No files selected.</p>", status_code=400)

            selected_paths = []
            for name in selected_names:
                path = UPLOAD_FOLDER / Path(name).name
                if not path.exists():
                    return HTMLResponse(
                        f"<p>File not found: {html.escape(Path(name).name)}</p>",
                        status_code=404,
                    )
                selected_paths.append(path)
            source = "selected uploaded files"
        else:
            selected_paths = sorted(UPLOAD_FOLDER.glob("*.csv"))
            source = "all uploaded files"

        if not selected_paths:
            return HTMLResponse("<p>No CSV files are available for this report.</p>", status_code=404)

        report = build_client_report_payload(selected_paths, column, source)
    except Exception as exc:
        return HTMLResponse(f"<p>{html.escape(str(exc))}</p>", status_code=400)

    return HTMLResponse(
        render_client_report_html(report),
        headers={"Content-Disposition": 'inline; filename="client-financial-report.html"'},
    )


@app.delete("/files/{filename}")
def delete_uploaded_file(
    filename: str,
    request: Request,
    x_api_key: str | None = Header(default=None),
):
    protect_request(request, x_api_key)
    safe_name = Path(filename).name
    path = UPLOAD_FOLDER / safe_name

    if not path.exists():
        return {"error": "File not found"}

    path.unlink()
    remove_upload_record(safe_name)

    return {
        "deleted": True,
        "filename": safe_name,
        "message": "File deleted.",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


def run():
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("ENV", "development").lower() != "production"

    uvicorn.run("calculator.api:app", host=host, port=port, reload=reload_enabled)
