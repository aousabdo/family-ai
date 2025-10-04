#!/usr/bin/env python3
"""
List all households and their children from the database.
Equivalent to the one-liner run via:
    docker compose exec server python - <<'PY' ... PY
"""

from app.db.session import session_scope
from app.db import models


def list_households():
    """Print household info with children details."""
    with session_scope() as session:
        households = session.query(models.Household).all()
        for h in households:
            print(f"{h.id} • {h.name} • {h.country} • {h.language_preference}")
            for child in h.children:
                print(f"  - {child.name}, {child.age}")


if __name__ == "__main__":
    list_households()
