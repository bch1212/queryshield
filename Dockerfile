# Dual-purpose image:
# - Glama launches the default stdio MCP server entrypoint for directory
#   introspection.
# - Railway overrides the command with `python -m queryshield.start` from
#   railway.json, so this image must also contain the full API application.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# pyodbc may need unixODBC headers if a wheel is unavailable; keeping the
# runtime library present also avoids import/link errors in production.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt queryshield-mcp==1.0.1

COPY . .

EXPOSE 8000

# Stdio MCP servers expect the process to read from stdin / write to stdout.
# Glama runs the container with `-i`; Railway replaces this with the API
# start command declared in railway.json.
ENTRYPOINT ["queryshield-mcp"]
