"""
==========================================================
NEXORA AI
Outreach Repository
Part 1 of 3
==========================================================

Repository responsible for all outreach records.

Responsibilities
----------------
- Outreach CRUD
- Email history
- Duplicate prevention
- Analytics queries

No UI logic.
No business workflow.
"""

from __future__ import annotations

from typing import Any

from dashboard.models import OutreachRecord
from dashboard.repositories.base_repository import BaseRepository


class OutreachRepository(BaseRepository):
    """
    Repository for outreach table.
    """

    TABLE_NAME = "outreach"

    PRIMARY_KEY = "id"

    DEFAULT_ORDER_BY = "created_at"

    DEFAULT_ORDER_DIRECTION = "DESC"

    REQUIRED_COLUMNS = {
        "website",
        "email",
    }

    ALLOWED_COLUMNS = {

        "website",

        "email",

        "subject",

        "body",

        "model",

        "created_at",

    }

    SERIALIZED_COLUMNS = set()

    # ==================================================
    # Row Conversion
    # ==================================================

    @staticmethod
    def _row_to_model(
        row: dict[str, Any] | None,
    ) -> OutreachRecord | None:

        if row is None:
            return None

        return OutreachRecord(

            id=row.get("id"),

            website=row.get(
                "website",
                "",
            ),

            email=row.get(
                "email",
                "",
            ),

            subject=row.get(
                "subject",
                "",
            ),

            body=row.get(
                "body",
                "",
            ),

            model=row.get(
                "model",
                "",
            ),

            created_at=row.get(
                "created_at",
            ),
        )

    # ==================================================
    # Create
    # ==================================================

    def create(
        self,
        record: OutreachRecord,
    ) -> int:
        """
        Insert outreach record.
        """

        values = {

            "website": record.website,

            "email": record.email,

            "subject": record.subject,

            "body": record.body,

            "model": record.model,

            "created_at": (
                record.created_at
                or self.now()
            ),
        }

        return self.insert(values)

    # ==================================================
    # Read
    # ==================================================

    def get(
        self,
        outreach_id: int,
    ) -> OutreachRecord | None:

        row = self.get_by_id(
            outreach_id,
        )

        return self._row_to_model(
            row,
        )

    # --------------------------------------------------

    def get_all_records(
        self,
    ) -> list[OutreachRecord]:

        rows = self.get_all()

        return [

            self._row_to_model(row)

            for row in rows

        ]

    # --------------------------------------------------

    def get_by_email(
        self,
        email: str,
    ) -> list[OutreachRecord]:

        rows = self.find_by(
            "email",
            email,
        )

        return [

            self._row_to_model(row)

            for row in rows

        ]

    # --------------------------------------------------

    def get_by_website(
        self,
        website: str,
    ) -> list[OutreachRecord]:

        rows = self.find_by(
            "website",
            website,
        )

        return [

            self._row_to_model(row)

            for row in rows

        ]

    # --------------------------------------------------

    def latest(
        self,
        limit: int = 20,
    ) -> list[OutreachRecord]:

        rows = self.paginate(
            page=1,
            page_size=limit,
        )

        return [

            self._row_to_model(row)

            for row in rows

        ]
    # ==================================================
    # Update
    # ==================================================

    def update_record(
        self,
        outreach_id: int,
        **changes: Any,
    ) -> bool:
        """
        Update an outreach record.
        """

        if not changes:
            return False

        return self.update(
            outreach_id,
            changes,
        )

    # --------------------------------------------------

    def update_subject(
        self,
        outreach_id: int,
        subject: str,
    ) -> bool:
        """
        Update subject only.
        """

        return self.update(
            outreach_id,
            {
                "subject": subject,
            },
        )

    # --------------------------------------------------

    def update_body(
        self,
        outreach_id: int,
        body: str,
    ) -> bool:
        """
        Update email body only.
        """

        return self.update(
            outreach_id,
            {
                "body": body,
            },
        )

    # ==================================================
    # Delete
    # ==================================================

    def delete_record(
        self,
        outreach_id: int,
    ) -> bool:
        """
        Delete a single outreach record.
        """

        return self.delete(
            outreach_id,
        )

    # --------------------------------------------------

    def delete_by_email(
        self,
        email: str,
    ) -> int:
        """
        Delete all records for an email.
        """

        return self.delete_where(
            "email=?",
            (email,),
        )

    # --------------------------------------------------

    def delete_by_website(
        self,
        website: str,
    ) -> int:
        """
        Delete all records for a website.
        """

        return self.delete_where(
            "website=?",
            (website,),
        )

    # ==================================================
    # Duplicate Detection
    # ==================================================

    def exists_for_email(
        self,
        email: str,
    ) -> bool:
        """
        Check if an email already exists.
        """

        return self.exists(
            self.table_name,
            "email",
            email,
        )

    # --------------------------------------------------

    def exists_for_website(
        self,
        website: str,
    ) -> bool:
        """
        Check if a website already exists.
        """

        return self.exists(
            self.table_name,
            "website",
            website,
        )

    # --------------------------------------------------

    def already_contacted(
        self,
        website: str,
        email: str,
    ) -> bool:
        """
        Determine whether this
        website/email combination
        already exists.
        """

        row = self.fetch_one(
            f"""
            SELECT id
            FROM {self.table_name}
            WHERE website=?
              AND email=?
            LIMIT 1
            """,
            (
                website,
                email,
            ),
        )

        return row is not None

    # ==================================================
    # Statistics
    # ==================================================

    def total_records(
        self,
    ) -> int:
        """
        Total outreach records.
        """

        return self.count()

    # --------------------------------------------------

    def total_unique_websites(
        self,
    ) -> int:
        """
        Count unique websites.
        """

        result = self.fetch_value(
            f"""
            SELECT COUNT(
                DISTINCT website
            )
            FROM {self.table_name}
            """
        )

        return int(result or 0)

    # --------------------------------------------------

    def total_unique_emails(
        self,
    ) -> int:
        """
        Count unique email addresses.
        """

        result = self.fetch_value(
            f"""
            SELECT COUNT(
                DISTINCT email
            )
            FROM {self.table_name}
            """
        )

        return int(result or 0)

    # --------------------------------------------------

    def models_used(
        self,
    ) -> list[str]:
        """
        Return all unique AI models
        used for outreach generation.
        """

        return self.distinct(
            "model",
        )

    # --------------------------------------------------

    def email_history(
        self,
        email: str,
    ) -> list[OutreachRecord]:
        """
        Return chronological email history.
        """

        rows = self.get_many(
            where="email=?",
            params=(email,),
            order_by="created_at ASC",
        )

        return [
            self._row_to_model(row)
            for row in rows
        ]

    # --------------------------------------------------

    def clear(
        self,
    ) -> None:
        """
        Remove every outreach record.
        """

        self.truncate()
    # ==================================================
    # Search & Analytics
    # ==================================================

    def search(
        self,
        keyword: str,
    ) -> list[OutreachRecord]:
        """
        Search outreach records by website,
        email, subject or body.
        """

        rows = super().search(
            keyword=keyword,
            columns=[
                "website",
                "email",
                "subject",
                "body",
            ],
        )

        return [
            self._row_to_model(row)
            for row in rows
        ]

    # --------------------------------------------------

    def recent(
        self,
        days: int,
    ) -> list[OutreachRecord]:
        """
        Return outreach records created
        within the last N days.

        Uses SQLite datetime comparison.
        """

        rows = self.get_many(
            where=(
                "datetime(created_at) >= "
                "datetime('now', ?)"
            ),
            params=(
                f"-{days} days",
            ),
        )

        return [
            self._row_to_model(row)
            for row in rows
        ]

    # --------------------------------------------------

    def count_by_model(
        self,
    ) -> dict[str, int]:
        """
        Count outreach grouped by AI model.
        """

        rows = self.fetch_all(
            f"""
            SELECT
                model,
                COUNT(*) AS total
            FROM {self.table_name}
            GROUP BY model
            ORDER BY total DESC
            """
        )

        return {
            row["model"]: row["total"]
            for row in rows
        }

    # --------------------------------------------------

    def count_by_website(
        self,
    ) -> dict[str, int]:
        """
        Count outreach grouped by website.
        """

        rows = self.fetch_all(
            f"""
            SELECT
                website,
                COUNT(*) AS total
            FROM {self.table_name}
            GROUP BY website
            ORDER BY total DESC
            """
        )

        return {
            row["website"]: row["total"]
            for row in rows
        }

    # --------------------------------------------------

    def count_by_email(
        self,
    ) -> dict[str, int]:
        """
        Count outreach grouped by email.
        """

        rows = self.fetch_all(
            f"""
            SELECT
                email,
                COUNT(*) AS total
            FROM {self.table_name}
            GROUP BY email
            ORDER BY total DESC
            """
        )

        return {
            row["email"]: row["total"]
            for row in rows
        }

    # ==================================================
    # Bulk Operations
    # ==================================================

    def bulk_create(
        self,
        records: list[OutreachRecord],
    ) -> int:
        """
        Bulk insert outreach records.
        """

        if not records:
            return 0

        rows = []

        for record in records:

            rows.append(
                {
                    "website": record.website,
                    "email": record.email,
                    "subject": record.subject,
                    "body": record.body,
                    "model": record.model,
                    "created_at": (
                        record.created_at
                        or self.now()
                    ),
                }
            )

        return self.insert_many(rows)

    # --------------------------------------------------

    def bulk_delete_by_email(
        self,
        emails: list[str],
    ) -> int:
        """
        Delete multiple email histories.
        """

        if not emails:
            return 0

        placeholders = ",".join(
            "?"
            for _ in emails
        )

        return self.delete_where(
            f"email IN ({placeholders})",
            tuple(emails),
        )

    # --------------------------------------------------

    def bulk_delete_by_website(
        self,
        websites: list[str],
    ) -> int:
        """
        Delete multiple website histories.
        """

        if not websites:
            return 0

        placeholders = ",".join(
            "?"
            for _ in websites
        )

        return self.delete_where(
            f"website IN ({placeholders})",
            tuple(websites),
        )

    # ==================================================
    # Validation Hooks
    # ==================================================

    def validate_create(
        self,
        values: dict[str, Any],
    ) -> None:
        """
        Repository-specific validation.
        """

        if not values.get("website"):
            raise ValueError(
                "Website is required."
            )

        if not values.get("email"):
            raise ValueError(
                "Email is required."
            )

    # --------------------------------------------------

    def validate_update(
        self,
        values: dict[str, Any],
    ) -> None:
        """
        Validate update payload.
        """

        if (
            "email" in values
            and not values["email"]
        ):
            raise ValueError(
                "Email cannot be empty."
            )

        if (
            "website" in values
            and not values["website"]
        ):
            raise ValueError(
                "Website cannot be empty."
            )

    # ==================================================
    # Repository Information
    # ==================================================

    @property
    def repository_name(
        self,
    ) -> str:
        return "OutreachRepository"

    # --------------------------------------------------

    def __repr__(
        self,
    ) -> str:

        return (
            f"{self.repository_name}"
            f"(table='{self.table_name}')"
        )