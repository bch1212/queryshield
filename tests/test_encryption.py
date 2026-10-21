"""Column-level encryption for named credentials.

Ported from AgentVault's tests/test_encryption.py. The old fixture used a
string shaped like a Stripe live key; secret scanners flagged it. The value
below is an obvious dummy.
"""
from __future__ import annotations

import pytest

from queryshield.credential_crypto import decrypt_value, encrypt_value, reset_fernet


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted value decrypts back to original."""
        reset_fernet()
        secret = "dummy_not_a_real_stripe_key"
        encrypted = encrypt_value(secret)

        assert encrypted != secret
        assert decrypt_value(encrypted) == secret

    def test_different_ciphertexts_per_call(self):
        """Fernet produces unique ciphertexts (nonce-based)."""
        reset_fernet()
        secret = "my_api_key_value"
        a = encrypt_value(secret)
        b = encrypt_value(secret)
        assert a != b

    def test_decrypt_bad_data_raises(self):
        """Decrypting garbage raises ValueError."""
        reset_fernet()
        with pytest.raises(ValueError, match="Failed to decrypt"):
            decrypt_value("not_valid_fernet_token")

    def test_empty_string_roundtrip(self):
        """Can encrypt and decrypt empty string."""
        reset_fernet()
        encrypted = encrypt_value("")
        assert decrypt_value(encrypted) == ""

    def test_long_value_roundtrip(self):
        """Can handle long values (e.g., JWT tokens)."""
        reset_fernet()
        long_val = "x" * 10000
        encrypted = encrypt_value(long_val)
        assert decrypt_value(encrypted) == long_val

    def test_missing_vault_key_fails_closed(self, monkeypatch):
        """No baked-in key. Encryption refuses to run without VAULT_KEY."""
        import queryshield.credential_crypto as crypto

        reset_fernet()

        class _Unset:
            vault_key = None

        monkeypatch.setattr(crypto, "get_settings", lambda: _Unset())
        with pytest.raises(RuntimeError, match="VAULT_KEY"):
            encrypt_value("dummy_not_a_real_stripe_key")
        reset_fernet()
