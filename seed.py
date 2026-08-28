"""Command line seeder.

    python seed.py            # seed only if the catalog is empty
    python seed.py --force    # wipe the seeded tables and rebuild from scratch
"""

from __future__ import annotations

import argparse
import sys

from app.core.config import settings
from app.db.seed import seed_database
from app.db.session import init_db


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the Nexa Commerce database.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing seeded rows and rebuild the demo dataset.",
    )
    args = parser.parse_args()

    print("Creating tables (if missing)...")
    init_db()

    print("Seeding demo data..." if args.force else "Seeding demo data (skipped if present)...")
    summary = seed_database(force=args.force)

    if not any(summary.values()):
        print("\nDatabase already contains products - nothing to do.")
        print("Re-run with --force to rebuild the demo dataset.")
        return 0

    width = max(len(k) for k in summary)
    print("\n  Seeded")
    print("  " + "-" * (width + 10))
    for key, value in summary.items():
        print(f"  {key.ljust(width)}  {value:>6}")
    print("  " + "-" * (width + 10))

    print("\n  Demo accounts")
    print(f"    admin     {settings.ADMIN_EMAIL} / {settings.ADMIN_PASSWORD}")
    print(f"    customer  {settings.DEMO_EMAIL} / {settings.DEMO_PASSWORD}")
    print("\nDone. Start the API with:  python run.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
