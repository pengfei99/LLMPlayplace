
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tp-mcp-demo")

@mcp.tool()
def calculate_cart_total(
    item_prices: list[float],
    discount_percent: float,
    tax_percent: float,
    shipping_fee: float,
    free_shipping_threshold: float,
) -> dict:
    """
    Calculate the final price of a shopping cart.

    Rules:
    - Sum item prices.
    - Apply discount.
    - Apply tax after discount.
    - Add shipping unless total with tax before shipping is strictly greater than the free shipping threshold.
    - Round values to two decimals.
    """
    subtotal = sum(item_prices)
    discounted_total = subtotal * (1 - discount_percent / 100)
    total_with_tax = discounted_total * (1 + tax_percent / 100)
    shipping_applied = 0 if total_with_tax > free_shipping_threshold else shipping_fee
    final_total = total_with_tax + shipping_applied

    return {
        "subtotal": round(subtotal, 2),
        "discounted_total": round(discounted_total, 2),
        "total_with_tax_before_shipping": round(total_with_tax, 2),
        "shipping_applied": round(shipping_applied, 2),
        "final_total": round(final_total, 2),
    }


@mcp.tool()
def divide(a: float, b: float) -> dict:
    """
    Divide a by b. If b is zero, return a structured error instead of crashing.
    """
    if b == 0:
        return {
            "error": "division_by_zero",
            "message": "Division by zero is not defined."
        }
    return {"result": a / b}


if __name__ == "__main__":
    mcp.run(transport="stdio")
