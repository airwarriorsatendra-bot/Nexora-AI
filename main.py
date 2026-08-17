"""Command-line entry point for backlink discovery."""

from __future__ import annotations

import argparse

from agents.manager_agent import ManagerAgent


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover and score backlink prospects.")
    parser.add_argument("keyword", nargs="?", help="Search keyword or a complete website URL.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum results to process.")
    args = parser.parse_args()

    if not args.keyword:
        parser.print_help()
        return 0

    results = ManagerAgent().run(args.keyword, limit=max(1, args.limit))
    print(f"Processed {len(results)} prospect(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
