"""Development entrypoint: ``python run.py`` (or ``py run.py``) starts the API.

For production use uvicorn/gunicorn directly, e.g.::

    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""

from __future__ import annotations

import argparse

import uvicorn

from app.core.config import settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Nexa Commerce API")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=8000, help="Bind port")
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable the auto-reloader (enabled by default in debug mode)",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
    )
    args = parser.parse_args()

    reload_enabled = settings.DEBUG and not args.no_reload

    print(f"\n  {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"  http://{args.host}:{args.port}")
    print(f"  Docs: http://{args.host}:{args.port}/docs\n")

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=reload_enabled,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
