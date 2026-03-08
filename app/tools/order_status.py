"""Order status tool (stub)."""


async def order_status(params: dict) -> dict:
    """Check order status by order ID.

    This is a stub returning mock data.
    Replace with real order management system integration.
    """
    order_id = params.get("order_id", "unknown")
    return {
        "tool": "order_status",
        "order_id": order_id,
        "status": "processing",
        "estimated_delivery": "2-3 business days",
    }
