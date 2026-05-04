"""NL→SQL translation via Claude with prompt caching + tool use.

The agent has two tools:
- ``get_schema(table_name?)`` — returns columns for one table or the whole DB
- ``validate_query(sql)`` — calls our safety validator and returns the verdict

The full schema is large, so we cache it on the prompt itself
(`cache_control: ephemeral`). The system prompt is also cached. Together
this makes repeated NL queries on the same DB cheap.

Failure modes:
- We bound the loop to ``MAX_TURNS`` to prevent runaway tool use.
- If the model emits SQL that fails validate_query, we let it self-correct
  but still re-validate at the proxy level — never trust the model's word
  for safety.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from queryshield.config import get_settings
from queryshield.models import QueryRequest
from queryshield.safety import validate_sql

log = logging.getLogger("queryshield.nl_to_sql")

MAX_TURNS = 6

NL_TO_SQL_SYSTEM = """You are a SQL generation expert for QueryShield, a secure proxy between AI agents and customer databases.

You translate natural-language questions into safe, READ-ONLY SQL queries.

Hard rules — these are enforced downstream and your query WILL be rejected if violated:
- Generate ONLY SELECT statements. Never INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, MERGE, GRANT, REVOKE, or any DDL/DML.
- Always use explicit column names (SELECT a, b, c). Never SELECT *.
- Always include a LIMIT clause; max LIMIT is {max_rows}.
- Use only tables and columns that appear in the provided schema. If you need information about the schema, call get_schema.
- If a question cannot be answered from the available schema, return a query that selects a literal "unanswerable" with LIMIT 1, do not invent tables.

When you have a candidate query, call validate_query(sql) to confirm it passes safety checks. If it fails, fix the issue and try again.

When the query passes validation, return ONLY the final SQL string in your response — no prose, no markdown fences."""


_TOOLS = [
    {
        "name": "get_schema",
        "description": (
            "Retrieve database schema. Pass table_name to get one table's "
            "columns. Omit it to get the full schema (already in context, "
            "but useful if you want to re-confirm)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Optional. Use 'schema.table' for non-default schemas.",
                }
            },
        },
    },
    {
        "name": "validate_query",
        "description": "Validate a candidate SQL string against the safety rules. Returns {safe: bool, reason: str}.",
        "input_schema": {
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"],
        },
    },
]


_client = None


def _anthropic():  # type: ignore[no-untyped-def]
    """Lazy import — keeps the module importable without the SDK installed."""
    global _client
    if _client is None:
        import anthropic  # type: ignore

        _client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key)
    return _client


async def translate_nl_to_sql(request: QueryRequest, schema: Dict[str, Any]) -> str:
    """Returns a cleaned SQL string. Raises ValueError on hard failure."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    messages: list[dict] = [{"role": "user", "content": request.query}]
    system = [
        {
            "type": "text",
            "text": NL_TO_SQL_SYSTEM.format(max_rows=request.max_rows),
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": "Database schema:\n" + json.dumps(schema, indent=2, default=str),
            "cache_control": {"type": "ephemeral"},
        },
    ]

    client = _anthropic()
    for turn in range(MAX_TURNS):
        response = client.messages.create(
            model=settings.nl_to_sql_model,
            max_tokens=1024,
            system=system,
            tools=_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    return _strip_to_sql(block.text)
            raise ValueError("model returned end_turn with no text block")

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if getattr(block, "type", None) != "tool_use":
                    continue
                if block.name == "get_schema":
                    table = (block.input or {}).get("table_name")
                    payload = (
                        schema.get(table) if table and table in schema else schema
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(payload, default=str),
                        }
                    )
                elif block.name == "validate_query":
                    sql = (block.input or {}).get("sql", "")
                    is_safe, reason = validate_sql(sql)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"safe": is_safe, "reason": reason}),
                        }
                    )
                else:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({"error": f"unknown tool {block.name}"}),
                            "is_error": True,
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
            continue

        # Anything else (max_tokens, stop_sequence) — bail.
        raise ValueError(f"unexpected stop_reason: {response.stop_reason}")

    raise ValueError(f"NL→SQL agent exceeded {MAX_TURNS} turns without producing SQL")


def _strip_to_sql(text: str) -> str:
    """Trim markdown fences / leading prose if the model added any."""
    s = text.strip()
    if s.startswith("```"):
        # ```sql\n...\n``` or ```\n...\n```
        first_nl = s.find("\n")
        if first_nl != -1:
            s = s[first_nl + 1 :]
        if s.endswith("```"):
            s = s[: -3]
    return s.strip().rstrip(";").strip()
