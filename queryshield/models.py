"""Data models — Pydantic for the API surface, SQLAlchemy for persistence.

The internal control-plane DB is small: agents, databases, rls_policies,
audit_log. We use SQLAlchemy 2.0 declarative + a single Engine so every
caller goes through the same connection pool.
"""
from __future__ import annotations

import enum
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from queryshield.config import get_settings

# --- Enums --------------------------------------------------------------

class QueryMode(str, enum.Enum):
    natural_language = "nl"
    structured = "structured"


class Tier(str, enum.Enum):
    starter = "starter"
    pro = "pro"
    enterprise = "enterprise"


TIER_LIMITS: Dict[str, Dict[str, int]] = {
    "starter": {"databases": 3, "queries_per_month": 1_000_000, "price_cents": 50_000},
    "pro": {"databases": 10, "queries_per_month": 10_000_000, "price_cents": 150_000},
    "enterprise": {"databases": 10_000, "queries_per_month": 1_000_000_000, "price_cents": 350_000},
}


# --- Pydantic (API surface) ---------------------------------------------

class QueryRequest(BaseModel):
    database_alias: str = Field(..., description="Alias of a database registered for this tenant.")
    query: str
    mode: QueryMode = QueryMode.natural_language
    max_rows: int = 1000
    context: Optional[str] = None


class QueryResult(BaseModel):
    query_id: str
    sql_executed: str
    rows: List[Dict[str, Any]]
    row_count: int
    cached: bool
    execution_time_ms: int


class RLSPolicy(BaseModel):
    """In-memory representation of an RLS policy.

    The DB stores the JSON form (see RLSPolicyRow); resolving a policy hands
    back this Pydantic class for the engine to consume.
    """

    agent_id: str
    database_alias: str
    allowed_schemas: List[str] = Field(default_factory=list)
    allowed_tables: List[str] = Field(default_factory=list)
    row_filters: Dict[str, str] = Field(default_factory=dict)
    read_only: bool = True


class DatabaseConfig(BaseModel):
    alias: str
    db_type: str  # "postgresql" | "mssql" | "mysql"
    schema_cache_ttl: int = 3600


class AgentRegistration(BaseModel):
    name: str
    tenant_id: str
    tier: Tier = Tier.starter


class AgentRegistrationResult(BaseModel):
    agent_id: str
    api_key: str
    tenant_id: str
    tier: Tier
    note: str = "Store the api_key now — it is shown only once."


class DatabaseRegistration(BaseModel):
    alias: str
    db_type: str
    connection_string: str  # encrypted at rest after registration
    allowed_schemas: List[str] = Field(default_factory=list)
    allowed_tables: List[str] = Field(default_factory=list)
    row_filters: Dict[str, str] = Field(default_factory=dict)


class AuditEntry(BaseModel):
    query_id: str
    agent_id: str
    tenant_id: str
    database_alias: str
    sql_executed: str
    cached: bool
    row_count: int
    execution_ms: int
    blocked_reason: Optional[str] = None
    created_at: datetime


# --- SQLAlchemy ORM -----------------------------------------------------

