"""API key checks adapted from AgentVault's tests/test_auth.py.

AgentVault issued a second prefix (avk_). The suite has one key: qs_,
generated and hashed by queryshield.models.
"""
from __future__ import annotations

from queryshield.models import generate_api_key, hash_api_key


class TestApiKeyGeneration:
    def test_key_has_prefix(self):
        key, prefix, _digest = generate_api_key()
        assert key.startswith("qs_")
        assert prefix == key[:8]
        assert not key.startswith("avk_")

    def test_keys_are_unique(self):
        keys = {generate_api_key()[0] for _ in range(100)}
        assert len(keys) == 100

    def test_key_length(self):
        key, _prefix, _digest = generate_api_key()
        assert len(key) > 40

    def test_hash_is_deterministic(self):
        key, _prefix, digest = generate_api_key()
        assert hash_api_key(key) == digest
        assert hash_api_key(key) == hash_api_key(key)

    def test_hash_differs_for_different_keys(self):
        k1, _, _ = generate_api_key()
        k2, _, _ = generate_api_key()
        assert hash_api_key(k1) != hash_api_key(k2)

    def test_prefix_extraction(self):
        _key, prefix, _digest = generate_api_key()
        assert prefix.startswith("qs_")
        assert len(prefix) == 8
