"""Aggregate analytics powering the admin dashboard.

Everything here is computed with grouped SQL rather than Python loops over
loaded rows, so the dashboard stays fast as the order table grows.  The one
deliberate exception is the revenue series: SQLite has no ``generate_series``,
so the date spine is built in Python and left-joined against a grouped query.
That guarantees a **gapless** series - every day in the window appears, days
without orders reporting zero - which the frontend area chart depends on.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Sequence

from sqlalchemy import Float, Integer, cast, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.category import Category
from app.models.order import ORDER_STATUSES, Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.admin import (
    AdminStatsOut,
    RevenuePoint,
    StatusBucket,
    TopCategory,
    TopProduct,
)
from app.services.serializers import (
    category_counts_map,
    money,
    order_to_out,
    products_to_out,
)

# Cancelled orders are excluded from every revenue figure: the money was never
# collected.  They still show up in status_breakdown so the operator can see them.
REVENUE_STATUSES = tuple(s for s in ORDER_STATUSES if s != "cancelled")

LOW_STOCK_THRESHOLD = 5
RECENT_ORDER_LIMIT = 8
TOP_PRODUCT_LIMIT = 8
TOP_CATEGORY_LIMIT = 6


def _window(days: int) -> tuple[datetime, datetime, datetime]:
    """Return ``(start, previous_start, now)`` for a rolling ``days`` window.

    ``start`` is midnight ``days - 1`` days ago, so a 7-day window covers seven
    whole calendar days including today rather than 7x24 hours ending now.
    """
    days = max(1, int(days or 30))
    now = datetime.utcnow()
    start = datetime.combine(now.date() - timedelta(days=days - 1), datetime.min.time())
    previous_start = start - timedelta(days=days)
    return start, previous_start, now


def _delta_pct(current: float, previous: float) -> float:
    """Percentage change, guarding the divide-by-zero the first month hits.

    Growth from nothing is reported as +100% rather than infinity, which is what
    a dashboard reader expects to see in a delta chip.
    """
    current = float(current or 0.0)
    previous = float(previous or 0.0)
    if previous <= 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100.0, 1)


def _revenue_totals(db: Session, start: datetime, end: datetime) -> tuple[float, int]:
    """Revenue and order count for non-cancelled orders in ``[start, end)``."""
    row = db.execute(
        select(
            func.coalesce(func.sum(Order.total), 0.0),
            func.count(Order.id),
        ).where(
            Order.status.in_(REVENUE_STATUSES),
            Order.created_at >= start,
            Order.created_at < end,
        )
    ).one()
    return money(row[0]), int(row[1] or 0)


def _revenue_series(db: Session, start: datetime, end: datetime) -> List[RevenuePoint]:
    """One point per calendar day in the window - never sparse.

    Days with no orders are emitted with ``revenue=0, orders=0`` so the chart
    draws a continuous line instead of interpolating across missing dates.
    """
    rows = db.execute(
        select(
            func.date(Order.created_at).label("day"),
            func.coalesce(func.sum(Order.total), 0.0),
            func.count(Order.id),
        )
        .where(
            Order.status.in_(REVENUE_STATUSES),
            Order.created_at >= start,
            Order.created_at < end,
        )
        .group_by("day")
    ).all()

    # func.date() yields "YYYY-MM-DD" strings on SQLite but real dates elsewhere.
    by_day: Dict[str, tuple[float, int]] = {}
    for day, revenue, count in rows:
        key = day.isoformat() if isinstance(day, (date, datetime)) else str(day)
        by_day[key[:10]] = (money(revenue), int(count or 0))

    series: List[RevenuePoint] = []
    cursor = start.date()
    last = end.date()
    while cursor <= last:
        key = cursor.isoformat()
        revenue, orders = by_day.get(key, (0.0, 0))
        series.append(RevenuePoint(date=key, revenue=revenue, orders=orders))
        cursor += timedelta(days=1)
    return series


def _status_breakdown(db: Session, start: datetime, end: datetime) -> List[StatusBucket]:
    """Count per order status, with every status present even at zero."""
    rows = db.execute(
        select(Order.status, func.count(Order.id))
        .where(Order.created_at >= start, Order.created_at < end)
        .group_by(Order.status)
    ).all()
    counts = {str(status): int(count or 0) for status, count in rows}
    return [StatusBucket(status=s, count=counts.get(s, 0)) for s in ORDER_STATUSES]


def _top_products(db: Session, start: datetime, end: datetime) -> List[TopProduct]:
    """Best sellers in the window, ranked by units sold."""
    rows = db.execute(
        select(
            OrderItem.product_id,
            func.max(OrderItem.name),
            func.max(OrderItem.slug),
            func.max(OrderItem.image),
            cast(func.coalesce(func.sum(OrderItem.quantity), 0), Integer),
            cast(func.coalesce(func.sum(OrderItem.line_total), 0.0), Float),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Order.status.in_(REVENUE_STATUSES),
            Order.created_at >= start,
            Order.created_at < end,
        )
        .group_by(OrderItem.product_id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(TOP_PRODUCT_LIMIT)
    ).all()

    return [
        TopProduct(
            id=int(product_id or 0),
            name=name or "Unknown product",
            slug=slug or "",
            image=image or "",
            units_sold=int(units or 0),
            revenue=money(revenue),
        )
        for product_id, name, slug, image, units, revenue in rows
    ]


def _top_categories(db: Session, start: datetime, end: datetime) -> List[TopCategory]:
    """Revenue per category, joined through the live product -> category link.

    Order items snapshot the product name but not its category, so this walks
    ``OrderItem -> Product -> Category``.  Items whose product was hard-deleted
    simply drop out of the ranking.
    """
    rows = db.execute(
        select(
            Category.name,
            cast(func.coalesce(func.sum(OrderItem.line_total), 0.0), Float),
        )
        .select_from(OrderItem)
        .join(Order, Order.id == OrderItem.order_id)
        .join(Product, Product.id == OrderItem.product_id)
        .join(Category, Category.id == Product.category_id)
        .where(
            Order.status.in_(REVENUE_STATUSES),
            Order.created_at >= start,
            Order.created_at < end,
        )
        .group_by(Category.id, Category.name)
        .order_by(func.sum(OrderItem.line_total).desc())
        .limit(TOP_CATEGORY_LIMIT)
    ).all()

    return [TopCategory(name=name, revenue=money(revenue)) for name, revenue in rows]


def _recent_orders(db: Session, limit: int = RECENT_ORDER_LIMIT) -> Sequence[Order]:
    """The newest orders overall, eagerly loading items to avoid N+1."""
    return (
        db.scalars(
            select(Order)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc(), Order.id.desc())
            .limit(limit)
        )
        .unique()
        .all()
    )


def _low_stock(db: Session, threshold: int = LOW_STOCK_THRESHOLD) -> Sequence[Product]:
    """Active products at or below the restock threshold, scarcest first."""
    return (
        db.scalars(
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.is_active.is_(True), Product.stock <= threshold)
            .order_by(Product.stock.asc(), Product.name.asc())
            .limit(12)
        )
        .unique()
        .all()
    )


def build_admin_stats(db: Session, days: int = 30) -> AdminStatsOut:
    """Assemble the whole ``GET /api/admin/stats`` payload."""
    start, previous_start, now = _window(days)
    end = now + timedelta(seconds=1)

    revenue, orders = _revenue_totals(db, start, end)
    prev_revenue, prev_orders = _revenue_totals(db, previous_start, start)

    customers = int(
        db.scalar(
            select(func.count(User.id)).where(
                User.role == "user", User.created_at >= start, User.created_at < end
            )
        )
        or 0
    )
    prev_customers = int(
        db.scalar(
            select(func.count(User.id)).where(
                User.role == "user",
                User.created_at >= previous_start,
                User.created_at < start,
            )
        )
        or 0
    )

    products_total = int(
        db.scalar(select(func.count(Product.id)).where(Product.is_active.is_(True))) or 0
    )
    pending_orders = int(
        db.scalar(
            select(func.count(Order.id)).where(Order.status.in_(("pending", "confirmed")))
        )
        or 0
    )

    counts = category_counts_map(db)

    return AdminStatsOut(
        revenue=revenue,
        revenue_delta_pct=_delta_pct(revenue, prev_revenue),
        orders=orders,
        orders_delta_pct=_delta_pct(orders, prev_orders),
        customers=customers,
        customers_delta_pct=_delta_pct(customers, prev_customers),
        products=products_total,
        avg_order_value=money(revenue / orders) if orders else 0.0,
        pending_orders=pending_orders,
        revenue_series=_revenue_series(db, start, end),
        status_breakdown=_status_breakdown(db, start, end),
        top_products=_top_products(db, start, end),
        top_categories=_top_categories(db, start, end),
        recent_orders=[order_to_out(o) for o in _recent_orders(db)],
        low_stock=products_to_out(_low_stock(db), counts),
    )


def customer_metrics(db: Session, user_ids: Sequence[int]) -> Dict[int, dict]:
    """Lifetime order metrics for the given users, in one grouped query.

    Returns ``{user_id: {"orders_count", "total_spent", "last_order_at"}}`` so the
    customers table can be built without a per-row query.
    """
    if not user_ids:
        return {}

    rows = db.execute(
        select(
            Order.user_id,
            func.count(Order.id),
            func.coalesce(func.sum(Order.total), 0.0),
            func.max(Order.created_at),
        )
        .where(Order.user_id.in_(list(user_ids)), Order.status.in_(REVENUE_STATUSES))
        .group_by(Order.user_id)
    ).all()

    metrics: Dict[int, dict] = {}
    for user_id, count, spent, last_at in rows:
        if isinstance(last_at, str):
            try:
                last_at = datetime.fromisoformat(last_at)
            except ValueError:
                last_at = None
        metrics[int(user_id)] = {
            "orders_count": int(count or 0),
            "total_spent": money(spent),
            "last_order_at": last_at,
        }
    return metrics


__all__ = [
    "build_admin_stats",
    "customer_metrics",
    "LOW_STOCK_THRESHOLD",
    "REVENUE_STATUSES",
]
