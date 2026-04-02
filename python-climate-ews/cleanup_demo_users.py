#!/usr/bin/env python3
import argparse
import sqlite3
from pathlib import Path


DEMO_EMAILS = [
    "john.phiri@example.com",
    "mary.banda@example.com",
    "peter.chanda@example.com",
    "grace.mulenga@example.com",
    "daniel.mwamba@example.com",
]

DEMO_PHONES = [
    "+260977123456",
    "+260966234567",
    "+260955345678",
    "+260944456789",
    "+260933567890",
]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Remove seeded demo users from the SQLite database")
    parser.add_argument(
        "--db",
        default=str((Path(__file__).resolve().parent / "instance" / "climate_ews.db")),
        help="Path to SQLite database file (default: python-climate-ews/instance/climate_ews.db)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print what would be deleted without changing the DB")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    conn = sqlite3.connect(str(db_path), timeout=15)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA busy_timeout=15000")

        cur.execute("SELECT COUNT(*) FROM user")
        before = int(cur.fetchone()[0])

        if args.dry_run:
            cur.execute(
                f"SELECT id, name, email, phone FROM user WHERE email IN ({','.join(['?']*len(DEMO_EMAILS))})",
                DEMO_EMAILS,
            )
            by_email = cur.fetchall()
            cur.execute(
                f"SELECT id, name, email, phone FROM user WHERE phone IN ({','.join(['?']*len(DEMO_PHONES))})",
                DEMO_PHONES,
            )
            by_phone = cur.fetchall()
            print(f"before={before} matches_email={len(by_email)} matches_phone={len(by_phone)} dry_run=1")
            return 0

        cur.execute(
            f"DELETE FROM user WHERE email IN ({','.join(['?']*len(DEMO_EMAILS))})",
            DEMO_EMAILS,
        )
        deleted_email = cur.rowcount

        cur.execute(
            f"DELETE FROM user WHERE phone IN ({','.join(['?']*len(DEMO_PHONES))})",
            DEMO_PHONES,
        )
        deleted_phone = cur.rowcount

        conn.commit()

        cur.execute("SELECT COUNT(*) FROM user")
        after = int(cur.fetchone()[0])

        print(
            f"before={before} after={after} deleted_email={deleted_email} deleted_phone={deleted_phone} dry_run=0"
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

