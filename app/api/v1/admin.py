"""Admin API: dashboard analytics plus catalog, order, customer and coupon management.

Every route in this module is gated by :func:`get_current_admin`, which raises
401 for an anonymous caller and 403 for a signed-in non-admin.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_admin, get_db
from app.models.category import Category
from app.models.order import ORDER_STATUSES, PAYMENT_STATUSES, Order, OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.admin import AdminStatsOut, CustomerOut
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import PaginatedResponse, paginate_params
from app.schemas.coupon import CouponCreate, CouponOut, CouponUpdate
from app.schemas.order import OrderOut
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.models.coupon import Coupon
from app.services.analytics import build_admin_stats, customer_metrics
from app.services.serializers import (
    category_counts_map,
    category_to_out,
    coupon_to_out,
    invalidate_category_counts,
    money,
    order_to_out,
    product_to_out,
    timeline_entry,
)
from app.services.slugs import unique_slug

router = APIRouter(dependencies=[Depends(get_current_admin)])


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@router.get("/stats", response_model=AdminStatsOut)
def get_stats(
    days: int = Query(30, ge=1, le=365, description="Length of the reporting window"),
    db: Session = Depends(get_db),
) -> AdminStatsOut:
    """Everything the dashboard renders, in one round trip."""
    return build_admin_stats(db, days=days)


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
def _get_product_or_404(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def _require_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.get("/products", response_model=PaginatedResponse[ProductOut])
def list_products(
    search: Optional[str] = None,
    category: Optional[str] = Query(None, description="Category slug"),
    status_filter: Optional[str] = Query(
        None, alias="status", description="active | inactive"
    ),
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> PaginatedResponse[ProductOut]:
    """Catalog listing for the admin table - includes inactive products."""
    page, page_size, offset = paginate_params(page, page_size)

    stmt = select(Product).options(selectinload(Product.category))
    count_stmt = select(func.count(Product.id))

    if search:
        term = f"%{search.strip().lower()}%"
        condition = or_(
            func.lower(Product.name).like(term),
            func.lower(Product.brand).like(term),
            func.lower(Product.slug).like(term),
        )
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    if category:
        category_row = db.scalar(select(Category).where(Category.slug == category))
        if category_row is None:
            raise HTTPException(status_code=404, detail="Category not found")
        stmt = stmt.where(Product.category_id == category_row.id)
        count_stmt = count_stmt.where(Product.category_id == category_row.id)

    if status_filter in ("active", "inactive"):
        wanted = status_filter == "active"
        stmt = stmt.where(Product.is_active.is_(wanted))
        count_stmt = count_stmt.where(Product.is_active.is_(wanted))

    total = int(db.scalar(count_stmt) or 0)
    rows = (
        db.scalars(
            stmt.order_by(Product.created_at.desc(), Product.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        .unique()
        .all()
    )

    counts = category_counts_map(db)
    return PaginatedResponse.create(
        [product_to_out(p, counts) for p in rows], total, page, page_size
    )


@router.post("/products", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate, db: Session = Depends(get_db)
) -> ProductOut:
    """Add a product to the catalog."""
    _require_category(db, payload.category_id)

    product = Product(
        name=payload.name.strip(),
        slug=unique_slug(db, Product, payload.slug or payload.name, fallback="product"),
        description=payload.description or "",
        price=money(payload.price),
        compare_at_price=(
            money(payload.compare_at_price)
            if payload.compare_at_price is not None
            else None
        ),
        stock=int(payload.stock or 0),
        brand=(payload.brand or "").strip(),
        category_id=payload.category_id,
        images=list(payload.images or []),
        tags=[t.strip() for t in (payload.tags or []) if t.strip()],
        is_featured=bool(payload.is_featured),
        is_active=bool(payload.is_active),
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    invalidate_category_counts(db)
    return product_to_out(product)


@router.patch("/products/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)
) -> ProductOut:
    """Partially update a product; omitted fields are left untouched."""
    product = _get_product_or_404(db, product_id)
    data = payload.model_dump(exclude_unset=True)

    if "category_id" in data and data["category_id"] is not None:
        _require_category(db, data["category_id"])

    if "name" in data and data["name"]:
        name = data["name"].strip()
        if name != product.name:
            product.slug = unique_slug(
                db, Product, name, fallback="product", exclude_id=product.id
            )
        product.name = name

    for field in (
        "description",
        "stock",
        "brand",
        "category_id",
        "is_featured",
        "is_active",
    ):
        if field in data and data[field] is not None:
            setattr(product, field, data[field])

    if "price" in data and data["price"] is not None:
        product.price = money(data["price"])
    if "compare_at_price" in data:
        product.compare_at_price = (
            money(data["compare_at_price"])
            if data["compare_at_price"] is not None
            else None
        )
    if "images" in data and data["images"] is not None:
        product.images = list(data["images"])
    if "tags" in data and data["tags"] is not None:
        product.tags = [t.strip() for t in data["tags"] if t.strip()]

    db.commit()
    db.refresh(product)

    invalidate_category_counts(db)
    return product_to_out(product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> Response:
    """Remove a product.

    A product that appears on an existing order is *soft* deleted - flipping
    ``is_active`` off - because hard-deleting it would orphan order history that
    customers can still open.  Anything never ordered is removed outright.
    """
    product = _get_product_or_404(db, product_id)

    ordered = db.scalar(
        select(func.count(OrderItem.id)).where(OrderItem.product_id == product.id)
    )
    if ordered:
        product.is_active = False
    else:
        db.delete(product)

    db.commit()
    invalidate_category_counts(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
def _get_order_or_404(db: Session, order_number: str) -> Order:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_number == order_number)
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/orders", response_model=PaginatedResponse[OrderOut])
def list_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None, description="Order number or customer"),
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> PaginatedResponse[OrderOut]:
    """Every order in the system, newest first."""
    page, page_size, offset = paginate_params(page, page_size)

    stmt = select(Order).options(selectinload(Order.items))
    count_stmt = select(func.count(Order.id))

    if status_filter and status_filter != "all":
        if status_filter not in ORDER_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown status '{status_filter}'. Expected one of: "
                + ", ".join(ORDER_STATUSES),
            )
        stmt = stmt.where(Order.status == status_filter)
        count_stmt = count_stmt.where(Order.status == status_filter)

    if search:
        term = f"%{search.strip().lower()}%"
        condition = or_(
            func.lower(Order.order_number).like(term),
            func.lower(Order.ship_name).like(term),
            func.lower(Order.ship_phone).like(term),
        )
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    total = int(db.scalar(count_stmt) or 0)
    rows = (
        db.scalars(
            stmt.order_by(Order.created_at.desc(), Order.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        .unique()
        .all()
    )

    return PaginatedResponse.create(
        [order_to_out(o) for o in rows], total, page, page_size
    )


@router.get("/orders/{order_number}", response_model=OrderOut)
def get_order(order_number: str, db: Session = Depends(get_db)) -> OrderOut:
    """Full detail for one order."""
    return order_to_out(_get_order_or_404(db, order_number))


class OrderStatusUpdate(BaseModel):
    """Body of ``PATCH /api/admin/orders/{order_number}``."""

    status: Optional[str] = None
    payment_status: Optional[str] = None


@router.patch("/orders/{order_number}", response_model=OrderOut)
def update_order(
    order_number: str,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
) -> OrderOut:
    """Move an order through its lifecycle.

    Changing to or away from ``cancelled`` also corrects the stock and sold
    counts, so the catalog stays consistent with what was actually shipped.
    """
    order = _get_order_or_404(db, order_number)

    new_status = payload.status
    new_payment_status = payload.payment_status

    if new_status is None and new_payment_status is None:
        raise HTTPException(
            status_code=400, detail="Provide a status or payment_status to update"
        )

    if new_status is not None:
        if new_status not in ORDER_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown status '{new_status}'. Expected one of: "
                + ", ".join(ORDER_STATUSES),
            )

        if new_status != order.status:
            # Cancelling returns the reserved stock to the catalog.
            if new_status == "cancelled" and order.status != "cancelled":
                for item in order.items or []:
                    product = db.get(Product, item.product_id)
                    if product is not None:
                        product.stock = int(product.stock or 0) + int(item.quantity or 0)
                        product.sold_count = max(
                            0, int(product.sold_count or 0) - int(item.quantity or 0)
                        )
                if order.payment_status == "paid":
                    order.payment_status = "refunded"

            # Un-cancelling takes it back out again.
            elif order.status == "cancelled" and new_status != "cancelled":
                for item in order.items or []:
                    product = db.get(Product, item.product_id)
                    if product is not None:
                        product.stock = max(
                            0, int(product.stock or 0) - int(item.quantity or 0)
                        )
                        product.sold_count = int(product.sold_count or 0) + int(
                            item.quantity or 0
                        )

            # Cash on delivery settles when the parcel lands.
            if new_status == "delivered" and order.payment_method == "cod":
                order.payment_status = "paid"

            order.status = new_status
            timeline = list(order.timeline or [])
            timeline.append(
                timeline_entry(
                    new_status,
                    note=f"Status updated to {new_status} by store admin",
                )
            )
            order.timeline = timeline

    if new_payment_status is not None:
        if new_payment_status not in PAYMENT_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown payment status '{new_payment_status}'. Expected one of: "
                + ", ".join(PAYMENT_STATUSES),
            )
        order.payment_status = new_payment_status

    order.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return order_to_out(order)


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
@router.get("/customers", response_model=PaginatedResponse[CustomerOut])
def list_customers(
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> PaginatedResponse[CustomerOut]:
    """Customer directory enriched with lifetime order metrics."""
    page, page_size, offset = paginate_params(page, page_size)

    stmt = select(User)
    count_stmt = select(func.count(User.id))

    if search:
        term = f"%{search.strip().lower()}%"
        condition = or_(
            func.lower(User.name).like(term),
            func.lower(User.email).like(term),
            func.lower(func.coalesce(User.phone, "")).like(term),
        )
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    total = int(db.scalar(count_stmt) or 0)
    users = (
        db.scalars(
            stmt.order_by(User.created_at.desc(), User.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        .unique()
        .all()
    )

    metrics = customer_metrics(db, [u.id for u in users])
    items = [
        CustomerOut(
            id=u.id,
            name=u.name,
            email=u.email,
            phone=u.phone,
            avatar_url=u.avatar_url,
            role=u.role if u.role in ("user", "admin") else "user",
            created_at=u.created_at,
            **metrics.get(
                u.id, {"orders_count": 0, "total_spent": 0.0, "last_order_at": None}
            ),
        )
        for u in users
    ]
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/customers/{user_id}/orders", response_model=List[OrderOut])
def customer_orders(user_id: int, db: Session = Depends(get_db)) -> List[OrderOut]:
    """Recent orders for one customer - powers the detail drawer."""
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    rows = (
        db.scalars(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(20)
        )
        .unique()
        .all()
    )
    return [order_to_out(o) for o in rows]


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------
def _get_coupon_or_404(db: Session, coupon_id: int) -> Coupon:
    coupon = db.get(Coupon, coupon_id)
    if coupon is None:
        raise HTTPException(status_code=404, detail="Coupon not found")
    return coupon


def _validate_coupon_value(coupon_type: str, value: float) -> None:
    if coupon_type == "percent" and value > 100:
        raise HTTPException(
            status_code=400, detail="A percentage coupon cannot exceed 100%"
        )


@router.get("/coupons", response_model=List[CouponOut])
def list_coupons(db: Session = Depends(get_db)) -> List[CouponOut]:
    """Every coupon, newest first."""
    rows = db.scalars(select(Coupon).order_by(Coupon.created_at.desc())).all()
    return [coupon_to_out(c) for c in rows]


@router.post("/coupons", response_model=CouponOut, status_code=status.HTTP_201_CREATED)
def create_coupon(payload: CouponCreate, db: Session = Depends(get_db)) -> CouponOut:
    """Create a discount code."""
    code = payload.code.strip().upper()
    if db.scalar(select(Coupon).where(Coupon.code == code)) is not None:
        raise HTTPException(
            status_code=400, detail="A coupon with this code already exists"
        )
    _validate_coupon_value(payload.type, payload.value)

    coupon = Coupon(
        code=code,
        type=payload.type,
        value=money(payload.value),
        min_order=money(payload.min_order),
        max_discount=(
            money(payload.max_discount) if payload.max_discount is not None else None
        ),
        is_active=bool(payload.is_active),
        expires_at=payload.expires_at,
    )
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon_to_out(coupon)


@router.patch("/coupons/{coupon_id}", response_model=CouponOut)
def update_coupon(
    coupon_id: int, payload: CouponUpdate, db: Session = Depends(get_db)
) -> CouponOut:
    """Partially update a coupon."""
    coupon = _get_coupon_or_404(db, coupon_id)
    data = payload.model_dump(exclude_unset=True)

    if "code" in data and data["code"]:
        code = data["code"].strip().upper()
        clash = db.scalar(
            select(Coupon).where(Coupon.code == code, Coupon.id != coupon.id)
        )
        if clash is not None:
            raise HTTPException(
                status_code=400, detail="A coupon with this code already exists"
            )
        coupon.code = code

    new_type = data.get("type", coupon.type)
    new_value = data.get("value", coupon.value)
    _validate_coupon_value(new_type, float(new_value or 0.0))

    if "type" in data and data["type"] is not None:
        coupon.type = data["type"]
    if "value" in data and data["value"] is not None:
        coupon.value = money(data["value"])
    if "min_order" in data and data["min_order"] is not None:
        coupon.min_order = money(data["min_order"])
    if "max_discount" in data:
        coupon.max_discount = (
            money(data["max_discount"]) if data["max_discount"] is not None else None
        )
    if "is_active" in data and data["is_active"] is not None:
        coupon.is_active = bool(data["is_active"])
    if "expires_at" in data:
        coupon.expires_at = data["expires_at"]

    db.commit()
    db.refresh(coupon)
    return coupon_to_out(coupon)


@router.delete("/coupons/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_coupon(coupon_id: int, db: Session = Depends(get_db)) -> Response:
    """Permanently remove a coupon."""
    db.delete(_get_coupon_or_404(db, coupon_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------
@router.get("/categories", response_model=List[CategoryOut])
def list_categories(db: Session = Depends(get_db)) -> List[CategoryOut]:
    """All categories with their live product counts."""
    counts = category_counts_map(db)
    rows = db.scalars(select(Category).order_by(Category.name)).all()
    return [category_to_out(c, counts.get(c.id, 0)) for c in rows]


@router.post(
    "/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED
)
def create_category(
    payload: CategoryCreate, db: Session = Depends(get_db)
) -> CategoryOut:
    """Create a category."""
    category = Category(
        name=payload.name.strip(),
        slug=unique_slug(
            db, Category, payload.slug or payload.name, fallback="category"
        ),
        description=payload.description or "",
        image_url=payload.image_url or "",
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category_to_out(category, 0)


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)
) -> CategoryOut:
    """Partially update a category."""
    category = _require_category(db, category_id)
    data = payload.model_dump(exclude_unset=True)

    if "name" in data and data["name"]:
        name = data["name"].strip()
        if name != category.name and not data.get("slug"):
            category.slug = unique_slug(
                db, Category, name, fallback="category", exclude_id=category.id
            )
        category.name = name

    if data.get("slug"):
        category.slug = unique_slug(
            db, Category, data["slug"], fallback="category", exclude_id=category.id
        )
    if "description" in data and data["description"] is not None:
        category.description = data["description"]
    if "image_url" in data and data["image_url"] is not None:
        category.image_url = data["image_url"]

    db.commit()
    db.refresh(category)
    return category_to_out(category)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> Response:
    """Delete an empty category.

    Categories holding products are refused rather than cascade-deleted, so a
    mis-click can never wipe out part of the catalog.
    """
    category = _require_category(db, category_id)

    remaining = db.scalar(
        select(func.count(Product.id)).where(Product.category_id == category.id)
    )
    if remaining:
        raise HTTPException(
            status_code=400,
            detail="Move or delete this category's products first",
        )

    db.delete(category)
    db.commit()
    invalidate_category_counts(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
