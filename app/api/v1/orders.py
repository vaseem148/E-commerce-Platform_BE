"""Customer order endpoints: checkout, history, detail and cancellation.

Mounted at ``/api/orders``.

Checkout is deliberately paranoid: the address must belong to the caller, the
cart must be non-empty, every line is re-validated against live stock, and all
money is recomputed from the database. Nothing about the price is ever taken
from the request body.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_active_user, get_db
from app.db.base import utcnow
from app.models.address import Address
from app.models.applied_coupon import CartCoupon
from app.models.cart import CartItem
from app.models.order import (
    CANCELLABLE_STATUSES,
    ORDER_STATUSES,
    STATUS_FLOW,
    Order,
    OrderItem,
    build_order_number,
)
from app.models.product import Product
from app.models.user import User
from app.schemas.common import PaginatedResponse, paginate_params
from app.schemas.order import OrderCreate, OrderOut
from app.services import pricing
from app.services.serializers import money, order_to_out, timeline_entry

router = APIRouter()


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------
#: Human labels for the tracker the frontend renders.
STAGE_LABELS: Dict[str, str] = {
    "pending": "Order placed",
    "confirmed": "Confirmed",
    "packed": "Packed",
    "shipped": "Shipped",
    "delivered": "Delivered",
    "cancelled": "Cancelled",
}

#: Default note attached to each stage when nothing more specific is known.
STAGE_NOTES: Dict[str, str] = {
    "pending": "Order placed and awaiting confirmation",
    "confirmed": "Payment confirmed - we are preparing your items",
    "packed": "Packed and ready to leave our warehouse",
    "shipped": "Handed over to the courier and on its way",
    "delivered": "Delivered - thank you for shopping with Nexa",
    "cancelled": "Order cancelled",
}


def _flow_index(stage: str) -> int:
    """Sort key placing ``cancelled`` after every forward stage."""
    return STATUS_FLOW.index(stage) if stage in STATUS_FLOW else len(STATUS_FLOW)


def _as_naive_utc(value: datetime) -> datetime:
    """Normalise a datetime to naive UTC (how SQLite stores them)."""
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _parse_at(raw: Any, fallback: datetime) -> datetime:
    """Read a timeline timestamp that may be a datetime or an ISO string."""
    if isinstance(raw, datetime):
        return _as_naive_utc(raw)
    if isinstance(raw, str):
        try:
            return _as_naive_utc(datetime.fromisoformat(raw.replace("Z", "+00:00")))
        except ValueError:
            return fallback
    return fallback


def _recorded_entries(order: Order) -> List[Dict[str, Any]]:
    """The order's stored timeline, normalised to dicts with real datetimes."""
    created = order.created_at or utcnow()
    entries: List[Dict[str, Any]] = []
    for raw in order.timeline or []:
        if not isinstance(raw, dict):
            continue
        stage = str(raw.get("status") or "").strip()
        if not stage:
            continue
        entries.append(
            {
                "status": stage,
                "at": _parse_at(raw.get("at"), created),
                "note": str(raw.get("note") or STAGE_NOTES.get(stage, "")),
            }
        )
    return entries


def _spread(start: datetime, end: datetime, count: int) -> List[datetime]:
    """``count`` monotonically increasing moments between ``start`` and ``end``."""
    if count <= 1:
        return [start]
    if end <= start:
        return [start + timedelta(seconds=i) for i in range(count)]
    step = (end - start) / (count - 1)
    return [start + step * i for i in range(count)]


def derive_timeline(order: Order) -> List[Dict[str, Any]]:
    """Rebuild the achieved stages from ``status`` + ``created_at``/``updated_at``.

    Used as a fallback for orders whose stored timeline is empty or has fallen
    behind an admin status change, so the tracker is always coherent.
    """
    created = order.created_at or utcnow()
    updated = order.updated_at or created

    if order.status == "cancelled":
        stages = ["pending", "cancelled"]
    elif order.status in STATUS_FLOW:
        stages = list(STATUS_FLOW[: STATUS_FLOW.index(order.status) + 1])
    else:
        stages = ["pending"]

    moments = _spread(created, updated, len(stages))
    return [
        {"status": stage, "at": moments[index], "note": STAGE_NOTES[stage]}
        for index, stage in enumerate(stages)
    ]


