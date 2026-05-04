"""SSRF defenses for customer-supplied database connection strings.

When a tenant registers a connection string, we resolve the host and refuse
private/loopback/link-local/metadata-service IPs unless ``ALLOW_PRIVATE_DBS``
is set (development override).

This is *necessary* but not *sufficient* defense — a determined attacker can
DNS-rebind, but doing so requires holding a custom DNS server. Combined with
the AST-only-SELECT contract and the read-only credentials we expect
customers to provide, the blast radius of a successful SSRF is bounded to
"read public data the QueryShield host could already see".
"""
from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse

# Always-block ranges (RFC 1918 + loopback + link-local + metadata + reserved).
_BLOCK_NETS = [
    ipaddress.ip_network(n)
    for n in [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "169.254.0.0/16",   # link-local incl. AWS/Azure/GCP metadata 169.254.169.254
        "::1/128",
        "fc00::/7",
        "fe80::/10",
        "100.64.0.0/10",   # CGNAT — Railway's private network falls in here
        "0.0.0.0/8",
    ]
]


class UnsafeDatabaseHost(ValueError):
    """Raised when a connection-string host resolves to a private IP."""


def assert_safe_database_url(connection_string: str, db_type: str) -> None:
    """Parse a connection string, resolve the host, and reject private IPs.

    Skips SQLite (file paths) and DSN-style mssql strings without an obvious
    host token (those are ODBC connection strings; users self-hosting MSSQL
    are an enterprise deal where we trust the customer's proxy setup).
    """
    if os.getenv("ALLOW_PRIVATE_DBS", "").lower() in {"1", "true", "yes"}:
        return
    db_type = (db_type or "").lower()
    if db_type in {"sqlite", "sqlite3"}:
        return
    if db_type in {"mssql", "sqlserver"}:
        # ODBC DSN strings — best-effort regex would help, but skip for v1.
        return

    try:
        parsed = urlparse(connection_string)
    except Exception:
        raise UnsafeDatabaseHost("could not parse connection string")
    host = parsed.hostname
    if not host:
        raise UnsafeDatabaseHost("connection string is missing a hostname")

    if host.lower() in {"localhost", "localhost.", "ip6-localhost", "ip6-loopback"}:
        raise UnsafeDatabaseHost(f"host '{host}' is a loopback alias and is not allowed")

    try:
        # Resolve all A/AAAA records — if any resolve to a private IP, refuse.
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise UnsafeDatabaseHost(f"could not resolve host '{host}': {e}")

    addrs = {info[4][0] for info in infos}
    for raw in addrs:
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            continue
        for net in _BLOCK_NETS:
            if ip in net:
                raise UnsafeDatabaseHost(
                    f"host '{host}' resolves to {ip} which is in a blocked range "
                    f"({net}). If this is intentional in self-hosted deploys, set "
                    f"ALLOW_PRIVATE_DBS=true."
                )