class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(64), primary_key=True, default=_new_id)
    name = Column(String(255), nullable=False)
    owner_email = Column(String(320), nullable=True, index=True)
    tier = Column(String(32), default="starter", nullable=False)
    stripe_customer_id = Column(String(128), nullable=True)
    stripe_subscription_id = Column(String(128), nullable=True)
    queries_used_period = Column(Integer, default=0, nullable=False)
    period_started_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class MagicLink(Base):
    """One-shot login token emailed to the tenant owner.

    The token cleartext is sent to the user; we store its sha256. Consumed
    rows are kept (not deleted) so we can detect replay attempts.
    """

    __tablename__ = "magic_links"

    id = Column(String(64), primary_key=True, default=_new_id)
    email = Column(String(320), nullable=False, index=True)
    token_hash = Column(String(128), nullable=False, unique=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Agent(Base):
    """An agent identity = an API key + RLS scope.

    api_key_hash is the storage form. The cleartext key is shown once at
    registration. The first 8 chars are kept as a prefix for log attribution.
    """

    __tablename__ = "agents"

    id = Column(String(64), primary_key=True, default=_new_id)
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    api_key_hash = Column(String(128), nullable=False, unique=True, index=True)
    api_key_prefix = Column(String(16), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class DatabaseRow(Base):
    """Per-tenant registered database. connection_blob is Fernet-encrypted."""

    __tablename__ = "databases"

    id = Column(String(64), primary_key=True, default=_new_id)
    tenant_id = Column(String(64), nullable=False, index=True)
    alias = Column(String(128), nullable=False)
    db_type = Column(String(32), nullable=False)
    connection_blob = Column(LargeBinary, nullable=False)
    schema_cache_ttl = Column(Integer, default=3600, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (Index("ix_db_tenant_alias", "tenant_id", "alias", unique=True),)


class RLSPolicyRow(Base):
    __tablename__ = "rls_policies"

    id = Column(String(64), primary_key=True, default=_new_id)
    agent_id = Column(String(64), nullable=False, index=True)
    database_alias = Column(String(128), nullable=False)
    allowed_schemas = Column(JSON, default=list, nullable=False)
    allowed_tables = Column(JSON, default=list, nullable=False)
    row_filters = Column(JSON, default=dict, nullable=False)
    read_only = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (Index("ix_rls_agent_db", "agent_id", "database_alias", unique=True),)


class AuditLog(Base):
    """Append-only. Never store rows — only metadata."""

    __tablename__ = "audit_log"

    query_id = Column(String(64), primary_key=True)
    agent_id = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    database_alias = Column(String(128), nullable=False)
    sql_executed = Column(Text, nullable=False)
    nl_query = Column(Text, nullable=True)
    cached = Column(Boolean, default=False, nullable=False)
    row_count = Column(Integer, default=0, nullable=False)
    execution_ms = Column(Integer, default=0, nullable=False)
    blocked_reason = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)


# --- Engine + session ---------------------------------------------------

_settings = get_settings()
ENGINE = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    future=True,
)
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, expire_on_commit=False, future=True)


def init_db() -> None:
    """Create tables if missing + apply lightweight column-add migrations.

    SQLAlchemy ``create_all`` is a no-op for existing tables, so when we
    add a column we have to ALTER TABLE explicitly. We keep this list short
    and idempotent — when it grows, switch to Alembic.
    """
    Base.metadata.create_all(bind=ENGINE)
    _apply_column_migrations()


def _apply_column_migrations() -> None:
    from sqlalchemy import text

    # (table, column, type) — Postgres-flavored. Each statement uses
    # ADD COLUMN IF NOT EXISTS so the boot is safe to retry.
    migrations = [
        ("tenants", "owner_email", "VARCHAR(320)"),
    ]
    dialect = ENGINE.dialect.name  # "postgresql" | "sqlite" | ...
    if dialect not in {"postgresql", "sqlite"}:
        return
    with ENGINE.begin() as conn:
        for table, column, coltype in migrations:
            if dialect == "postgresql":
                conn.execute(text(
                    f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {coltype}'
                ))
            else:
                # SQLite: PRAGMA + skip-if-exists check
                row = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
                cols = {r[1] for r in row}
                if column not in cols:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {coltype}'))
    # Best-effort index on the new column (helps the email lookup path).
    if dialect == "postgresql":
        with ENGINE.begin() as conn:
            conn.execute(text(
                'CREATE INDEX IF NOT EXISTS ix_tenants_owner_email ON tenants(owner_email)'
            ))


def generate_api_key() -> tuple[str, str, str]:
    """Returns (cleartext_key, prefix, hash)."""
    import hashlib

    raw = "qs_" + secrets.token_urlsafe(32)
    prefix = raw[:8]
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, prefix, digest


def hash_api_key(raw: str) -> str:
    import hashlib

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
