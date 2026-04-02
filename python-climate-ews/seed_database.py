#!/usr/bin/env python3
"""
Database Seeder Script
Run this script to populate the database with initial data.
"""

import os
import sys
import argparse

# Add parent directory to path so imports work when run from this folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db
from services.data_seeder import DataSeeder


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Seed Climate EWS database")
    parser.add_argument(
        "--with-samples",
        action="store_true",
        help="Include sample users/alerts (demo data).",
    )
    args = parser.parse_args(argv)

    print("=" * 60)
    print("Climate Early Warning System - Database Seeder")
    print("=" * 60)
    print()

    app = create_app("development")

    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("OK: Database tables created")

        try:
            DataSeeder.seed_all(include_samples=args.with_samples)
        except Exception as exc:
            print(f"\nERROR during seeding: {exc}")
            import traceback

            traceback.print_exc()
            return 1

    print()
    print("=" * 60)
    print("Seeding completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Start the server: flask run")
    print("2. Open the dashboard: http://localhost:5000")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
