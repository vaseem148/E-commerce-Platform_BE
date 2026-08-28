"""Idempotent database seeding.

Running this twice is safe: unless ``force=True`` is passed the seeder returns
immediately when the catalog already has products.  ``force=True`` wipes the
seeded tables first, so ``python seed.py --force`` always produces the same
database - the RNG is pinned to a fixed seed, so the demo data is reproducible.

The order history is deliberately backdated across the last 60 days with a
realistic status mix, because an admin dashboard with every order created "now"
produces a revenue chart that is a single spike and proves nothing.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.seed_data import CATEGORIES, COUPONS, CUSTOMERS, PRODUCTS, REVIEW_POOL
from app.db.session import SessionLocal, init_db
from app.models.address import Address
from app.models.applied_coupon import CartCoupon
from app.models.cart import CartItem
from app.models.category import Category
from app.models.coupon import Coupon
from app.models.order import Order, OrderItem, build_order_number
from app.models.product import Product
from app.models.review import Review
from app.models.user import User
from app.models.wishlist import WishlistItem
from app.services.serializers import compute_discount, compute_totals, money
from app.services.slugs import slugify

RNG_SEED = 1337
ORDER_HISTORY_DAYS = 60

# Weighted so most historical orders have completed - which is what a real
# store's history looks like, and what makes the revenue chart meaningful.
STATUS_WEIGHTS = [
    ("delivered", 52),
    ("shipped", 14),
    ("packed", 9),
    ("confirmed", 8),
    ("pending", 7),
    ("cancelled", 10),
]

PAYMENT_METHOD_WEIGHTS = [("upi", 42), ("card", 26), ("cod", 22), ("netbanking", 10)]

STATUS_NOTES = {
    "pending": "Order placed and awaiting confirmation",
    "confirmed": "Payment confirmed, preparing your items",
    "packed": "Packed and handed to the courier",
    "shipped": "Shipped and on its way",
    "delivered": "Delivered successfully",
    "cancelled": "Order cancelled",
}

STATUS_SEQUENCE = ["pending", "confirmed", "packed", "shipped", "delivered"]

CITIES = [
    ("Chennai", "Tamil Nadu", "600042"),
    ("Bengaluru", "Karnataka", "560034"),
    ("Mumbai", "Maharashtra", "400058"),
    ("Hyderabad", "Telangana", "500081"),
    ("Pune", "Maharashtra", "411045"),
    ("Kochi", "Kerala", "682024"),
    ("Delhi", "Delhi", "110016"),
    ("Coimbatore", "Tamil Nadu", "641012"),
]

STREETS = [
    "12/4 Kamaraj Avenue",
    "48 Brigade Terrace",
    "7B Lakeview Residency",
    "221 Anna Nagar West",
    "9 Palm Grove Apartments",
    "156 MG Road",
    "33 Rosewood Enclave",
    "88 Green Park Extension",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _weighted_choice(rng: random.Random, weighted: Sequence[tuple]) -> str:
    values = [v for v, _ in weighted]
    weights = [w for _, w in weighted]
    return rng.choices(values, weights=weights, k=1)[0]


def _product_images(slug: str, count: int = 4) -> List[str]:
    """Deterministic, always-resolvable image URLs for a product."""
    return [f"https://picsum.photos/seed/{slug}-{i}/800/800" for i in range(1, count + 1)]


def _category_image(slug: str) -> str:
    return f"https://picsum.photos/seed/cat-{slug}/800/600"


def _avatar(name: str) -> str:
    return f"https://picsum.photos/seed/user-{slugify(name)}/200/200"


def _has_data(db: Session) -> bool:
    return bool(db.scalar(select(func.count(Product.id))))


def _wipe(db: Session) -> None:
    """Delete seeded rows in FK-safe order."""
    for model in (
        OrderItem,
        Order,
        Review,
        CartItem,
        CartCoupon,
        WishlistItem,
        Address,
        Product,
        Category,
        Coupon,
        User,
    ):
        db.execute(delete(model))
    db.commit()


# ---------------------------------------------------------------------------
# Seed steps
# ---------------------------------------------------------------------------
def _seed_categories(db: Session) -> Dict[str, Category]:
    categories: Dict[str, Category] = {}
    for entry in CATEGORIES:
        category = Category(
            name=entry["name"],
            slug=entry["slug"],
            description=entry["description"],
            image_url=_category_image(entry["slug"]),
        )
        db.add(category)
        categories[entry["slug"]] = category
    db.flush()
    return categories


def _seed_products(
    db: Session, categories: Dict[str, Category], rng: random.Random
) -> List[Product]:
    products: List[Product] = []
    used_slugs: set = set()

    for entry in PRODUCTS:
        category = categories[entry["category"]]

        slug = slugify(entry["name"], fallback="product")
        suffix = 2
        while slug in used_slugs:
            slug = f"{slugify(entry['name'])}-{suffix}"
            suffix += 1
        used_slugs.add(slug)

        # Spread creation dates so "newest first" ordering is meaningful and the
        # customers/products created deltas on the dashboard have something to
        # compare against.
        created = datetime.utcnow() - timedelta(
            days=rng.randint(1, 120), hours=rng.randint(0, 23)
        )

        product = Product(
            name=entry["name"],
            slug=slug,
            description=entry["description"],
            price=money(entry["price"]),
            compare_at_price=(
                money(entry["compare_at"]) if entry.get("compare_at") else None
            ),
            stock=int(entry["stock"]),
            brand=entry["brand"],
            category_id=category.id,
            images=_product_images(slug),
            tags=list(entry.get("tags") or []),
            is_featured=bool(entry.get("featured")),
            is_active=True,
            rating=0.0,
            review_count=0,
            sold_count=0,
            created_at=created,
            updated_at=created,
        )
        db.add(product)
        products.append(product)

    db.flush()
    return products


def _seed_users(db: Session, rng: random.Random) -> tuple[User, User, List[User]]:
    now = datetime.utcnow()

    admin = User(
        name=settings.ADMIN_NAME,
        email=settings.ADMIN_EMAIL.lower(),
        password_hash=hash_password(settings.ADMIN_PASSWORD),
        phone="9840100100",
        avatar_url=_avatar(settings.ADMIN_NAME),
        role="admin",
        is_active=True,
        created_at=now - timedelta(days=200),
        updated_at=now - timedelta(days=200),
    )
    demo = User(
        name=settings.DEMO_NAME,
        email=settings.DEMO_EMAIL.lower(),
        password_hash=hash_password(settings.DEMO_PASSWORD),
        phone="9840200200",
        avatar_url=_avatar(settings.DEMO_NAME),
        role="user",
        is_active=True,
        created_at=now - timedelta(days=95),
        updated_at=now - timedelta(days=95),
    )
    db.add_all([admin, demo])

    customers: List[User] = [demo]
    for entry in CUSTOMERS:
        # Spread joins across the last ~100 days so the "new customers" delta on
        # the dashboard compares two non-empty windows.
        joined = now - timedelta(days=rng.randint(1, 100), hours=rng.randint(0, 23))
        user = User(
            name=entry["name"],
            email=entry["email"].lower(),
            password_hash=hash_password("Demo@123"),
            phone=entry["phone"],
            avatar_url=_avatar(entry["name"]),
            role="user",
            is_active=True,
            created_at=joined,
            updated_at=joined,
        )
        db.add(user)
        customers.append(user)

    db.flush()
    return admin, demo, customers


def _seed_addresses(db: Session, users: Sequence[User], rng: random.Random) -> Dict[int, List[Address]]:
    by_user: Dict[int, List[Address]] = {}

    for user in users:
        count = 2 if user.email == settings.DEMO_EMAIL.lower() else rng.randint(1, 2)
        addresses: List[Address] = []
        for index in range(count):
            city, state, pincode = rng.choice(CITIES)
            address = Address(
                user_id=user.id,
                full_name=user.name,
                phone=user.phone or "9840000000",
                line1=rng.choice(STREETS),
                line2="Near Central Park" if index == 0 else None,
                city=city,
                state=state,
                pincode=pincode,
                is_default=(index == 0),
            )
            db.add(address)
            addresses.append(address)
        by_user[user.id] = addresses

    db.flush()
    return by_user


def _seed_coupons(db: Session) -> List[Coupon]:
    now = datetime.utcnow()
    coupons: List[Coupon] = []

    for entry in COUPONS:
        expires_in = entry.get("expires_in_days")
        coupon = Coupon(
            code=entry["code"],
            type=entry["type"],
            value=money(entry["value"]),
            min_order=money(entry["min_order"]),
            max_discount=(
                money(entry["max_discount"]) if entry.get("max_discount") else None
            ),
            is_active=bool(entry["is_active"]),
            expires_at=(now + timedelta(days=expires_in)) if expires_in is not None else None,
            used_count=0,
        )
        db.add(coupon)
        coupons.append(coupon)

    db.flush()
    return coupons


def _seed_reviews(
    db: Session, products: Sequence[Product], users: Sequence[User], rng: random.Random
) -> int:
    """Write reviews, then recompute each product's rating and review_count.

    The denormalised ``rating``/``review_count`` columns are the ones the catalog
    sorts and filters on, so they must agree with the rows written here.
    """
    written = 0

    for product in products:
        # Popular products attract more reviews; a couple get none, which
        # exercises the "no reviews yet" empty state.
        target = rng.choices([0, 1, 2, 3, 4, 5, 6, 7], weights=[4, 8, 14, 18, 18, 16, 12, 10], k=1)[0]
        if target == 0:
            continue

        reviewers = rng.sample(list(users), min(target, len(users)))
        ratings: List[int] = []

        for reviewer in reviewers:
            # Skew positive, the way real catalogs do, but keep enough low
            # ratings that the breakdown bars are not a single block.
            rating = rng.choices([5, 4, 3, 2, 1], weights=[46, 28, 14, 8, 4], k=1)[0]
            title, comment = rng.choice(REVIEW_POOL[rating])
            created = product.created_at + timedelta(
                days=rng.randint(1, 60), hours=rng.randint(0, 23)
            )
            if created > datetime.utcnow():
                created = datetime.utcnow() - timedelta(hours=rng.randint(1, 72))

            db.add(
                Review(
                    product_id=product.id,
                    user_id=reviewer.id,
                    rating=rating,
                    title=title,
                    comment=comment,
                    created_at=created,
                    updated_at=created,
                )
            )
            ratings.append(rating)
            written += 1

        if ratings:
            product.rating = round(sum(ratings) / len(ratings), 1)
            product.review_count = len(ratings)

    db.flush()
    return written


def _order_timeline(status: str, placed: datetime) -> List[dict]:
    """Build the stage history an order of this status would have accumulated."""
    entries: List[dict] = []

    if status == "cancelled":
        entries.append(
            {"status": "pending", "at": placed.isoformat(), "note": STATUS_NOTES["pending"]}
        )
        cancelled_at = placed + timedelta(hours=6)
        entries.append(
            {
                "status": "cancelled",
                "at": cancelled_at.isoformat(),
                "note": STATUS_NOTES["cancelled"],
            }
        )
        return entries

    reached = STATUS_SEQUENCE[: STATUS_SEQUENCE.index(status) + 1]
    for offset, stage in enumerate(reached):
        at = placed + timedelta(hours=offset * 18)
        entries.append({"status": stage, "at": at.isoformat(), "note": STATUS_NOTES[stage]})
    return entries


def _seed_orders(
    db: Session,
    products: Sequence[Product],
    users: Sequence[User],
    addresses: Dict[int, List[Address]],
    coupons: Sequence[Coupon],
    rng: random.Random,
) -> int:
    """Create backdated order history spread across the reporting window."""
    now = datetime.utcnow()
    sellable = [p for p in products if p.stock > 0 or True]  # history may include sold-out items
    usable_coupons = [c for c in coupons if c.is_active and c.code != "EXPIRED10"]

    order_count = rng.randint(46, 58)
    created = 0

    for _ in range(order_count):
        user = rng.choice(list(users))
        user_addresses = addresses.get(user.id) or []
        if not user_addresses:
            continue
        address = user_addresses[0]

        placed = now - timedelta(
            days=rng.randint(0, ORDER_HISTORY_DAYS - 1),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
        )
        status = _weighted_choice(rng, STATUS_WEIGHTS)
        payment_method = _weighted_choice(rng, PAYMENT_METHOD_WEIGHTS)

        line_products = rng.sample(list(sellable), rng.randint(1, 4))
        items: List[OrderItem] = []
        subtotal = 0.0

        for product in line_products:
            quantity = rng.choices([1, 2, 3], weights=[68, 24, 8], k=1)[0]
            line_total = money(product.price * quantity)
            subtotal += line_total
            items.append(
                OrderItem(
                    product_id=product.id,
                    name=product.name,
                    slug=product.slug,
                    image=(product.images or [""])[0],
                    price=money(product.price),
                    quantity=quantity,
                    line_total=line_total,
                    created_at=placed,
                )
            )
            if status != "cancelled":
                product.sold_count = int(product.sold_count or 0) + quantity

        subtotal = money(subtotal)

        # Roughly a third of orders used a coupon.
        coupon: Optional[Coupon] = None
        if usable_coupons and rng.random() < 0.34:
            candidate = rng.choice(usable_coupons)
            if subtotal >= float(candidate.min_order or 0):
                coupon = candidate

        discount = compute_discount(subtotal, coupon)
        totals = compute_totals(subtotal, discount)

        if coupon is not None and totals["discount"] > 0:
            coupon.used_count = int(coupon.used_count or 0) + 1
        else:
            coupon = None

        payment_status = "pending"
        if status == "cancelled":
            payment_status = "refunded" if payment_method != "cod" else "failed"
        elif payment_method != "cod":
            payment_status = "paid"
        elif status == "delivered":
            payment_status = "paid"

        order = Order(
            order_number=f"TMP-{rng.getrandbits(48):012X}",
            user_id=user.id,
            status=status,
            payment_method=payment_method,
            payment_status=payment_status,
            subtotal=totals["subtotal"],
            discount=totals["discount"],
            shipping=totals["shipping"],
            tax=totals["tax"],
            total=totals["total"],
            coupon_code=coupon.code if coupon else None,
            notes=None,
            ship_name=address.full_name,
            ship_phone=address.phone,
            ship_line1=address.line1,
            ship_line2=address.line2,
            ship_city=address.city,
            ship_state=address.state,
            ship_pincode=address.pincode,
            timeline=_order_timeline(status, placed),
            created_at=placed,
            updated_at=placed,
        )
        order.items = items
        db.add(order)
        created += 1

    db.flush()

    # order_number is derived from the primary key, so it can only be assigned
    # once the rows have been flushed and the ids exist.
    for order in db.scalars(select(Order)).unique().all():
        order.order_number = build_order_number(order.id, order.created_at)

    db.flush()
    return created


def _seed_demo_activity(
    db: Session, demo: User, products: Sequence[Product], rng: random.Random
) -> None:
    """Give the demo account a live cart and wishlist so the UI is not empty."""
    in_stock = [p for p in products if p.stock > 0]
    if not in_stock:
        return

    for product in rng.sample(in_stock, min(3, len(in_stock))):
        db.add(
            CartItem(
                user_id=demo.id,
                product_id=product.id,
                quantity=rng.randint(1, 2),
            )
        )

    for product in rng.sample(in_stock, min(5, len(in_stock))):
        db.add(WishlistItem(user_id=demo.id, product_id=product.id))

    db.flush()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def seed_database(force: bool = False) -> Dict[str, int]:
    """Populate the database with demo content.

    Returns a summary of what was created.  When the catalog is already
    populated and ``force`` is False, nothing happens and every count is zero.
    """
    db: Session = SessionLocal()
    summary: Dict[str, int] = {
        "categories": 0,
        "products": 0,
        "users": 0,
        "addresses": 0,
        "coupons": 0,
        "reviews": 0,
        "orders": 0,
    }

    try:
        if _has_data(db) and not force:
            return summary
        if force:
            _wipe(db)

        rng = random.Random(RNG_SEED)

        categories = _seed_categories(db)
        products = _seed_products(db, categories, rng)
        admin, demo, customers = _seed_users(db, rng)
        all_users = [admin] + customers
        addresses = _seed_addresses(db, all_users, rng)
        coupons = _seed_coupons(db)
        review_count = _seed_reviews(db, products, customers, rng)
        order_count = _seed_orders(db, products, customers, addresses, coupons, rng)
        _seed_demo_activity(db, demo, products, rng)

        db.commit()

        summary.update(
            categories=len(categories),
            products=len(products),
            users=len(all_users),
            addresses=sum(len(v) for v in addresses.values()),
            coupons=len(coupons),
            reviews=review_count,
            orders=order_count,
        )
        return summary

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def reset_and_seed() -> Dict[str, int]:
    """Create the schema if needed, then force a fresh seed."""
    init_db()
    return seed_database(force=True)


__all__ = ["seed_database", "reset_and_seed"]
