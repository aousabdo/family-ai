#!/usr/bin/env python3
"""Set or update the household secret used for chat login."""
from __future__ import annotations

import argparse
import os

from app.db import crud
from app.db.session import session_scope


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update a household secret.")
    parser.add_argument("household_id", help="Household identifier (e.g. household-123)")
    parser.add_argument("secret", help="New secret that the family will type in the login modal")
    parser.add_argument(
        "--echo", action="store_true", help="Print the secret back (useful when scripting)"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    household_id = args.household_id.strip()
    secret = args.secret.strip()
    if not household_id:
        raise SystemExit("household_id cannot be blank")
    if not secret:
        raise SystemExit("secret cannot be blank")

    with session_scope() as session:
        crud.set_household_secret(session, household_id, secret)
        session.flush()

    print(f"Secret set for household: {household_id}")
    if args.echo:
        print(f"Secret: {secret}")


if __name__ == "__main__":
    # Guard against accidentally running outside the server container.
    # When executed via `docker compose exec server ...`, WORKDIR=/app and import succeeds.
    if not os.environ.get("DATABASE_URL"):
        print("Warning: DATABASE_URL not set – make sure you run this inside the server container.")
    main()
