"""Column-level Fernet encryption for named credentials.

Uses ``VAULT_KEY``, the same key as the database-connection vault. There is
no baked-in fallback: a missing or invalid key refuses to encrypt or decrypt.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from queryshield.config import get_settings

_fernet: Fernet | None = None


def reset_fernet() -> None:
    """Drop the cached Fernet instance. Tests call this after swapping keys."""
    global _fernet
    _fernet = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = get_settings().vault_key
        if not key:
            raise RuntimeError("VAULT_KEY is not set — cannot encrypt or decrypt credentials")
        raw = key.encode("utf-8") if isinstance(key, str) else key
        try:
            _fernet = Fernet(raw)
        except (TypeError, ValueError) as e:
            raise RuntimeError("VAULT_KEY is not a valid Fernet key") from e
    return _fernet


def encrypt_value(plaintext: str) -> str:
    """Encrypt a credential value. Returns a urlsafe-base64 Fernet token."""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a credential value."""
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError("Failed to decrypt credential — key mismatch or corrupted data") from e
