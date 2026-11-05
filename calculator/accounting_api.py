import csv
import io
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from calculator.accounting_db import (
    AuditLog,
    AuthToken,
    BankTransaction,
    Business,
    BusinessMember,
    Client,
    Expense,
    Invoice,
    InvoiceItem,
    RECEIPT_FOLDER,
    Supplier,
    User,
    create_auth_token,
    get_db_session,
    hash_password,
    hash_token,
    init_accounting_db,
    new_id,
    utc_now,
    verify_password,
)


router = APIRouter(prefix="/accounting", tags=["Accounting"])
ALLOWED_STATUSES = {"draft", "unpaid", "paid", "overdue"}
ALLOWED_LABELS = {"review-needed", "approved", "missing-info", "draft"}


def to_iso(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def money(value):
    return round(float(value or 0), 2)


def parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def invoice_totals(invoice):
    subtotal = 0.0
    tax = 0.0
    for item in invoice.items:
        line_total = float(item.quantity or 0) * float(item.price or 0)
        subtotal += line_total
        tax += line_total * (float(item.tax_rate or 0) / 100)
    return {
        "subtotal": money(subtotal),
        "tax": money(tax),
        "total": money(subtotal + tax),
    }


def expense_tax(expense):
    amount = float(expense.amount or 0)
    tax_rate = float(expense.tax_rate or 0)
    if not tax_rate:
        return 0.0
    return money(amount - amount / (1 + tax_rate / 100))


def client_name(session, client_id):
    if not client_id:
        return "Unassigned"
    client = session.get(Client, client_id)
    if not client:
        return "Unassigned"
    return client.business_name or client.name


def supplier_name(session, supplier_id, fallback=""):
    if not supplier_id:
        return fallback or "Unassigned"
    supplier = session.get(Supplier, supplier_id)
    if not supplier:
        return fallback or "Unassigned"
    return supplier.business_name or supplier.name


def is_overdue(invoice):
    if invoice.status == "paid" or not invoice.due_date:
        return False
    try:
        due_date = datetime.fromisoformat(invoice.due_date)
    except ValueError:
        return False
    return due_date.date() < datetime.now(UTC).date()


def effective_invoice_status(invoice):
    if invoice.status == "paid":
        return "paid"
    if invoice.status == "overdue" or is_overdue(invoice):
        return "overdue"
    return invoice.status or "unpaid"


def audit(session, business_id, user, action, entity, entity_id="", details=""):
    session.add(
        AuditLog(
            business_id=business_id,
            user_id=user.id if user else None,
            action=action,
            entity=entity,
            entity_id=entity_id or "",
            details=details or "",
        )
    )


def require_current_user(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_db_session),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Provide a bearer token.")
    raw_token = authorization.split(" ", 1)[1].strip()
    token = session.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == hash_token(raw_token),
            AuthToken.expires_at > utc_now(),
        )
    )
    if not token:
        raise HTTPException(status_code=401, detail="Invalid or expired bearer token.")
    user = session.get(User, token.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Token user no longer exists.")
    return user


def require_business_access(session, user, business_id):
    membership = session.scalar(
        select(BusinessMember).where(
            BusinessMember.business_id == business_id,
            BusinessMember.user_id == user.id,
        )
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Business not found.")
    business = session.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    return business


def validate_business_contact(session, business_id, model, record_id, label):
    if not record_id:
        return None
    record = session.get(model, record_id)
    if not record or record.business_id != business_id:
        raise HTTPException(status_code=400, detail=f"{label} does not belong to this business.")
    return record


def user_payload(user):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "created_at": to_iso(user.created_at),
    }


def business_payload(business):
    return {
        "id": business.id,
        "name": business.name,
        "owner": business.owner,
        "tax_rate": business.tax_rate,
        "created_at": to_iso(business.created_at),
        "updated_at": to_iso(business.updated_at),
    }


def client_payload(client):
    return {
        "id": client.id,
        "business_id": client.business_id,
        "name": client.name,
        "email": client.email,
        "phone": client.phone,
        "business_name": client.business_name,
        "tax_number": client.tax_number,
        "address": client.address,
        "created_at": to_iso(client.created_at),
        "updated_at": to_iso(client.updated_at),
    }


def supplier_payload(supplier):
    return {
        "id": supplier.id,
        "business_id": supplier.business_id,
        "name": supplier.name,
        "email": supplier.email,
        "phone": supplier.phone,
        "business_name": supplier.business_name,
        "tax_number": supplier.tax_number,
        "address": supplier.address,
        "created_at": to_iso(supplier.created_at),
        "updated_at": to_iso(supplier.updated_at),
    }


def invoice_payload(session, invoice):
    return {
        "id": invoice.id,
        "business_id": invoice.business_id,
        "client_id": invoice.client_id,
        "client_name": client_name(session, invoice.client_id),
        "number": invoice.number,
        "issue_date": invoice.issue_date,
        "due_date": invoice.due_date,
        "status": effective_invoice_status(invoice),
        "stored_status": invoice.status,
        "label": invoice.label,
        "notes": invoice.notes,
        "comments": invoice.comments,
        "created_by": invoice.created_by,
        "created_at": to_iso(invoice.created_at),
        "updated_at": to_iso(invoice.updated_at),
        "paid_at": invoice.paid_at,
        "items": [
            {
                "id": item.id,
                "description": item.description,
                "quantity": item.quantity,
                "price": item.price,
                "tax_rate": item.tax_rate,
                "position": item.position,
            }
            for item in invoice.items
        ],
        "totals": invoice_totals(invoice),
    }


def expense_payload(session, expense):
    return {
        "id": expense.id,
        "business_id": expense.business_id,
        "supplier_id": expense.supplier_id,
        "supplier_name": supplier_name(session, expense.supplier_id, expense.supplier_name),
        "date": expense.date,
        "category": expense.category,
        "amount": expense.amount,
        "tax_rate": expense.tax_rate,
        "tax_amount": expense_tax(expense),
        "payment_method": expense.payment_method,
        "notes": expense.notes,
        "comments": expense.comments,
        "deductible": expense.deductible,
        "receipt_filename": expense.receipt_filename,
        "label": expense.label,
        "created_by": expense.created_by,
        "created_at": to_iso(expense.created_at),
        "updated_at": to_iso(expense.updated_at),
    }


def audit_payload(log):
    return {
        "id": log.id,
        "business_id": log.business_id,
        "user_id": log.user_id,
        "action": log.action,
        "entity": log.entity,
        "entity_id": log.entity_id,
        "details": log.details,
        "timestamp": to_iso(log.timestamp),
    }


def bank_payload(transaction):
    return {
        "id": transaction.id,
        "business_id": transaction.business_id,
        "import_batch_id": transaction.import_batch_id,
        "date": transaction.date,
        "description": transaction.description,
        "reference": transaction.reference,
        "amount": transaction.amount,
        "status": transaction.status,
        "matched_entity_type": transaction.matched_entity_type,
        "matched_entity_id": transaction.matched_entity_id,
        "confidence": transaction.confidence,
        "notes": transaction.notes,
        "created_at": to_iso(transaction.created_at),
    }


def contact_payload_from_body(payload):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required.")
    return {
        "name": name,
        "email": str(payload.get("email", "")).strip(),
        "phone": str(payload.get("phone", "")).strip(),
        "business_name": str(payload.get("business_name") or payload.get("businessName") or "").strip(),
        "tax_number": str(payload.get("tax_number") or payload.get("taxNumber") or "").strip(),
        "address": str(payload.get("address", "")).strip(),
    }


def update_model_fields(model, values):
    for key, value in values.items():
        setattr(model, key, value)
    model.updated_at = utc_now()


def existing_value(model, field, default=None):
    if model is None:
        return default
    value = getattr(model, field, None)
    return default if value is None else value


@router.on_event("startup")
def startup_accounting_db():
    init_accounting_db()


@router.post("/auth/register")
def register(payload: dict = Body(...), session: Session = Depends(get_db_session)):
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    name = str(payload.get("name", "")).strip()
    business_name = str(payload.get("business_name") or payload.get("businessName") or "My Business").strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")
    existing = session.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists.")

    salt, password_hash = hash_password(password)
    user = User(email=email, name=name or email.split("@", 1)[0], password_hash=password_hash, password_salt=salt)
    business = Business(name=business_name, owner=user.name, tax_rate=float(payload.get("tax_rate", 15) or 15))
    session.add_all([user, business])
    session.flush()
    session.add(BusinessMember(user_id=user.id, business_id=business.id, role="owner"))
    audit(session, business.id, user, "created", "business", business.id, f"Registered {business.name}")
    token = create_auth_token(session, user)
    session.commit()
    return {"token": token, "user": user_payload(user), "business": business_payload(business)}


@router.post("/auth/login")
def login(payload: dict = Body(...), session: Session = Depends(get_db_session)):
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    user = session.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_salt, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_auth_token(session, user)
    session.commit()
    return {"token": token, "user": user_payload(user)}


@router.get("/me")
def me(current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    memberships = session.scalars(select(BusinessMember).where(BusinessMember.user_id == current_user.id)).all()
    businesses = [session.get(Business, membership.business_id) for membership in memberships]
    return {
        "user": user_payload(current_user),
        "businesses": [business_payload(business) for business in businesses if business],
    }


@router.get("/businesses")
def list_businesses(current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    memberships = session.scalars(select(BusinessMember).where(BusinessMember.user_id == current_user.id)).all()
    businesses = [session.get(Business, membership.business_id) for membership in memberships]
    return {"businesses": [business_payload(business) for business in businesses if business]}


@router.post("/businesses")
def create_business(payload: dict = Body(...), current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    name = str(payload.get("name", "")).strip()
    if not name:
        raise HTTPException(status_code=400, detail="Business name is required.")
    business = Business(
        name=name,
        owner=str(payload.get("owner", current_user.name)).strip(),
        tax_rate=float(payload.get("tax_rate", 15) or 15),
    )
    session.add(business)
    session.flush()
    session.add(BusinessMember(user_id=current_user.id, business_id=business.id, role="owner"))
    audit(session, business.id, current_user, "created", "business", business.id, business.name)
    session.commit()
    return business_payload(business)


@router.get("/businesses/{business_id}")
def get_business(business_id: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    business = require_business_access(session, current_user, business_id)
    return business_payload(business)


@router.patch("/businesses/{business_id}")
def update_business(business_id: str, payload: dict = Body(...), current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    business = require_business_access(session, current_user, business_id)
    if "name" in payload:
        business.name = str(payload["name"]).strip() or business.name
    if "owner" in payload:
        business.owner = str(payload["owner"]).strip()
    if "tax_rate" in payload or "taxRate" in payload:
        business.tax_rate = float(payload.get("tax_rate", payload.get("taxRate")) or business.tax_rate)
    business.updated_at = utc_now()
    audit(session, business.id, current_user, "edited", "business", business.id, business.name)
    session.commit()
    return business_payload(business)


@router.delete("/businesses/{business_id}")
def delete_business(business_id: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    business = require_business_access(session, current_user, business_id)
    audit(session, business.id, current_user, "deleted", "business", business.id, business.name)
    session.delete(business)
    session.commit()
    return {"deleted": True, "id": business_id}


@router.get("/businesses/{business_id}/clients")
def list_clients(business_id: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    clients = session.scalars(select(Client).where(Client.business_id == business_id).order_by(Client.name)).all()
    return {"clients": [client_payload(client) for client in clients]}


@router.post("/businesses/{business_id}/clients")
def create_client(business_id: str, payload: dict = Body(...), current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    client = Client(business_id=business_id, **contact_payload_from_body(payload))
    session.add(client)
    session.flush()
    audit(session, business_id, current_user, "created", "client", client.id, client.name)
    session.commit()
    return client_payload(client)


@router.patch("/businesses/{business_id}/clients/{client_id}")
def update_client(business_id: str, client_id: str, payload: dict = Body(...), current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    client = validate_business_contact(session, business_id, Client, client_id, "Client")
    update_model_fields(client, contact_payload_from_body({**client_payload(client), **payload}))
    audit(session, business_id, current_user, "edited", "client", client.id, client.name)
    session.commit()
    return client_payload(client)


@router.delete("/businesses/{business_id}/clients/{client_id}")
def delete_client(business_id: str, client_id: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    client = validate_business_contact(session, business_id, Client, client_id, "Client")
    audit(session, business_id, current_user, "deleted", "client", client.id, client.name)
    session.delete(client)
    session.commit()
    return {"deleted": True, "id": client_id}


@router.get("/businesses/{business_id}/suppliers")
def list_suppliers(business_id: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    suppliers = session.scalars(select(Supplier).where(Supplier.business_id == business_id).order_by(Supplier.name)).all()
    return {"suppliers": [supplier_payload(supplier) for supplier in suppliers]}


@router.post("/businesses/{business_id}/suppliers")
def create_supplier(business_id: str, payload: dict = Body(...), current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    supplier = Supplier(business_id=business_id, **contact_payload_from_body(payload))
    session.add(supplier)
    session.flush()
    audit(session, business_id, current_user, "created", "supplier", supplier.id, supplier.name)
    session.commit()
    return supplier_payload(supplier)


@router.patch("/businesses/{business_id}/suppliers/{supplier_id}")
def update_supplier(business_id: str, supplier_id: str, payload: dict = Body(...), current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    supplier = validate_business_contact(session, business_id, Supplier, supplier_id, "Supplier")
    update_model_fields(supplier, contact_payload_from_body({**supplier_payload(supplier), **payload}))
    audit(session, business_id, current_user, "edited", "supplier", supplier.id, supplier.name)
    session.commit()
    return supplier_payload(supplier)


@router.delete("/businesses/{business_id}/suppliers/{supplier_id}")
def delete_supplier(business_id: str, supplier_id: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    supplier = validate_business_contact(session, business_id, Supplier, supplier_id, "Supplier")
    audit(session, business_id, current_user, "deleted", "supplier", supplier.id, supplier.name)
    session.delete(supplier)
    session.commit()
    return {"deleted": True, "id": supplier_id}


def apply_invoice_payload(invoice, payload, session, business_id, current_user):
    client_id = payload.get("client_id") or payload.get("clientId") or existing_value(invoice, "client_id")
    validate_business_contact(session, business_id, Client, client_id, "Client")
    status = str(payload.get("status", existing_value(invoice, "status", "unpaid"))).strip().lower()
    label = str(payload.get("label", existing_value(invoice, "label", "review-needed"))).strip().lower()
    if status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported invoice status.")
    if label not in ALLOWED_LABELS:
        raise HTTPException(status_code=400, detail="Unsupported invoice label.")
    values = {
        "client_id": client_id,
        "number": str(payload.get("number", existing_value(invoice, "number", ""))).strip(),
        "issue_date": str(payload.get("issue_date") or payload.get("issueDate") or existing_value(invoice, "issue_date", "")).strip(),
        "due_date": str(payload.get("due_date") or payload.get("dueDate") or existing_value(invoice, "due_date", "")).strip(),
        "status": status,
        "label": label,
        "notes": str(payload.get("notes", existing_value(invoice, "notes", ""))),
        "comments": str(payload.get("comments", existing_value(invoice, "comments", ""))),
        "created_by": existing_value(invoice, "created_by", current_user.name),
        "paid_at": str(payload.get("paid_at") or payload.get("paidAt") or existing_value(invoice, "paid_at", "")),
    }
    if not values["number"] or not values["issue_date"] or not values["due_date"]:
        raise HTTPException(status_code=400, detail="Invoice number, issue date, and due date are required.")
    return values


def replace_invoice_items(session, invoice, items):
    invoice.items.clear()
    for position, item in enumerate(items or []):
        invoice.items.append(
            InvoiceItem(
                description=str(item.get("description", "")).strip(),
                quantity=float(item.get("quantity", 0) or 0),
                price=float(item.get("price", 0) or 0),
                tax_rate=float(item.get("tax_rate", item.get("taxRate", 0)) or 0),
                position=position,
            )
        )
    if not invoice.items:
        raise HTTPException(status_code=400, detail="At least one invoice item is required.")
    session.flush()


@router.get("/businesses/{business_id}/invoices")
def list_invoices(business_id: str, status: str | None = None, search: str | None = None, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    invoices = session.scalars(select(Invoice).where(Invoice.business_id == business_id).order_by(Invoice.issue_date.desc())).all()
    if status and status != "all":
        invoices = [invoice for invoice in invoices if effective_invoice_status(invoice) == status]
    if search:
        needle = search.lower()
        invoices = [
            invoice
            for invoice in invoices
            if needle in invoice.number.lower() or needle in client_name(session, invoice.client_id).lower()
        ]
    return {"invoices": [invoice_payload(session, invoice) for invoice in invoices]}


@router.post("/businesses/{business_id}/invoices")
def create_invoice(business_id: str, payload: dict = Body(...), current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    invoice = Invoice(business_id=business_id)
    for key, value in apply_invoice_payload(invoice, payload, session, business_id, current_user).items():
        setattr(invoice, key, value)
    session.add(invoice)
    session.flush()
    replace_invoice_items(session, invoice, payload.get("items", []))
    audit(session, business_id, current_user, "created", "invoice", invoice.id, invoice.number)
    session.commit()
    return invoice_payload(session, invoice)


@router.get("/businesses/{business_id}/invoices/{invoice_id}")
def get_invoice(business_id: str, invoice_id: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.business_id != business_id:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return invoice_payload(session, invoice)


@router.patch("/businesses/{business_id}/invoices/{invoice_id}")
def update_invoice(business_id: str, invoice_id: str, payload: dict = Body(...), current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.business_id != business_id:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    for key, value in apply_invoice_payload(invoice, {**invoice_payload(session, invoice), **payload}, session, business_id, current_user).items():
        setattr(invoice, key, value)
    invoice.updated_at = utc_now()
    if "items" in payload:
        replace_invoice_items(session, invoice, payload.get("items", []))
    audit(session, business_id, current_user, "edited", "invoice", invoice.id, invoice.number)
    session.commit()
    return invoice_payload(session, invoice)


@router.patch("/businesses/{business_id}/invoices/{invoice_id}/status")
def update_invoice_status(business_id: str, invoice_id: str, payload: dict = Body(...), current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.business_id != business_id:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    status = str(payload.get("status", "")).lower()
    if status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported invoice status.")
    invoice.status = status
    invoice.paid_at = str(payload.get("paid_at") or payload.get("paidAt") or datetime.now(UTC).date()) if status == "paid" else ""
    invoice.updated_at = utc_now()
    audit(session, business_id, current_user, "updated status", "invoice", invoice.id, f"{invoice.number} -> {status}")
    session.commit()
    return invoice_payload(session, invoice)


@router.delete("/businesses/{business_id}/invoices/{invoice_id}")
def delete_invoice(business_id: str, invoice_id: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.business_id != business_id:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    audit(session, business_id, current_user, "deleted", "invoice", invoice.id, invoice.number)
    session.delete(invoice)
    session.commit()
    return {"deleted": True, "id": invoice_id}


def apply_expense_payload(expense, payload, session, business_id, current_user):
    supplier_id = payload.get("supplier_id") or payload.get("supplierId") or existing_value(expense, "supplier_id")
    validate_business_contact(session, business_id, Supplier, supplier_id, "Supplier")
    label = str(payload.get("label", existing_value(expense, "label", "review-needed"))).strip().lower()
    if label not in ALLOWED_LABELS:
        raise HTTPException(status_code=400, detail="Unsupported expense label.")
    return {
        "supplier_id": supplier_id,
        "date": str(payload.get("date", existing_value(expense, "date", ""))).strip(),
        "supplier_name": str(payload.get("supplier_name") or payload.get("supplierName") or existing_value(expense, "supplier_name", "")).strip(),
        "category": str(payload.get("category", existing_value(expense, "category", ""))).strip(),
        "amount": float(payload.get("amount", existing_value(expense, "amount", 0)) or 0),
        "tax_rate": float(payload.get("tax_rate", payload.get("taxRate", existing_value(expense, "tax_rate", 0))) or 0),
        "payment_method": str(payload.get("payment_method") or payload.get("paymentMethod") or existing_value(expense, "payment_method", "")).strip(),
        "notes": str(payload.get("notes", existing_value(expense, "notes", ""))),
        "comments": str(payload.get("comments", existing_value(expense, "comments", ""))),
        "deductible": parse_bool(payload.get("deductible"), existing_value(expense, "deductible", True)),
        "label": label,
        "created_by": existing_value(expense, "created_by", current_user.name),
    }


@router.get("/businesses/{business_id}/expenses")
def list_expenses(business_id: str, month: str | None = None, category: str | None = None, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    expenses = session.scalars(select(Expense).where(Expense.business_id == business_id).order_by(Expense.date.desc())).all()
    if month and month != "all":
        expenses = [expense for expense in expenses if expense.date.startswith(month)]
    if category and category != "all":
        expenses = [expense for expense in expenses if expense.category == category]
    return {"expenses": [expense_payload(session, expense) for expense in expenses]}


@router.post("/businesses/{business_id}/expenses")
def create_expense(business_id: str, payload: dict = Body(...), current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    expense = Expense(business_id=business_id)
    for key, value in apply_expense_payload(expense, payload, session, business_id, current_user).items():
        setattr(expense, key, value)
    if not expense.date or not expense.category:
        raise HTTPException(status_code=400, detail="Expense date and category are required.")
    session.add(expense)
    session.flush()
    audit(session, business_id, current_user, "created", "expense", expense.id, f"{expense.category} {expense.amount}")
    session.commit()
    return expense_payload(session, expense)


@router.patch("/businesses/{business_id}/expenses/{expense_id}")
def update_expense(business_id: str, expense_id: str, payload: dict = Body(...), current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    expense = session.get(Expense, expense_id)
    if not expense or expense.business_id != business_id:
        raise HTTPException(status_code=404, detail="Expense not found.")
    for key, value in apply_expense_payload(expense, {**expense_payload(session, expense), **payload}, session, business_id, current_user).items():
        setattr(expense, key, value)
    expense.updated_at = utc_now()
    audit(session, business_id, current_user, "edited", "expense", expense.id, expense.category)
    session.commit()
    return expense_payload(session, expense)


@router.delete("/businesses/{business_id}/expenses/{expense_id}")
def delete_expense(business_id: str, expense_id: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    expense = session.get(Expense, expense_id)
    if not expense or expense.business_id != business_id:
        raise HTTPException(status_code=404, detail="Expense not found.")
    audit(session, business_id, current_user, "deleted", "expense", expense.id, expense.category)
    session.delete(expense)
    session.commit()
    return {"deleted": True, "id": expense_id}


@router.post("/businesses/{business_id}/expenses/{expense_id}/receipt")
async def upload_receipt(business_id: str, expense_id: str, file: UploadFile = File(...), current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    expense = session.get(Expense, expense_id)
    if not expense or expense.business_id != business_id:
        raise HTTPException(status_code=404, detail="Expense not found.")
    safe_name = Path(file.filename or "receipt").name
    business_folder = RECEIPT_FOLDER / business_id
    business_folder.mkdir(parents=True, exist_ok=True)
    saved_name = f"{expense_id}-{safe_name}"
    destination = business_folder / saved_name
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Receipt file is empty.")
    destination.write_bytes(content)
    expense.receipt_filename = safe_name
    expense.receipt_path = str(destination)
    expense.updated_at = utc_now()
    audit(session, business_id, current_user, "uploaded", "receipt", expense.id, safe_name)
    session.commit()
    return {"filename": safe_name, "size": len(content), "expense": expense_payload(session, expense)}


def dashboard_metrics(session, business_id):
    invoices = session.scalars(select(Invoice).where(Invoice.business_id == business_id)).all()
    expenses = session.scalars(select(Expense).where(Expense.business_id == business_id)).all()
    paid = [invoice for invoice in invoices if effective_invoice_status(invoice) == "paid"]
    open_invoices = [invoice for invoice in invoices if effective_invoice_status(invoice) != "paid"]
    overdue = [invoice for invoice in invoices if effective_invoice_status(invoice) == "overdue"]
    total_income = sum(invoice_totals(invoice)["total"] for invoice in paid)
    total_expenses = sum(float(expense.amount or 0) for expense in expenses)
    output_tax = sum(invoice_totals(invoice)["tax"] for invoice in invoices)
    input_tax = sum(expense_tax(expense) for expense in expenses if expense.deductible)
    monthly_revenue = {}
    monthly_expenses = {}
    expense_categories = {}
    for invoice in paid:
        month = (invoice.paid_at or invoice.issue_date or "unknown")[:7]
        monthly_revenue[month] = monthly_revenue.get(month, 0.0) + invoice_totals(invoice)["total"]
    for expense in expenses:
        month = (expense.date or "unknown")[:7]
        monthly_expenses[month] = monthly_expenses.get(month, 0.0) + float(expense.amount or 0)
        category = expense.category or "Uncategorised"
        expense_categories[category] = expense_categories.get(category, 0.0) + float(expense.amount or 0)
    months = sorted(set(monthly_revenue) | set(monthly_expenses))
    return {
        "total_income": money(total_income),
        "total_expenses": money(total_expenses),
        "net_profit": money(total_income - total_expenses),
        "outstanding_invoices": money(sum(invoice_totals(invoice)["total"] for invoice in open_invoices)),
        "outstanding_invoice_count": len(open_invoices),
        "overdue_invoices": len(overdue),
        "overdue_invoice_total": money(sum(invoice_totals(invoice)["total"] for invoice in overdue)),
        "cash_flow_summary": money(total_income - total_expenses),
        "output_tax": money(output_tax),
        "input_tax": money(input_tax),
        "tax_estimate": money(output_tax - input_tax),
        "monthly_revenue": [{"month": month, "amount": money(monthly_revenue.get(month, 0.0))} for month in months],
        "monthly_cash_flow": [
            {
                "month": month,
                "income": money(monthly_revenue.get(month, 0.0)),
                "expenses": money(monthly_expenses.get(month, 0.0)),
                "net": money(monthly_revenue.get(month, 0.0) - monthly_expenses.get(month, 0.0)),
            }
            for month in months
        ],
        "expense_category_breakdown": [
            {"category": category, "amount": money(amount)}
            for category, amount in sorted(expense_categories.items(), key=lambda item: item[1], reverse=True)
        ],
    }


@router.get("/businesses/{business_id}/dashboard")
def dashboard(business_id: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    return dashboard_metrics(session, business_id)


def build_report(session, business_id, report_type):
    metrics = dashboard_metrics(session, business_id)
    if report_type == "sales":
        invoices = session.scalars(select(Invoice).where(Invoice.business_id == business_id).order_by(Invoice.issue_date.desc())).all()
        return {
            "title": "Sales Report",
            "headers": ["Invoice", "Client", "Date", "Status", "Total"],
            "rows": [
                [invoice.number, client_name(session, invoice.client_id), invoice.issue_date, effective_invoice_status(invoice), invoice_totals(invoice)["total"]]
                for invoice in invoices
            ],
        }
    if report_type == "expenses":
        expenses = session.scalars(select(Expense).where(Expense.business_id == business_id).order_by(Expense.date.desc())).all()
        return {
            "title": "Expense Report",
            "headers": ["Date", "Supplier", "Category", "Amount", "Tax", "Deductible"],
            "rows": [
                [expense.date, supplier_name(session, expense.supplier_id, expense.supplier_name), expense.category, expense.amount, expense_tax(expense), "Yes" if expense.deductible else "No"]
                for expense in expenses
            ],
        }
    if report_type == "tax":
        return {
            "title": "Tax/VAT Summary",
            "headers": ["Metric", "Amount"],
            "rows": [
                ["Output VAT on invoices", metrics["output_tax"]],
                ["Input VAT on deductible expenses", metrics["input_tax"]],
                ["Estimated VAT payable", metrics["tax_estimate"]],
            ],
        }
    if report_type == "cash-flow":
        return {
            "title": "Cash Flow Report",
            "headers": ["Month", "Income", "Expenses", "Net Cash Flow"],
            "rows": [
                [row["month"], row["income"], row["expenses"], row["net"]]
                for row in metrics["monthly_cash_flow"]
            ],
        }
    return {
        "title": "Profit & Loss Report",
        "headers": ["Metric", "Amount"],
        "rows": [
            ["Income", metrics["total_income"]],
            ["Expenses", metrics["total_expenses"]],
            ["Net Profit", metrics["net_profit"]],
        ],
    }


def build_report_response(business_id, report_type, current_user, session):
    require_business_access(session, current_user, business_id)
    if report_type not in {"profit-loss", "sales", "expenses", "tax", "cash-flow"}:
        raise HTTPException(status_code=400, detail="Unsupported report type.")
    normalized_type = "profit-loss" if report_type == "profit-loss" else report_type
    return build_report(session, business_id, normalized_type)


@router.get("/businesses/{business_id}/reports/{report_type}.csv")
def report_csv(business_id: str, report_type: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    report = build_report_response(business_id, report_type, current_user, session)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(report["headers"])
    writer.writerows(report["rows"])
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{report_type}-report.csv"'},
    )


def pdf_response(filename, build_story):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    doc.build(build_story())
    return Response(
        buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/businesses/{business_id}/invoices/{invoice_id}/pdf")
def invoice_pdf(business_id: str, invoice_id: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    business = require_business_access(session, current_user, business_id)
    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.business_id != business_id:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    totals = invoice_totals(invoice)
    styles = getSampleStyleSheet()

    def story():
        rows = [["Description", "Qty", "Price", "VAT", "Total"]]
        for item in invoice.items:
            line_total = float(item.quantity) * float(item.price)
            rows.append([item.description, item.quantity, f"R{item.price:,.2f}", f"{item.tax_rate:g}%", f"R{line_total:,.2f}"])
        rows.extend([["", "", "", "Subtotal", f"R{totals['subtotal']:,.2f}"], ["", "", "", "VAT/Tax", f"R{totals['tax']:,.2f}"], ["", "", "", "Total", f"R{totals['total']:,.2f}"]])
        table = Table(rows, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b6b58")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8e0e6")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        return [
            Paragraph(business.name, styles["Title"]),
            Paragraph(f"Invoice {invoice.number}", styles["Heading2"]),
            Paragraph(f"Client: {client_name(session, invoice.client_id)}", styles["Normal"]),
            Paragraph(f"Issue date: {invoice.issue_date} | Due date: {invoice.due_date} | Status: {effective_invoice_status(invoice)}", styles["Normal"]),
            Spacer(1, 18),
            table,
            Spacer(1, 18),
            Paragraph(invoice.notes or "", styles["Normal"]),
        ]

    audit(session, business_id, current_user, "exported", "invoice_pdf", invoice.id, invoice.number)
    session.commit()
    return pdf_response(f"{invoice.number}.pdf", story)


@router.get("/businesses/{business_id}/reports/{report_type}.pdf")
def report_pdf(business_id: str, report_type: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    business = require_business_access(session, current_user, business_id)
    report = build_report_response(business_id, report_type, current_user, session)
    styles = getSampleStyleSheet()

    def story():
        table = Table([report["headers"], *report["rows"]], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#235c7a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8e0e6")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]))
        return [Paragraph(business.name, styles["Title"]), Paragraph(report["title"], styles["Heading2"]), Spacer(1, 18), table]

    audit(session, business_id, current_user, "exported", "report_pdf", report_type, report["title"])
    session.commit()
    return pdf_response(f"{report_type}-report.pdf", story)


@router.get("/businesses/{business_id}/reports/{report_type}")
def report_json(business_id: str, report_type: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    return build_report_response(business_id, report_type, current_user, session)


@router.get("/businesses/{business_id}/audit-logs")
def list_audit_logs(business_id: str, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    logs = session.scalars(select(AuditLog).where(AuditLog.business_id == business_id).order_by(AuditLog.timestamp.desc())).all()
    return {"audit_logs": [audit_payload(log) for log in logs]}


def detect_csv_field(fieldnames, candidates):
    lower_map = {field.lower().strip(): field for field in fieldnames or []}
    for candidate in candidates:
        if candidate in lower_map:
            return lower_map[candidate]
    return None


def find_reconciliation_match(session, business_id, amount, description):
    description = (description or "").lower()
    if amount > 0:
        invoices = session.scalars(select(Invoice).where(Invoice.business_id == business_id)).all()
        for invoice in invoices:
            total = invoice_totals(invoice)["total"]
            if abs(total - amount) < 0.01:
                confidence = 0.9 if invoice.number.lower() in description else 0.75
                return "invoice", invoice.id, confidence
    else:
        expenses = session.scalars(select(Expense).where(Expense.business_id == business_id)).all()
        for expense in expenses:
            if abs(float(expense.amount or 0) - abs(amount)) < 0.01:
                confidence = 0.85 if expense.category.lower() in description else 0.7
                return "expense", expense.id, confidence
    return "", "", 0.0


@router.post("/businesses/{business_id}/bank-import")
async def import_bank_csv(business_id: str, file: UploadFile = File(...), current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Bank CSV file is empty.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Bank CSV must be UTF-8 text.") from exc
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    date_field = detect_csv_field(fieldnames, {"date", "transaction date", "posted date"})
    description_field = detect_csv_field(fieldnames, {"description", "details", "narrative", "memo"})
    amount_field = detect_csv_field(fieldnames, {"amount", "value", "transaction amount"})
    reference_field = detect_csv_field(fieldnames, {"reference", "ref", "transaction id"})
    if not date_field or not description_field or not amount_field:
        raise HTTPException(status_code=400, detail="Bank CSV needs date, description, and amount columns.")

    batch_id = new_id("batch")
    imported = []
    for row in reader:
        try:
            amount = float(str(row.get(amount_field, "0")).replace(",", "").strip())
        except ValueError:
            continue
        matched_type, matched_id, confidence = find_reconciliation_match(session, business_id, amount, row.get(description_field, ""))
        transaction = BankTransaction(
            business_id=business_id,
            import_batch_id=batch_id,
            date=str(row.get(date_field, "")).strip(),
            description=str(row.get(description_field, "")).strip(),
            reference=str(row.get(reference_field, "")).strip() if reference_field else "",
            amount=amount,
            status="matched" if matched_id else "unmatched",
            matched_entity_type=matched_type,
            matched_entity_id=matched_id,
            confidence=confidence,
        )
        session.add(transaction)
        imported.append(transaction)

    audit(session, business_id, current_user, "imported", "bank_csv", batch_id, f"{len(imported)} transactions")
    session.commit()
    return {"import_batch_id": batch_id, "transactions": [bank_payload(transaction) for transaction in imported]}


@router.get("/businesses/{business_id}/bank-transactions")
def list_bank_transactions(business_id: str, status: str | None = None, current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    query = select(BankTransaction).where(BankTransaction.business_id == business_id).order_by(BankTransaction.date.desc())
    transactions = session.scalars(query).all()
    if status:
        transactions = [transaction for transaction in transactions if transaction.status == status]
    return {"transactions": [bank_payload(transaction) for transaction in transactions]}


@router.patch("/businesses/{business_id}/bank-transactions/{transaction_id}/match")
def update_bank_match(business_id: str, transaction_id: str, payload: dict = Body(...), current_user: User = Depends(require_current_user), session: Session = Depends(get_db_session)):
    require_business_access(session, current_user, business_id)
    transaction = session.get(BankTransaction, transaction_id)
    if not transaction or transaction.business_id != business_id:
        raise HTTPException(status_code=404, detail="Bank transaction not found.")
    matched_type = str(payload.get("matched_entity_type") or payload.get("matchedEntityType") or "").strip()
    matched_id = str(payload.get("matched_entity_id") or payload.get("matchedEntityId") or "").strip()
    if matched_type not in {"invoice", "expense", ""}:
        raise HTTPException(status_code=400, detail="Match type must be invoice, expense, or empty.")
    if matched_type == "invoice":
        invoice = session.get(Invoice, matched_id)
        if not invoice or invoice.business_id != business_id:
            raise HTTPException(status_code=404, detail="Invoice match not found.")
    if matched_type == "expense":
        expense = session.get(Expense, matched_id)
        if not expense or expense.business_id != business_id:
            raise HTTPException(status_code=404, detail="Expense match not found.")
    transaction.matched_entity_type = matched_type
    transaction.matched_entity_id = matched_id
    transaction.status = "matched" if matched_type and matched_id else "unmatched"
    transaction.confidence = float(payload.get("confidence", 1.0 if transaction.status == "matched" else 0.0))
    transaction.notes = str(payload.get("notes", transaction.notes or ""))
    audit(session, business_id, current_user, "matched", "bank_transaction", transaction.id, transaction.status)
    session.commit()
    return bank_payload(transaction)
