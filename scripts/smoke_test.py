"""End-to-end smoke test for the Nexa Commerce API.

Exercises every endpoint group against a running server using only the standard
library, so it needs no test dependencies:

    python run.py                    # in one terminal
    python scripts/smoke_test.py     # in another

Exits non-zero if any check fails, which makes it usable as a CI gate.
The database must be seeded first (``python seed.py --force``).
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Optional, Tuple

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 20

ADMIN = {"email": "admin@nexa.com", "password": "Admin@123"}
CUSTOMER = {"email": "demo@nexa.com", "password": "Demo@123"}

_passed = 0
_failed = 0
_failures: list[str] = []


# ---------------------------------------------------------------------------
# Tiny HTTP helper
# ---------------------------------------------------------------------------
def request(
    method: str, path: str, body: Optional[dict] = None, token: Optional[str] = None
) -> Tuple[int, Any]:
    """Perform one request, returning ``(status_code, parsed_json)``.

    HTTP errors are returned rather than raised so the checks below can assert
    on 400/401/403/404 responses directly.
    """
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        return exc.code, (json.loads(raw) if raw else None)


def check(name: str, condition: bool, detail: str = "") -> bool:
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  PASS  {name}" + (f"  ({detail})" if detail else ""))
    else:
        _failed += 1
        _failures.append(name)
        print(f"  FAIL  {name}" + (f"  ({detail})" if detail else ""))
    return condition


def section(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")


def wait_for_server(attempts: int = 40) -> bool:
    """Poll /api/health until the server answers."""
    for _ in range(attempts):
        try:
            if request("GET", "/api/health")[0] == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def test_catalog() -> dict:
    section("Catalog")

    status, _ = request("GET", "/api/health")
    check("GET /api/health", status == 200)

    status, categories = request("GET", "/api/categories")
    check(
        "GET /api/categories returns 8",
        status == 200 and len(categories) == 8,
        f"n={len(categories) if status == 200 else status}",
    )

    status, listing = request("GET", "/api/products?page_size=12")
    check(
        "GET /api/products has the seeded catalog",
        status == 200 and listing["total"] >= 60,
        f"total={listing.get('total')}",
    )
    check(
        "envelope fields present",
        all(k in listing for k in ("items", "total", "page", "page_size", "pages")),
    )
    check(
        "facets computed",
        "facets" in listing and len(listing["facets"]["brands"]) > 0,
        f"brands={len(listing.get('facets', {}).get('brands', []))}",
    )

    _, searched = request("GET", "/api/products?search=headphones")
    check(
        "search narrows the result set",
        searched["total"] < listing["total"],
        f"n={searched['total']}",
    )

    _, filtered = request("GET", "/api/products?category=electronics&sort=price_desc")
    prices = [p["price"] for p in filtered["items"]]
    check("category filter applies", filtered["total"] == 8, f"n={filtered['total']}")
    check("sort=price_desc is descending", prices == sorted(prices, reverse=True))

    _, cheap = request("GET", "/api/products?max_price=1000")
    check(
        "max_price filter applies",
        all(p["price"] <= 1000 for p in cheap["items"]),
        f"n={cheap['total']}",
    )

    _, rated = request("GET", "/api/products?min_rating=4")
    check("min_rating filter applies", all(p["rating"] >= 4 for p in rated["items"]))

    _, page2 = request("GET", "/api/products?page=2&page_size=12")
    check("pagination works", page2["page"] == 2 and len(page2["items"]) > 0)

    slug = listing["items"][0]["slug"]
    status, detail = request("GET", f"/api/products/{slug}")
    check(
        "GET /api/products/{slug}",
        status == 200 and "related" in detail and "rating_breakdown" in detail,
    )
    check("unknown slug is 404", request("GET", "/api/products/no-such-thing")[0] == 404)

    status, reviews = request("GET", f"/api/products/{slug}/reviews")
    check("product reviews carry a summary", status == 200 and "summary" in reviews)

    status, featured = request("GET", "/api/products/featured?limit=8")
    check("featured products", status == 200 and len(featured) > 0, f"n={len(featured)}")

    return listing


def test_auth() -> Tuple[str, str]:
    section("Authentication")

    status, admin_token = request("POST", "/api/auth/login", ADMIN)
    check("admin login", status == 200 and "access_token" in admin_token)

    status, user_token = request("POST", "/api/auth/login", CUSTOMER)
    check("customer login", status == 200 and "access_token" in user_token)

    status, _ = request("POST", "/api/auth/login", {**CUSTOMER, "password": "nope"})
    check("wrong password is 401", status == 401)

    at = admin_token["access_token"]
    ut = user_token["access_token"]

    status, me = request("GET", "/api/auth/me", token=ut)
    check("GET /api/auth/me", status == 200 and me["email"] == CUSTOMER["email"])
    check("GET /api/auth/me without a token is 401", request("GET", "/api/auth/me")[0] == 401)

    return at, ut


def test_cart(user_token: str, product_id: int) -> None:
    section("Cart and pricing")

    request("DELETE", "/api/cart", token=user_token)

    status, cart = request(
        "POST", "/api/cart/items", {"product_id": product_id, "quantity": 2}, user_token
    )
    check("add to cart", status == 201 and cart["count"] == 2, f"count={cart['count']}")

    payable = round(cart["subtotal"] - cart["discount"], 2)
    shipping = 0 if payable >= 999 else 49
    expected = round(payable + shipping + round(payable * 0.05, 2), 2)
    check(
        "totals follow the pricing rules",
        abs(cart["total"] - expected) < 0.02,
        f"api={cart['total']} expected={expected}",
    )

    status, cart = request(
        "PATCH", f"/api/cart/items/{cart['items'][0]['id']}", {"quantity": 3}, user_token
    )
    check("update quantity", status == 200 and cart["count"] == 3)

    status, cart = request("POST", "/api/cart/coupon", {"code": "WELCOME10"}, user_token)
    check("apply WELCOME10", status == 200 and cart["discount"] > 0, f"discount={cart['discount']}")

    status, cart = request("DELETE", "/api/cart/coupon", token=user_token)
    check("remove coupon", status == 200 and cart["discount"] == 0)

    status, body = request("POST", "/api/cart/coupon", {"code": "EXPIRED10"}, user_token)
    check("expired coupon is rejected", status == 400, str(body.get("detail")))

    status, body = request("POST", "/api/cart/coupon", {"code": "NOPE"}, user_token)
    check("unknown coupon is rejected", status == 400, str(body.get("detail")))


def test_wishlist(user_token: str, product_id: int) -> None:
    section("Wishlist")

    status, items = request("POST", f"/api/wishlist/{product_id}", token=user_token)
    check("add to wishlist", status in (200, 201) and any(p["id"] == product_id for p in items))

    status, again = request("POST", f"/api/wishlist/{product_id}", token=user_token)
    check("adding twice is idempotent", status in (200, 201) and len(again) == len(items))

    status, after = request("DELETE", f"/api/wishlist/{product_id}", token=user_token)
    check("remove from wishlist", status == 200 and not any(p["id"] == product_id for p in after))


def test_orders(user_token: str) -> None:
    section("Orders")

    status, addresses = request("GET", "/api/addresses", token=user_token)
    check("list addresses", status == 200 and len(addresses) > 0)

    # Ensure there is something to buy.
    _, listing = request("GET", "/api/products?in_stock=true&page_size=1")
    product = listing["items"][0]
    _, before = request("GET", f"/api/products/{product['slug']}")

    request("DELETE", "/api/cart", token=user_token)
    request("POST", "/api/cart/items", {"product_id": product["id"], "quantity": 2}, user_token)

    status, order = request(
        "POST",
        "/api/orders",
        {"address_id": addresses[0]["id"], "payment_method": "upi"},
        user_token,
    )
    if not check(
        "place an order",
        status in (200, 201) and "order_number" in (order or {}),
        str((order or {}).get("order_number") or (order or {}).get("detail")),
    ):
        return

    number = order["order_number"]

    _, cart = request("GET", "/api/cart", token=user_token)
    check("cart is emptied by checkout", cart["count"] == 0)

    _, after = request("GET", f"/api/products/{product['slug']}")
    check(
        "stock decremented",
        after["stock"] == before["stock"] - 2,
        f"{before['stock']} -> {after['stock']}",
    )

    check("order payment marked paid for UPI", order["payment_status"] == "paid")

    status, fetched = request("GET", f"/api/orders/{number}", token=user_token)
    check("fetch the order", status == 200 and len(fetched["timeline"]) > 0)

    status, listing = request("GET", "/api/orders", token=user_token)
    check("order history is paginated", status == 200 and listing["total"] > 0)

    status, cancelled = request("POST", f"/api/orders/{number}/cancel", token=user_token)
    check("cancel the order", status == 200 and cancelled["status"] == "cancelled")

    _, restored = request("GET", f"/api/products/{product['slug']}")
    check(
        "stock restored on cancel",
        restored["stock"] == before["stock"],
        f"{after['stock']} -> {restored['stock']}",
    )

    status, _ = request("POST", f"/api/orders/{number}/cancel", token=user_token)
    check("cancelling twice is rejected", status == 400)


def test_admin(admin_token: str, user_token: str) -> None:
    section("Admin")

    status, stats = request("GET", "/api/admin/stats?days=30", token=admin_token)
    check("GET /api/admin/stats", status == 200 and stats["revenue"] > 0, f"revenue={stats['revenue']}")
    check(
        "revenue_series is gapless",
        len(stats["revenue_series"]) == 30,
        f"n={len(stats['revenue_series'])}",
    )
    check("every status is present", len(stats["status_breakdown"]) == 6)
    check("top products ranked", len(stats["top_products"]) > 0)
    check("low stock panel populated", len(stats["low_stock"]) > 0, f"n={len(stats['low_stock'])}")
    check("recent orders included", len(stats["recent_orders"]) > 0)

    _, week = request("GET", "/api/admin/stats?days=7", token=admin_token)
    check("days=7 changes the window", len(week["revenue_series"]) == 7)

    status, products = request("GET", "/api/admin/products?page_size=5", token=admin_token)
    check("admin product listing", status == 200 and products["total"] >= 60)

    status, created = request(
        "POST",
        "/api/admin/products",
        {
            "name": "Smoke Test Widget",
            "description": "Created by the smoke test.",
            "price": 1299,
            "stock": 7,
            "brand": "SmokeCo",
            "category_id": 1,
            "images": ["https://picsum.photos/seed/smoke-1/800/800"],
            "tags": ["test"],
        },
        admin_token,
    )
    check("create a product", status == 201 and created["slug"] == "smoke-test-widget")

    if status == 201:
        status, updated = request(
            "PATCH", f"/api/admin/products/{created['id']}", {"price": 999}, admin_token
        )
        check("update a product", status == 200 and updated["price"] == 999)

        status, _ = request(
            "DELETE", f"/api/admin/products/{created['id']}", token=admin_token
        )
        check("delete a product", status == 204)

    status, orders = request("GET", "/api/admin/orders?page_size=5", token=admin_token)
    check("admin order listing", status == 200 and orders["total"] > 0, f"n={orders['total']}")

    if orders["items"]:
        number = orders["items"][0]["order_number"]
        status, patched = request(
            "PATCH", f"/api/admin/orders/{number}", {"status": "packed"}, admin_token
        )
        check("update order status", status == 200 and patched["status"] == "packed")

        status, _ = request(
            "PATCH", f"/api/admin/orders/{number}", {"status": "teleported"}, admin_token
        )
        check("invalid status rejected", status == 400)

    status, customers = request("GET", "/api/admin/customers", token=admin_token)
    check("customer directory", status == 200 and customers["total"] > 0)
    check(
        "lifetime metrics computed",
        any(c["orders_count"] > 0 for c in customers["items"]),
    )

    status, coupons = request("GET", "/api/admin/coupons", token=admin_token)
    check("coupon listing", status == 200 and len(coupons) == 6, f"n={len(coupons)}")

    check("customer token is 403", request("GET", "/api/admin/stats", token=user_token)[0] == 403)
    check("anonymous is 401", request("GET", "/api/admin/stats")[0] == 401)


# ---------------------------------------------------------------------------
def main() -> int:
    print(f"Nexa API smoke test -> {BASE_URL}")

    if not wait_for_server():
        print("\nServer did not respond on /api/health. Start it with: python run.py")
        return 1

    listing = test_catalog()
    admin_token, user_token = test_auth()

    product_id = listing["items"][0]["id"]
    test_cart(user_token, product_id)
    test_wishlist(user_token, product_id)
    test_orders(user_token)
    test_admin(admin_token, user_token)

    print("\n" + "=" * 46)
    print(f"  PASSED {_passed}    FAILED {_failed}")
    print("=" * 46)
    if _failures:
        print("\nFailed checks:")
        for name in _failures:
            print(f"  - {name}")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
