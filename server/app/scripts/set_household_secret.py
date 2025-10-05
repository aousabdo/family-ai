"""CLI to set or update a household secret for chat login."""
from __future__ import annotations

import argparse

from app.db import crud
from app.db.session import session_scope


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or update a household secret")
    parser.add_argument("household_id", help="Household identifier (e.g. household-123)")
    parser.add_argument("secret", help="Secret that families will type in the login modal")
    parser.add_argument(
        "--echo", action="store_true", help="Print the secret back (useful for scripting)"
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
    main()
