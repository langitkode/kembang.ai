"""Tool router – registry and execution of chatbot tools.

LLM must not call tools directly (coding rule #14).
Tools are invoked by this router based on tool_name.
"""

import logging
from typing import Any

from app.tools.product_lookup import product_lookup
from app.tools.order_status import order_status

logger = logging.getLogger(__name__)

# ── Registry ──────────────────────────────────────────────────────────────────

_TOOL_REGISTRY: dict[str, Any] = {
    "product_lookup": product_lookup,
    "order_status": order_status,
}


def list_tools() -> list[dict[str, str]]:
    """Return metadata about available tools (for LLM function-calling)."""
    return [
        {
            "name": "product_lookup",
            "description": "Look up product details by name or SKU.",
            "parameters": '{"query": "string"}',
        },
        {
            "name": "order_status",
            "description": "Check the status of a customer order.",
            "parameters": '{"order_id": "string"}',
        },
    ]


async def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a registered tool and return its output.

    Returns ``{"error": "..."}`` if the tool is not found.
    """
    handler = _TOOL_REGISTRY.get(tool_name)
    if handler is None:
        logger.warning("Unknown tool requested: %s", tool_name)
        return {"error": f"unknown_tool: {tool_name}"}

    logger.info("Executing tool %s with input %s", tool_name, tool_input)
    return await handler(tool_input)
