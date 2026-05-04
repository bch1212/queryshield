"""Process entry point — runs uvicorn programmatically.

Why not put ``uvicorn ... --port $PORT`` directly in railway.json?

Railway exec's the startCommand without a shell, so the literal string
``$PORT`` is passed to uvicorn, which fails to parse it as an int. The
canonical fix is to have a Python entrypoint read the env var via
``os.getenv`` and start uvicorn with the resolved value.
"""
from __future__ import annotations

import os

import uvicorn


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    workers = int(os.getenv("UVICORN_WORKERS", "1"))
    uvicorn.run(
        "queryshield.main:app",
        host=host,
        port=port,
        workers=workers,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
