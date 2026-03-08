"""Product lookup tool (stub)."""


async def product_lookup(params: dict) -> dict:
    """Look up product info by query.

    This is a stub returning mock data.
    Replace with real product database or API integration.
    """
    query = params.get("query", "")
    return {
        "tool": "product_lookup",
        "results": [
            {
                "name": f"Sample Product matching '{query}'",
                "price": 50000,
                "currency": "IDR",
                "in_stock": True,
            }
        ],
    }
