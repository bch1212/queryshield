"""Credential vault — Fernet-encrypted connection strings stored in our
internal Postgres.

The build prompt called for AWS Secrets Manager, but Brett's stack runs on
Railway without AWS provisioned. Postgres + Fernet gives us the same
property the threat model actually demands: connection strings are never
visible to agents, never returned by any API, and at-rest in the audit DB
they're symmetrically encrypted with a key only the application process
holds.

VAULT_KEY is a Fernet key (urlsafe base64). Generate once with::

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Rotate by re-encrypting each row under a new key in a one-shot script;
losing the key = losing access to every registered DB.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select

from queryshield.config import get_settings
from queryshield.models import DatabaseRow, SessionLocal

log = logging.getLogger("queryshield.vault")


def _fernet() -> Fernet:
    key = get_settings().vault_key
    if not key:
        # In dev, fall back to a deterministic key so local boots work.
        # In production the startup config check refuses to start without one.
        key = "dev-only-vault-key-do-not-use-in-prod-dev-only-vault-key="
    return Fernet(key.encode("utf-8") if isinstance(key, str) else key)


def encrypt_connection(payload: dict) -> bytes:
    """Encrypt a connection-info dict.

    payload schema::
        {"type": "postgresql"|"mssql"|"mysql", "url": "...", "dsn": "..."}
    """
    blob = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return _fernet().encrypt(blob)


def decrypt_connection(blob: bytes) -> dict:
    try:
        plain = _fernet().decrypt(blob)
    except InvalidToken as e:
        raise RuntimeError("vault: cannot decrypt — VAULT_KEY mismatch") from e
    return json.loads(plain)


# --- Convenience: alias-keyed lookup -------------------------------------

async def get_connection_string(tenant_id: str, alias: str) -> dict:
    """Returns the decrypted connection-info dict for ``tenant.alias``.

    Async signature only because the proxy is async; the underlying call is
    synchronous SQLAlchemy.
    """
    with SessionLocal() as session:
        row = session.execute(
            select(DatabaseRow).where(
                DatabaseRow.tenant_id == tenant_id,
                DatabaseRow.alias == alias,
            )
        ).scalar_one_or_none()

    if row is None:
        raise KeyError(f"no database registered with alias '{alias}' for this tenant")
    return decrypt_connection(row.connection_blob)


def store_connection(
    tenant_id: str,
    alias: str,
    db_type: str,
    connection_string: str,
    schema_cache_ttl: int = 3600,
) -> str:
    """Store an encrypted connection string. Returns the row id.

    Idempotent on (tenant_id, alias): re-storing replaces the blob.
    """
    payload = _normalize_connection(db_type, connection_string)
    blob = encrypt_connection(payload)

    with SessionLocal() as session:
        existing = session.execute(
            select(DatabaseRow).where(
                DatabaseRow.tenant_id == tenant_id,
                DatabaseRow.alias == alias,
            )
        ).scalar_one_or_none()

        if existing is not None:
            existing.connection_blob = blob
            existing.db_type = db_type
            existing.schema_cache_ttl = schema_cache_ttl
            session.commit()
            log.info("vault: replaced credentials for %s/%s", tenant_id, alias)
            return existing.id

        row = DatabaseRow(
            tenant_id=tenant_id,
            alias=alias,
            db_type=db_type,
            connection_blob=blob,
            schema_cache_ttl=schema_cache_ttl,
        )
        session.add(row)
        session.commit()
        log.info("vault: stored new credentials for %s/%s", tenant_id, alias)
        return row.id


def _normalize_connection(db_type: str, connection_string: str) -> dict:
    """Wrap raw connection strings in a structured payload.

    For postgresql/mysql, ``url`` is the SQLAlchemy/asyncpg-compatible URL.
    For mssql, ``dsn`` is the pyodbc connection string.
    """
    db_type = db_type.lower()
    if db_type in {"postgresql", "postgres", "pg", "mysql"}:
        return {"type": "postgresql" if db_type != "mysql" else "mysql", "url": connection_string}
    if db_type in {"mssql", "sqlserver"}:
        return {"type": "mssql", "dsn": connection_string}
    if db_type in {"sqlite", "sqlite3"}:
        return {"type": "sqlite", "path": connection_string}
    raise ValueError(f"unsupported db_type: {db_type}")


def list_databases(tenant_id: str) -> list[dict]:
    """Return per-tenant alias listing — never returns credential blobs."""
    with SessionLocal() as session:
        rows = session.execute(
            select(DatabaseRow).where(DatabaseRow.tenant_id == tenant_id)
        ).scalars().all()
    return [
        {
            "alias": r.alias,
            "db_type": r.db_type,
            "schema_cache_ttl": r.schema_cache_ttl,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def delete_database(tenant_id: str, alias: str) -> bool:
    with SessionLocal() as session:
        row = session.execute(
            select(DatabaseRow).where(
                DatabaseRow.tenant_id == tenant_id,
                DatabaseRow.alias == alias,
            )
        ).scalar_one_or_none()
        if row is None:
            return False
        session.delete(row)
        session.commit()
    return True


def find_database_metadata(tenant_id: str, alias: str) -> Optional[DatabaseRow]:
    """Returns the ORM row (without decrypting the blob) for type/ttl lookup."""
    with SessionLocal() as session:
        return session.execute(
            select(DatabaseRow).where(
                DatabaseRow.tenant_id == tenant_id,
                DatabaseRow.alias == alias,
            )
        ).scalar_one_or_none()
