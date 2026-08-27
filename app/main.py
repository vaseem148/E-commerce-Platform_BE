"""Nexa Commerce API - FastAPI application factory and entrypoint."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import (
    addresses,
    admin,
    auth,
    cart,
    categories,
    orders,
    products,
    reviews,
    wishlist,
)
from app.core.config import settings
from app.db.session import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nexa")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create tables on boot and seed demo data when the database is empty."""
    init_db()

    if settings.AUTO_SEED:
        try:
            # Imported lazily so a seeding problem can never break application
            # start-up or create an import cycle.
            from app.db.seed import seed_database

            seed_database(force=False)
        except Exception as exc:  # noqa: BLE001 - seeding is best-effort
            logger.warning("Database seeding skipped: %s", exc)

    logger.info(
        "%s v%s ready - docs at http://localhost:8000/docs",
        settings.PROJECT_NAME,
        settings.VERSION,
    )
    yield
    logger.info("%s shutting down", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# --- CORS --------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# --- Middleware ---------------------------------------------------------------
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Attach a simple server-timing header - handy while profiling the UI."""
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


# --- Error handling: every error body is {"detail": "..."} --------------------
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    _request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Flatten pydantic validation errors into a single readable sentence."""
    messages = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", []) if part != "body"]
        field = ".".join(location) or "request"
        messages.append(f"{field}: {error.get('msg', 'invalid value')}")

    detail = "; ".join(messages) or "Invalid request payload"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Never leak a traceback to the client."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Something went wrong. Please try again."},
    )


# --- Routers ------------------------------------------------------------------
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(addresses.router, prefix="/api/addresses", tags=["addresses"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(reviews.router, prefix="/api", tags=["reviews"])
app.include_router(cart.router, prefix="/api/cart", tags=["cart"])
app.include_router(wishlist.router, prefix="/api/wishlist", tags=["wishlist"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


# --- Meta endpoints -----------------------------------------------------------
@app.get("/api/health", tags=["meta"], summary="Health check")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/", tags=["meta"], summary="API welcome")
async def root() -> dict:
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "ok",
        "docs": "/docs",
        "health": "/api/health",
        "api_prefix": settings.API_PREFIX,
    }
