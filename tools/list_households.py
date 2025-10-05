#!/usr/bin/env python3
"""Utility to list recent households from the Family AI API."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import requests

DEFAULT_BASE_URL = os.environ.get("FAMILY_AI_API_BASE", "http://127.0.0.1:8080/api")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List the most recent households from the Family AI Companion API",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="API base URL (default: %(default)s)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of households to show (default: %(default)s)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON instead of a table",
    )
    return parser.parse_args()


def fetch_households(base_url: str) -> list[dict[str, Any]]:
    url = base_url.rstrip("/") + "/admin/households"
    response = requests.get(url, timeout=10)
    if response.status_code != requests.codes.ok:
        raise SystemExit(f"Request failed ({response.status_code}): {response.text}")
    payload = response.json()
    return payload.get("households", [])


def main() -> None:
    args = parse_args()
    households = fetch_households(args.base_url)
    if args.limit:
        households = households[: args.limit]

    if args.json:
        json.dump(households, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return

    if not households:
        print("(no households returned)")
        return

    headers = ["id", "name", "language_preference", "country", "primary_email", "created_at"]
    widths = [max(len(str(row.get(h, ""))) for row in households + [{h: h}]) for h in headers]

    def format_row(row: dict[str, Any]) -> str:
        return " | ".join(str(row.get(h, ""))[: width].ljust(width) for h, width in zip(headers, widths, strict=True))

    header_line = format_row({h: h for h in headers})
    separator = "-+-".join("-" * width for width in widths)

    print(header_line)
    print(separator)
    for row in households:
        print(format_row(row))


if __name__ == "__main__":
    main()
