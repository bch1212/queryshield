# Glama-friendly MCP server image.
# Builds the standalone `queryshield-mcp` stdio MCP server (the same one
# that's published to PyPI). Glama's introspection check launches the
# container, sends an MCP `initialize` over stdio, and verifies tool
# discovery works — no QUERYSHIELD_API_KEY is needed for that handshake.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install only the dependencies the MCP client needs — keep the image small.
RUN pip install --no-cache-dir queryshield-mcp==1.0.1

# Stdio MCP servers expect the process to read from stdin / write to stdout.
# Glama runs the container with `-i` so this just works.
ENTRYPOINT ["queryshield-mcp"]
