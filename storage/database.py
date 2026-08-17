"""Backward-compatible database initialization entry point."""

from dashboard.database import db


def initialize_database():
    """Return the initialized shared database manager."""
    return db


if __name__ == "__main__":
    initialize_database()
    print("Database ready.")
