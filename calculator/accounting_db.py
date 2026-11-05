import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FOLDER = BASE_DIR / "data"
DATA_FOLDER.mkdir(exist_ok=True)
RECEIPT_FOLDER = DATA_FOLDER / "receipts"
RECEIPT_FOLDER.mkdir(exist_ok=True)

_ENGINE = None
_SESSION_LOCAL = None


def utc_now():
    return datetime.now(UTC)


def new_id(prefix):
    return f"{prefix}_{secrets.token_urlsafe(12)}"


def get_accounting_database_url():
    configured = os.getenv("ACCOUNTING_DATABASE_URL") or os.getenv("DATABASE_URL")
    if configured:
        if configured.startswith("postgres://"):
            return configured.replace("postgres://", "postgresql+psycopg://", 1)
        if configured.startswith("postgresql://") and "+psycopg" not in configured:
            return configured.replace("postgresql://", "postgresql+psycopg://", 1)
        return configured
    return f"sqlite:///{DATA_FOLDER / 'accounting.sqlite3'}"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "accounting_users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("user"))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    password_salt: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    memberships: Mapped[list["BusinessMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthToken(Base):
    __tablename__ = "accounting_auth_tokens"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("token"))
    user_id: Mapped[str] = mapped_column(ForeignKey("accounting_users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Business(Base):
    __tablename__ = "accounting_businesses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("biz"))
    name: Mapped[str] = mapped_column(String(255))
    owner: Mapped[str] = mapped_column(String(255), default="")
    tax_rate: Mapped[float] = mapped_column(Float, default=15.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    memberships: Mapped[list["BusinessMember"]] = relationship(back_populates="business", cascade="all, delete-orphan")
    clients: Mapped[list["Client"]] = relationship(back_populates="business", cascade="all, delete-orphan")
    suppliers: Mapped[list["Supplier"]] = relationship(back_populates="business", cascade="all, delete-orphan")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="business", cascade="all, delete-orphan")
    expenses: Mapped[list["Expense"]] = relationship(back_populates="business", cascade="all, delete-orphan")


class BusinessMember(Base):
    __tablename__ = "accounting_business_members"
    __table_args__ = (UniqueConstraint("business_id", "user_id", name="uq_business_user"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("member"))
    business_id: Mapped[str] = mapped_column(ForeignKey("accounting_businesses.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("accounting_users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(64), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    business: Mapped[Business] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship(back_populates="memberships")


class Client(Base):
    __tablename__ = "accounting_clients"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("client"))
    business_id: Mapped[str] = mapped_column(ForeignKey("accounting_businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(80), default="")
    business_name: Mapped[str] = mapped_column(String(255), default="")
    tax_number: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    business: Mapped[Business] = relationship(back_populates="clients")


class Supplier(Base):
    __tablename__ = "accounting_suppliers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("supplier"))
    business_id: Mapped[str] = mapped_column(ForeignKey("accounting_businesses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(80), default="")
    business_name: Mapped[str] = mapped_column(String(255), default="")
    tax_number: Mapped[str] = mapped_column(String(120), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    business: Mapped[Business] = relationship(back_populates="suppliers")


class Invoice(Base):
    __tablename__ = "accounting_invoices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("inv"))
    business_id: Mapped[str] = mapped_column(ForeignKey("accounting_businesses.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[str | None] = mapped_column(ForeignKey("accounting_clients.id", ondelete="SET NULL"), nullable=True)
    number: Mapped[str] = mapped_column(String(120), index=True)
    issue_date: Mapped[str] = mapped_column(String(10))
    due_date: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(32), default="unpaid")
    label: Mapped[str] = mapped_column(String(64), default="review-needed")
    notes: Mapped[str] = mapped_column(Text, default="")
    comments: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    paid_at: Mapped[str] = mapped_column(String(10), default="")

    business: Mapped[Business] = relationship(back_populates="invoices")
    items: Mapped[list["InvoiceItem"]] = relationship(back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceItem.position")


class InvoiceItem(Base):
    __tablename__ = "accounting_invoice_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("item"))
    invoice_id: Mapped[str] = mapped_column(ForeignKey("accounting_invoices.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.0)
    position: Mapped[int] = mapped_column(Integer, default=0)

    invoice: Mapped[Invoice] = relationship(back_populates="items")


class Expense(Base):
    __tablename__ = "accounting_expenses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("exp"))
    business_id: Mapped[str] = mapped_column(ForeignKey("accounting_businesses.id", ondelete="CASCADE"), index=True)
    supplier_id: Mapped[str | None] = mapped_column(ForeignKey("accounting_suppliers.id", ondelete="SET NULL"), nullable=True)
    date: Mapped[str] = mapped_column(String(10))
    supplier_name: Mapped[str] = mapped_column(String(255), default="")
    category: Mapped[str] = mapped_column(String(120), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.0)
    payment_method: Mapped[str] = mapped_column(String(80), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    comments: Mapped[str] = mapped_column(Text, default="")
    deductible: Mapped[bool] = mapped_column(Boolean, default=True)
    receipt_filename: Mapped[str] = mapped_column(String(255), default="")
    receipt_path: Mapped[str] = mapped_column(String(500), default="")
    label: Mapped[str] = mapped_column(String(64), default="review-needed")
    created_by: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    business: Mapped[Business] = relationship(back_populates="expenses")


class AuditLog(Base):
    __tablename__ = "accounting_audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("audit"))
    business_id: Mapped[str] = mapped_column(ForeignKey("accounting_businesses.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("accounting_users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(120))
    entity: Mapped[str] = mapped_column(String(120))
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    details: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class BankTransaction(Base):
    __tablename__ = "accounting_bank_transactions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("bank"))
    business_id: Mapped[str] = mapped_column(ForeignKey("accounting_businesses.id", ondelete="CASCADE"), index=True)
    import_batch_id: Mapped[str] = mapped_column(String(64), index=True)
    date: Mapped[str] = mapped_column(String(10))
    description: Mapped[str] = mapped_column(Text, default="")
    reference: Mapped[str] = mapped_column(String(255), default="")
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="unmatched")
    matched_entity_type: Mapped[str] = mapped_column(String(32), default="")
    matched_entity_id: Mapped[str] = mapped_column(String(64), default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


def get_engine():
    global _ENGINE
    if _ENGINE is None:
        database_url = get_accounting_database_url()
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        _ENGINE = create_engine(database_url, connect_args=connect_args, future=True)
    return _ENGINE


def get_session_factory():
    global _SESSION_LOCAL
    if _SESSION_LOCAL is None:
        _SESSION_LOCAL = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False, future=True)
    return _SESSION_LOCAL


def init_accounting_db():
    Base.metadata.create_all(bind=get_engine())


def get_db_session():
    init_accounting_db()
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def reset_accounting_engine_for_tests():
    global _ENGINE, _SESSION_LOCAL
    if _ENGINE is not None:
        _ENGINE.dispose()
    _ENGINE = None
    _SESSION_LOCAL = None


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    ).hex()
    return salt, password_hash


def verify_password(password, salt, password_hash):
    _, candidate_hash = hash_password(password, salt=salt)
    return secrets.compare_digest(candidate_hash, password_hash)


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_auth_token(session, user, ttl_hours=24):
    raw_token = f"bfacct_{secrets.token_urlsafe(32)}"
    token = AuthToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=utc_now() + timedelta(hours=ttl_hours),
    )
    session.add(token)
    return raw_token