def order_stages(order: Order) -> List[Dict[str, Any]]:
    """Every tracker stage in order, each flagged ``completed`` with its ``at``.

    This is the shape a progress tracker wants: the full ladder of stages, not
    just the ones already reached. The API response itself carries only the
    achieved entries (that is what ``OrderOut.timeline`` is), so a stage with
    ``completed = False`` is one the order has not got to yet.
    """
    recorded = {entry["status"]: entry for entry in _recorded_entries(order)}
    derived = {entry["status"]: entry for entry in derive_timeline(order)}
    cancelled = order.status == "cancelled"
    reached = STATUS_FLOW.index(order.status) if order.status in STATUS_FLOW else -1

    stages: List[Dict[str, Any]] = []
    for index, stage in enumerate(STATUS_FLOW):
        entry = recorded.get(stage) or derived.get(stage)
        stages.append(
            {
                "status": stage,
                "label": STAGE_LABELS[stage],
                "note": (entry or {}).get("note") or STAGE_NOTES[stage],
                "at": (entry or {}).get("at"),
                "completed": entry is not None or (not cancelled and index <= reached),
            }
        )

    if cancelled:
        entry = recorded.get("cancelled") or derived.get("cancelled")
        stages.append(
            {
                "status": "cancelled",
                "label": STAGE_LABELS["cancelled"],
                "note": (entry or {}).get("note") or STAGE_NOTES["cancelled"],
                "at": (entry or {}).get("at"),
                "completed": True,
            }
        )
    return stages


def sync_order_timeline(order: Order) -> bool:
    """Top the stored timeline up with any stage the status implies.

    Returns ``True`` when the order was modified (the caller commits). This
    keeps the tracker correct even for seeded orders or admin status changes
    that did not append an entry themselves.
    """
    recorded = _recorded_entries(order)
    seen = {entry["status"] for entry in recorded}

    merged = list(recorded)
    for entry in derive_timeline(order):
        if entry["status"] not in seen:
            merged.append(entry)
            seen.add(entry["status"])

    if recorded and len(merged) == len(recorded):
        return False

    merged.sort(key=lambda entry: (_flow_index(entry["status"]), entry["at"]))
    order.timeline = [
        timeline_entry(entry["status"], entry["at"], entry["note"])
        for entry in merged
    ]
    return True


def _append_timeline(order: Order, stage: str, note: str = "") -> None:
    """Append one achieved stage to the order's timeline."""
    entries = list(order.timeline or [])
    entries.append(
        timeline_entry(stage, utcnow(), note or STAGE_NOTES.get(stage, ""))
    )
    order.timeline = entries


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------
def _get_owned_order(db: Session, user: User, order_number: str) -> Order:
    """Fetch one of the caller's own orders or raise 404."""
    order = db.scalars(
        select(Order).where(
            Order.order_number == order_number, Order.user_id == user.id
        )
    ).first()
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    return order


