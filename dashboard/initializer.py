"""Schema creation and forward-only migration support for the SQLite database."""

from __future__ import annotations

from dashboard.database_manager import DatabaseManager


LATEST_SCHEMA_VERSION = 2


class DatabaseInitializer:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def initialize(self) -> None:
        self.create_schema_table()
        if self.current_version() == 0:
            self.create_tables()
        self.ensure_compatible_schema()
        self.create_indexes()
        self.set_version(LATEST_SCHEMA_VERSION)
        self.verify()

    def create_schema_table(self) -> None:
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
        )

    def current_version(self) -> int:
        row = self.db.fetch_one("SELECT version FROM schema_version LIMIT 1")
        return int(row["version"]) if row else 0

    def set_version(self, version: int) -> None:
        self.db.execute("DELETE FROM schema_version")
        self.db.execute("INSERT INTO schema_version(version) VALUES(?)", (version,))

    def create_tables(self) -> None:
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS prospects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT, url TEXT UNIQUE, description TEXT, category TEXT,
                emails TEXT, phones TEXT, contact_page TEXT, about_page TEXT,
                write_for_us TEXT, social_links TEXT, niche TEXT, summary TEXT,
                accepts_guest_posts INTEGER DEFAULT 0, backlink_value TEXT,
                reason TEXT, priority_score INTEGER DEFAULT 0, priority TEXT,
                status TEXT DEFAULT 'New', notes TEXT, source TEXT,
                created_at TEXT, last_scanned TEXT
            )
            """
        )
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS outreach (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website TEXT, email TEXT, subject TEXT, body TEXT,
                model TEXT, created_at TEXT
            )
            """
        )

    def ensure_compatible_schema(self) -> None:
        """Add columns missing from pre-repository database versions."""
        existing = {row["name"] for row in self.db.fetch_all("PRAGMA table_info(prospects)")}
        required = {
            "description": "TEXT", "emails": "TEXT", "phones": "TEXT",
            "contact_page": "TEXT", "about_page": "TEXT", "write_for_us": "TEXT",
            "social_links": "TEXT", "niche": "TEXT", "summary": "TEXT",
            "accepts_guest_posts": "INTEGER DEFAULT 0", "backlink_value": "TEXT",
            "reason": "TEXT", "priority_score": "INTEGER DEFAULT 0",
            "priority": "TEXT", "status": "TEXT DEFAULT 'New'", "notes": "TEXT",
            "source": "TEXT DEFAULT 'legacy'", "created_at": "TEXT", "last_scanned": "TEXT",
        }
        for name, definition in required.items():
            if name not in existing:
                self.db.execute(f"ALTER TABLE prospects ADD COLUMN {name} {definition}")

    def create_indexes(self) -> None:
        for statement in (
            "CREATE INDEX IF NOT EXISTS idx_prospect_url ON prospects(url)",
            "CREATE INDEX IF NOT EXISTS idx_priority ON prospects(priority_score)",
            "CREATE INDEX IF NOT EXISTS idx_status ON prospects(status)",
            "CREATE INDEX IF NOT EXISTS idx_category ON prospects(category)",
            "CREATE INDEX IF NOT EXISTS idx_outreach_email ON outreach(email)",
        ):
            self.db.execute(statement)

    def run_migrations(self, current_version: int) -> None:
        del current_version
        self.ensure_compatible_schema()
        self.create_indexes()
        self.set_version(LATEST_SCHEMA_VERSION)

    def verify(self) -> None:
        for table in ("schema_version", "prospects", "outreach"):
            if not self.db.table_exists(table):
                raise RuntimeError(f"Required table missing: {table}")
