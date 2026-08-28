# Nexa — Commerce API (Backend)

**Nexa** is a production-quality e-commerce platform: a full storefront, a customer account area, and an admin back office. This repository holds the **backend** — a REST API built with FastAPI and SQLAlchemy 2.0 on SQLite, with JWT authentication, faceted catalog search, server-authoritative cart and coupon pricing, order management, and an admin analytics suite.

The user interface lives in a separate repository (`E-commerce-Platform_FE`). **That frontend expects this API on `http://localhost:8000`.** See [Running the frontend](#running-the-frontend) below — you need both halves running to use the app.

| | |
|---|---|
| **Backend** | this repo — `E-commerce-Platform_BE`, runs on **http://localhost:8000** |
| **Frontend** | `E-commerce-Platform_FE` — Vite + React + TypeScript, runs on **http://localhost:5173** |
| **API docs** | Swagger UI at **http://localhost:8000/docs**, ReDoc at `/redoc`, schema at `/openapi.json` |

No database server to install: SQLite is a single file, and the seeder builds a complete demo catalog.

---

## Table of contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Demo credentials](#demo-credentials)
- [Quick start](#quick-start)
- [Running the frontend](#running-the-frontend)
- [Seeding the database](#seeding-the-database)
- [Smoke test](#smoke-test)
- [API documentation](#api-documentation)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [Data model](#data-model)
- [Endpoint reference](#endpoint-reference)
- [Conventions](#conventions)

---

## Features

### Storefront

| Feature | Notes |
|---|---|
| Faceted catalog search | Filter by category, brand, price range, minimum rating, in-stock, on-sale, tag, free-text search |
| Live facets | Every product query returns brand and category counts plus the price range for the current filter set |
| Six sort orders | `newest`, `price_asc`, `price_desc`, `rating`, `popular`, `name_asc` |
| Product detail | Related products and a star-rating breakdown in one payload |
| Reviews | Paginated, with a rating summary; one review per user per product, author-or-admin delete |
| Cart | Server-authoritative totals — subtotal, discount, shipping, tax and total are computed server-side on every mutation |
| Coupons | Percent and flat codes with minimum-order rules, discount caps, expiry and usage counts |
| Wishlist | Per-user, returns full product objects |
| Pagination | One uniform envelope across every list endpoint |

### Account

| Feature | Notes |
|---|---|
| Register / login | JWT bearer tokens, PBKDF2-SHA256 password hashing at 260k iterations |
| Profile | Update name, phone and avatar |
| Change password | Verifies the current password before rotating |
| Addresses | Full CRUD with a single-default invariant enforced server-side |
| Checkout | Creates an order from the cart, snapshots the shipping address and line items, clears the cart |
| Order history | Paginated and filterable by status |
| Status timeline | Every order carries an append-only timeline of status changes with timestamps and notes |
| Cancel | Permitted only from cancellable states; restocks inventory and marks paid orders refunded |

### Admin

| Feature | Notes |
|---|---|
| Analytics dashboard | Revenue, orders, customers and AOV with period-over-period deltas over a configurable window |
| Gapless revenue series | Days with no orders are filled with zeroes so charts never skip |
| Breakdowns | Order-status distribution, top products by units and revenue, top categories, low-stock list, recent orders |
| Product management | Create, update and delete with automatic slug generation and uniqueness |
| Order management | Status and payment-status transitions, validated against the allowed progression |
| Customer directory | Lifetime spend, order counts and last-order date per customer |
| Coupon management | Full CRUD |
| Authorization | Every `/api/admin/*` route returns **401** anonymous and **403** for a non-admin token |

---

## Tech stack

| Concern | Choice |
|---|---|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (typed `Mapped[...]` declarative models) |
| Database | SQLite (swappable via `DATABASE_URL`) |
| Validation | Pydantic v2 + pydantic-settings |
| Auth | PyJWT (HS256) with PBKDF2-SHA256 hashing from the standard library |
| Server | Uvicorn |

Dependencies are intentionally few — see `requirements.txt`.

---

## Demo credentials

Created by the seeder.

| Role | Email | Password |
|---|---|---|
| Admin | `admin@nexa.com` | `Admin@123` |
| Customer | `demo@nexa.com` | `Demo@123` |

---

## Quick start

> Requires **Python 3.10+**.

### Windows (PowerShell)

```powershell
git clone <url-of-E-commerce-Platform_BE> ep_backend
cd ep_backend

py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python seed.py --force      # build the demo dataset
python run.py               # serves http://localhost:8000
```

If PowerShell blocks the activate script, allow it for the current session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Or use the bundled helper, which creates the venv, installs dependencies and seeds on first run, then prints the URL:

```powershell
.\start.ps1
```

### macOS / Linux

```bash
git clone <url-of-E-commerce-Platform_BE> ep_backend
cd ep_backend

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python seed.py --force
python run.py
```

Or:

```bash
chmod +x start.sh   # first time only
./start.sh
```

### Verify

```bash
curl http://localhost:8000/api/health      # -> {"status":"ok"}
```

Then open **http://localhost:8000/docs**.

### `run.py` options

```
python run.py [--host 127.0.0.1] [--port 8000] [--no-reload] [--log-level info]
```

Auto-reload is on whenever `DEBUG=true`. For production, drive the ASGI app directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Running the frontend

The API is only half the product. In a **second terminal**, from the `E-commerce-Platform_FE` repository:

### Windows (PowerShell)

```powershell
cd ep_frontend
npm install
npm run dev
```

### macOS / Linux

```bash
cd ep_frontend
npm install
npm run dev
```

The app opens at **http://localhost:5173**.

The frontend's Vite dev server proxies `/api` to `http://localhost:8000`, so the browser stays same-origin and no CORS preflight is involved in development. If you instead serve the built SPA from a different origin, add that origin to `CORS_ORIGINS` here (see [Configuration](#configuration)) and build the frontend with `VITE_API_BASE_URL` pointing at this API.

---

## Seeding the database

```bash
python seed.py            # seed only if the catalog is empty
python seed.py --force    # wipe the seeded rows and rebuild
```

A full seed produces:

| Table | Rows |
|---|---:|
| categories | 8 |
| products | 64 |
| users | 14 |
| addresses | 26 |
| coupons | 6 |
| reviews | 272 |
| orders | 58 |

Orders are backdated across the trailing month so the admin dashboard has a realistic revenue series on first load. `AUTO_SEED=true` (the default) also seeds automatically on first boot if the database is empty.

To start completely fresh, delete `nexa.db` (and its `-shm` / `-wal` sidecars) and re-run the seeder.

---

## Smoke test

An end-to-end test that exercises the whole API against a live server.

```bash
# terminal 1
python run.py

# terminal 2
python scripts/smoke_test.py
```

Expected result:

```
==============================================
  PASSED 59    FAILED 0
==============================================
```

It covers health, catalog and facets, filtering and sorting, product detail, reviews, auth, addresses, the cart and coupon lifecycle, order placement and cancellation, wishlist, every admin surface, and the 401/403 authorization boundary.

---

## API documentation

With the server running:

| URL | What |
|---|---|
| http://localhost:8000/docs | **Swagger UI** — interactive; try any endpoint from the browser |
| http://localhost:8000/redoc | ReDoc — reference-style rendering |
| http://localhost:8000/openapi.json | Raw OpenAPI 3 schema |

To call a protected endpoint in Swagger UI: `POST /api/auth/login`, copy `access_token` from the response, click **Authorize**, and paste it.

From the command line:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@nexa.com","password":"Admin@123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:8000/api/admin/stats -H "Authorization: Bearer $TOKEN"
```

---

## Configuration

Settings load from environment variables and an optional `.env`. Copy `.env.example` to `.env` to change anything; every key has a working default.

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | `nexa-super-secret-…` | JWT signing key. **Change in production.** |
| `ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | Token lifetime (one week) |
| `PBKDF2_ITERATIONS` | `260000` | Password hashing cost |
| `DATABASE_URL` | `sqlite:///./nexa.db` | Any SQLAlchemy URL |
| `SQL_ECHO` | `false` | Log every SQL statement |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed origins |
| `DEBUG` | `true` | Enables auto-reload via `run.py` |
| `API_PREFIX` | `/api` | Route prefix |
| `AUTO_SEED` | `true` | Seed on first boot when empty |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | `admin@nexa.com` / `Admin@123` | Seeded admin |
| `DEMO_EMAIL` / `DEMO_PASSWORD` | `demo@nexa.com` / `Demo@123` | Seeded customer |
| `FREE_SHIPPING_THRESHOLD` | `999.0` | Order value above which shipping is free |
| `SHIPPING_FLAT_RATE` | `49.0` | Flat shipping fee below the threshold |
| `TAX_RATE` | `0.05` | 5% GST |
| `CURRENCY` | `INR` | Display currency |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | `12` / `100` | Pagination bounds |

The pricing keys are the **single source of truth**. The cart and every order total are computed server-side from them; the frontend mirrors the same numbers only for pre-checkout estimate copy.

---

## Project structure

```
ep_backend/
├── run.py                    dev entrypoint  (python run.py)
├── seed.py                   seeder CLI      (python seed.py --force)
├── requirements.txt
├── .env.example
├── scripts/
│   └── smoke_test.py         59-check end-to-end suite
└── app/
    ├── main.py               FastAPI app, CORS, error handlers, router wiring
    ├── core/
    │   ├── config.py         pydantic-settings Settings
    │   ├── security.py       PBKDF2 hashing, JWT encode/decode
    │   └── deps.py           DB session, current-user and admin dependencies
    ├── db/
    │   ├── base.py           declarative Base
    │   ├── session.py        engine, SessionLocal, init_db
    │   ├── seed.py           seeding logic
    │   └── seed_data.py      the demo catalog
    ├── models/               SQLAlchemy models, one per table
    ├── schemas/              Pydantic request/response models
    ├── services/
    │   ├── pricing.py        discount, shipping, tax and total maths
    │   ├── analytics.py      dashboard aggregation
    │   ├── serializers.py    ORM -> response shaping
    │   └── slugs.py          unique slug generation
    └── api/v1/               routers: auth, addresses, categories, products,
                              reviews, cart, wishlist, orders, admin
```

---

## Data model

```
User ──< Address
 │
 ├──< CartItem >── Product ──> Category
 ├──< WishlistItem >── Product
 ├──< Review >── Product
 ├──< Order ──< OrderItem
 └──  CartCoupon >── Coupon
```

| Table | Key columns |
|---|---|
| **users** | `id`, `name`, `email` (unique), `password_hash`, `phone`, `avatar_url`, `role` (`user` \| `admin`), `is_active`, `created_at`, `updated_at` |
| **categories** | `id`, `name`, `slug` (unique), `description`, `image_url`, timestamps |
| **products** | `id`, `name`, `slug` (unique), `description`, `price`, `compare_at_price`, `stock`, `brand`, `category_id` → categories, `images` (JSON), `tags` (JSON), `is_featured`, `is_active`, `rating`, `review_count`, `sold_count`, timestamps |
| **reviews** | `id`, `product_id` → products, `user_id` → users, `rating` (1–5), `title`, `comment`, timestamps — unique per (product, user) |
| **addresses** | `id`, `user_id` → users, `full_name`, `phone`, `line1`, `line2`, `city`, `state`, `pincode`, `is_default`, timestamps |
| **cart_items** | `id`, `user_id` → users, `product_id` → products, `quantity`, timestamps |
| **cart_coupons** | Links a user's cart to an applied `Coupon` |
| **wishlist_items** | `id`, `user_id` → users, `product_id` → products |
| **coupons** | `id`, `code` (unique), `type` (`percent` \| `flat`), `value`, `min_order`, `max_discount`, `is_active`, `expires_at`, `used_count`, timestamps |
| **orders** | `id`, `order_number` (unique, e.g. `NEX-2026-000262`), `user_id` → users, `status`, `payment_method`, `payment_status`, `subtotal`, `discount`, `shipping`, `tax`, `total`, `coupon_code`, `notes`, `ship_*` address snapshot, `timeline` (JSON), timestamps |
| **order_items** | `id`, `order_id` → orders, `product_id`, `name`, `slug`, `image`, `price`, `quantity` — a snapshot, so history survives catalog edits |

### Enumerations

| Enum | Values |
|---|---|
| `role` | `user`, `admin` |
| `order.status` | `pending` → `confirmed` → `packed` → `shipped` → `delivered`, plus `cancelled` |
| `payment_method` | `cod`, `card`, `upi`, `netbanking` |
| `payment_status` | `pending`, `paid`, `failed`, `refunded` |
| `coupon.type` | `percent`, `flat` |

### Notable invariants

- **Order items and shipping addresses are snapshots.** Renaming or deleting a product never rewrites past orders.
- **Cart and order money is computed server-side** in `services/pricing.py`; clients never send totals.
- **`timeline` is append-only.** Every accepted status transition appends `{ status, at, note }`.
- **One default address per user** — setting a new default clears the previous one.
- **Cancelling restocks inventory** and flips a paid order to `refunded`.

### Response envelopes

Every list endpoint returns the same shape:

```json
{ "items": [ ... ], "total": 64, "page": 1, "page_size": 12, "pages": 6 }
```

`GET /api/products` adds `facets`; `GET /api/products/{slug}/reviews` adds `summary`. Errors are always `{ "detail": "human readable message" }`, including validation failures, which are flattened from Pydantic's array form into one sentence.

---

## Endpoint reference

Base URL `http://localhost:8000`. **Auth** column: — public · 🔑 bearer token · 🛡 admin only.

### System

| Method | Path | Auth | Description |
|---|---|:--:|---|
| `GET` | `/` | — | API metadata and links |
| `GET` | `/api/health` | — | Liveness probe → `{"status":"ok"}` |

### Auth — `/api/auth`

| Method | Path | Auth | Description |
|---|---|:--:|---|
| `POST` | `/api/auth/register` | — | Create an account. Body `{name, email, password}` → `{access_token, token_type, user}` |
| `POST` | `/api/auth/login` | — | Sign in. Body `{email, password}` → `{access_token, token_type, user}` |
| `GET` | `/api/auth/me` | 🔑 | Current user |
| `PATCH` | `/api/auth/me` | 🔑 | Update `name`, `phone`, `avatar_url` |
| `POST` | `/api/auth/change-password` | 🔑 | Body `{current_password, new_password}` → `{detail}` |

### Catalog — `/api/products`, `/api/categories`

| Method | Path | Auth | Description |
|---|---|:--:|---|
| `GET` | `/api/products` | — | Paginated, faceted listing. Query: `search`, `category` (repeatable), `brand` (repeatable), `min_price`, `max_price`, `min_rating`, `in_stock`, `featured`, `on_sale`, `tag`, `sort`, `page`, `page_size` |
| `GET` | `/api/products/featured` | — | Featured products as a bare array. Query: `limit` (default 8) |
| `GET` | `/api/products/{slug}` | — | Product detail with `related` and `rating_breakdown` |
| `GET` | `/api/categories` | — | All categories as a bare array, each with `product_count` |
| `GET` | `/api/categories/{slug}` | — | One category |

### Reviews

| Method | Path | Auth | Description |
|---|---|:--:|---|
| `GET` | `/api/products/{slug}/reviews` | — | Paginated reviews plus a `summary` with the star distribution. Query: `page`, `page_size` |
| `POST` | `/api/products/{slug}/reviews` | 🔑 | Create a review. Body `{rating, title, comment}`. One per user per product |
| `DELETE` | `/api/reviews/{review_id}` | 🔑 | Delete — author or admin only |

### Cart — `/api/cart`

Every response is the complete recalculated cart.

| Method | Path | Auth | Description |
|---|---|:--:|---|
| `GET` | `/api/cart` | 🔑 | Current cart with totals |
| `POST` | `/api/cart/items` | 🔑 | Add. Body `{product_id, quantity}` |
| `PATCH` | `/api/cart/items/{item_id}` | 🔑 | Set quantity. Body `{quantity}` |
| `DELETE` | `/api/cart/items/{item_id}` | 🔑 | Remove one line |
| `DELETE` | `/api/cart` | 🔑 | Empty the cart |
| `POST` | `/api/cart/coupon` | 🔑 | Apply a code. Body `{code}` |
| `DELETE` | `/api/cart/coupon` | 🔑 | Remove the applied coupon |

### Wishlist — `/api/wishlist`

| Method | Path | Auth | Description |
|---|---|:--:|---|
| `GET` | `/api/wishlist` | 🔑 | Wishlisted products as a bare array |
| `POST` | `/api/wishlist/{product_id}` | 🔑 | Add |
| `DELETE` | `/api/wishlist/{product_id}` | 🔑 | Remove |

### Addresses — `/api/addresses`

| Method | Path | Auth | Description |
|---|---|:--:|---|
| `GET` | `/api/addresses` | 🔑 | The user's addresses as a bare array |
| `POST` | `/api/addresses` | 🔑 | Create |
| `PATCH` | `/api/addresses/{address_id}` | 🔑 | Update (partial) |
| `DELETE` | `/api/addresses/{address_id}` | 🔑 | Delete |

### Orders — `/api/orders`

| Method | Path | Auth | Description |
|---|---|:--:|---|
| `POST` | `/api/orders` | 🔑 | Place an order from the cart. Body `{address_id, payment_method, notes?}`. Snapshots items and address, then clears the cart |
| `GET` | `/api/orders` | 🔑 | Paginated history. Query: `status`, `page`, `page_size` |
| `GET` | `/api/orders/{order_number}` | 🔑 | One order with its `timeline` |
| `POST` | `/api/orders/{order_number}/cancel` | 🔑 | Cancel if cancellable; restocks and refunds |

### Admin — `/api/admin`

All require an admin token: **401** anonymous, **403** for a non-admin.

| Method | Path | Auth | Description |
|---|---|:--:|---|
| `GET` | `/api/admin/stats` | 🛡 | Dashboard payload — KPIs with deltas, gapless `revenue_series`, `status_breakdown`, `top_products`, `top_categories`, `recent_orders`, `low_stock`. Query: `days` (default 30) |
| `GET` | `/api/admin/products` | 🛡 | Paginated. Query: `search`, `category`, `status` (`active` \| `inactive`), `page`, `page_size` |
| `POST` | `/api/admin/products` | 🛡 | Create. Body `{name, description, price, compare_at_price, stock, brand, category_id, images[], tags[], is_featured, is_active}` |
| `PATCH` | `/api/admin/products/{product_id}` | 🛡 | Update (partial) |
| `DELETE` | `/api/admin/products/{product_id}` | 🛡 | Delete |
| `GET` | `/api/admin/orders` | 🛡 | Paginated. Query: `status`, `search`, `page`, `page_size` |
| `GET` | `/api/admin/orders/{order_number}` | 🛡 | Order detail |
| `PATCH` | `/api/admin/orders/{order_number}` | 🛡 | Body `{status?, payment_status?}`; appends a timeline entry |
| `GET` | `/api/admin/customers` | 🛡 | Paginated directory with `orders_count`, `total_spent`, `last_order_at`. Query: `search`, `page`, `page_size` |
| `GET` | `/api/admin/customers/{user_id}/orders` | 🛡 | That customer's orders as a bare array |
| `GET` | `/api/admin/coupons` | 🛡 | All coupons as a bare array |
| `POST` | `/api/admin/coupons` | 🛡 | Create. Body `{code, type, value, min_order, max_discount, is_active, expires_at}` |
| `PATCH` | `/api/admin/coupons/{coupon_id}` | 🛡 | Update (partial) |
| `DELETE` | `/api/admin/coupons/{coupon_id}` | 🛡 | Delete |
| `GET` | `/api/admin/categories` | 🛡 | All categories as a bare array |
| `POST` | `/api/admin/categories` | 🛡 | Create. Body `{name, description, image_url, slug?}` |
| `PATCH` | `/api/admin/categories/{category_id}` | 🛡 | Update (partial) |
| `DELETE` | `/api/admin/categories/{category_id}` | 🛡 | Delete |

### Status codes

| Code | Meaning |
|---|---|
| `200` | OK |
| `201` | Created — register, add to cart, place order, admin creates |
| `204` | No content — deletes |
| `400` | Invalid request (bad coupon, illegal status transition, insufficient stock) |
| `401` | Missing or invalid token |
| `403` | Authenticated but not an admin |
| `404` | Not found |
| `409` | Conflict (duplicate email, duplicate slug or coupon code) |
| `422` | Validation failure, flattened to `{ "detail": "field: message" }` |

---

## Conventions

- **The backend is the source of truth for money.** Discounts, shipping, tax and totals are only ever computed in `services/pricing.py` and returned to the client.
- **Snapshots over joins for history.** Order items and shipping addresses are copied at purchase time.
- **Typed all the way through.** SQLAlchemy 2.0 `Mapped[...]` models and Pydantic v2 schemas; the frontend's `src/types/index.ts` mirrors these response shapes one-to-one.
- **Uniform envelopes and uniform errors**, so clients need exactly one pagination handler and one error handler.
- **Authorization is enforced server-side.** The frontend's admin route guard is a convenience, never the control.