# ---------------------------------------------------------------------------
# Checkout
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Place an order from the current cart",
)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrderOut:
    """Turn the cart into an order.

    One transaction: snapshot the address and every line, recompute the money
    server-side, decrement stock, bump the sold and coupon counters, and empty
    the cart. Any failure rolls the whole thing back.
    """
    address = db.scalars(
        select(Address).where(
            Address.id == payload.address_id, Address.user_id == current_user.id
        )
    ).first()
    if address is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )

    snapshot = pricing.compute_cart_totals(db, current_user)
    lines: List[CartItem] = snapshot["items"]
    if not lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your cart is empty",
        )

    # Re-validate every line against live stock before touching anything.
    for line in lines:
        product = line.product
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An item in your cart is no longer available",
            )
        pricing.ensure_stock(product, int(line.quantity or 0))

    coupon = snapshot["coupon"]
    prepaid = payload.payment_method != "cod"

    try:
        order = Order(
            # Placeholder: the real number needs the primary key, which only
            # exists after the flush below. Unique so the insert cannot clash.
            order_number=f"TMP-{uuid4().hex[:20].upper()}",
            user_id=current_user.id,
            status="confirmed" if prepaid else "pending",
            payment_method=payload.payment_method,
            payment_status="paid" if prepaid else "pending",
            subtotal=money(snapshot["subtotal"]),
            discount=money(snapshot["discount"]),
            shipping=money(snapshot["shipping"]),
            tax=money(snapshot["tax"]),
            total=money(snapshot["total"]),
            coupon_code=coupon.code if coupon is not None else None,
            notes=payload.notes,
            ship_name=address.full_name,
            ship_phone=address.phone,
            ship_line1=address.line1,
            ship_line2=address.line2,
            ship_city=address.city,
            ship_state=address.state,
            ship_pincode=address.pincode,
            timeline=[],
        )
        db.add(order)
        db.flush()  # assigns order.id and order.created_at

        order.order_number = build_order_number(order.id, order.created_at)

        for line in lines:
            product = line.product
            quantity = int(line.quantity or 0)
            db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    name=product.name,
                    slug=product.slug or "",
                    image=product.primary_image,
                    price=money(product.price),
                    quantity=quantity,
                    line_total=money(line.line_total),
                )
            )
            product.stock = max(0, int(product.stock or 0) - quantity)
            product.sold_count = int(product.sold_count or 0) + quantity

        if coupon is not None:
            coupon.used_count = int(coupon.used_count or 0) + 1

        entries = [
            timeline_entry("pending", order.created_at, "Order placed")
        ]
        if prepaid:
            entries.append(
                timeline_entry(
                    "confirmed",
                    order.created_at,
                    "Payment received - your order is confirmed",
                )
            )
        order.timeline = entries

        # The cart has become the order.
        db.execute(delete(CartItem).where(CartItem.user_id == current_user.id))
        db.execute(delete(CartCoupon).where(CartCoupon.user_id == current_user.id))

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:  # pragma: no cover - defensive, never leak a traceback
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="We could not place your order. Please try again.",
        )

    db.refresh(order)
    return order_to_out(order)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=PaginatedResponse[OrderOut],
    summary="List the current user's orders",
)
def list_orders(
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by order status"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedResponse[OrderOut]:
    """Paginated order history, newest first, optionally filtered by status."""
    stmt = select(Order).where(Order.user_id == current_user.id)

    if status_filter:
        cleaned = status_filter.strip().lower()
        if cleaned not in ORDER_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid order status",
            )
        stmt = stmt.where(Order.status == cleaned)

    safe_page, safe_size, offset = paginate_params(
        page, page_size, settings.MAX_PAGE_SIZE
    )
    total = int(
        db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    )

    orders = list(
        db.scalars(
            stmt.order_by(Order.created_at.desc(), Order.id.desc())
            .offset(offset)
            .limit(safe_size)
        ).unique()
    )

    if any(sync_order_timeline(order) for order in orders):
        db.commit()

    return PaginatedResponse[OrderOut].create(
        items=[order_to_out(order) for order in orders],
        total=total,
        page=safe_page,
        page_size=safe_size,
    )


@router.get(
    "/{order_number}",
    response_model=OrderOut,
    summary="Get one order by its order number",
)
def get_order(
    order_number: str = Path(..., min_length=3, max_length=32),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrderOut:
    """Return a single order. 404 when it is not the caller's."""
    order = _get_owned_order(db, current_user, order_number)
    if sync_order_timeline(order):
        db.commit()
    return order_to_out(order)


@router.post(
    "/{order_number}/cancel",
    response_model=OrderOut,
    summary="Cancel an order",
)
def cancel_order(
    order_number: str = Path(..., min_length=3, max_length=32),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrderOut:
    """Cancel a pending or confirmed order and put the stock back."""
    order = _get_owned_order(db, current_user, order_number)

    if order.status not in CANCELLABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This order can no longer be cancelled",
        )

    try:
        for item in order.items or []:
            product = db.get(Product, item.product_id)
            if product is None:
                continue
            quantity = int(item.quantity or 0)
            product.stock = int(product.stock or 0) + quantity
            product.sold_count = max(0, int(product.sold_count or 0) - quantity)

        if order.coupon_code:
            coupon = pricing.find_coupon(db, order.coupon_code)
            if coupon is not None:
                coupon.used_count = max(0, int(coupon.used_count or 0) - 1)

        order.status = "cancelled"
        if order.payment_status == "paid":
            order.payment_status = "refunded"

        _append_timeline(
            order,
            "cancelled",
            "Order cancelled at your request"
            + (" - refund initiated" if order.payment_status == "refunded" else ""),
        )

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:  # pragma: no cover - defensive
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="We could not cancel this order. Please try again.",
        )

    db.refresh(order)
    return order_to_out(order)
