"""
==========================================================
NEXORA AI
Prospect Repository
==========================================================

Repository responsible for CRUD operations for backlink
prospects.

Features
--------
- Enterprise Repository Pattern
- SQLite UPSERT support
- Bulk operations
- Search & pagination
- Strong typing
- JSON field handling
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from dashboard.models import Prospect, SearchFilters
from dashboard.repositories.base_repository import BaseRepository


class ProspectRepository(BaseRepository):
    """
    Repository responsible for all Prospect persistence.
    """

    TABLE_NAME = "prospects"

    # =====================================================
    # SQL
    # =====================================================

    SQL_GET_BY_ID = """
    SELECT *
    FROM prospects
    WHERE id=?
    """

    SQL_GET_BY_URL = """
    SELECT *
    FROM prospects
    WHERE url=?
    """

    SQL_COUNT = """
    SELECT COUNT(*)
    FROM prospects
    """

    SQL_EXISTS = """
    SELECT EXISTS(
        SELECT 1
        FROM prospects
        WHERE url=?
    )
    """

    SQL_DELETE = """
    DELETE
    FROM prospects
    WHERE id=?
    """

    SQL_DELETE_ALL = """
    DELETE
    FROM prospects
    """

    SQL_LIST = """
    SELECT *
    FROM prospects
    ORDER BY priority_score DESC
    """

    SQL_UPSERT = """
    INSERT INTO prospects (

        title,
        url,
        description,
        category,
        emails,
        phones,
        contact_page,
        about_page,
        write_for_us,
        social_links,
        niche,
        summary,
        accepts_guest_posts,
        backlink_value,
        reason,
        priority_score,
        priority,
        status,
        notes,
        source,
        created_at,
        last_scanned

    )

    VALUES (
        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
    )

    ON CONFLICT(url)

    DO UPDATE SET

        title=excluded.title,
        description=excluded.description,
        category=excluded.category,
        emails=excluded.emails,
        phones=excluded.phones,
        contact_page=excluded.contact_page,
        about_page=excluded.about_page,
        write_for_us=excluded.write_for_us,
        social_links=excluded.social_links,
        niche=excluded.niche,
        summary=excluded.summary,
        accepts_guest_posts=excluded.accepts_guest_posts,
        backlink_value=excluded.backlink_value,
        reason=excluded.reason,
        priority_score=excluded.priority_score,
        priority=excluded.priority,
        status=excluded.status,
        notes=excluded.notes,
        source=excluded.source,
        last_scanned=excluded.last_scanned
    """

    # =====================================================
    # Constructor
    # =====================================================

    def __init__(self, db):

        super().__init__(db)

    # =====================================================
    # Mapping Helpers
    # =====================================================

    def _from_row(
        self,
        row,
    ) -> Prospect:
        """
        Convert sqlite.Row -> Prospect.
        """

        return Prospect(

            id=row["id"],

            title=row["title"],

            url=row["url"],

            description=row["description"],

            category=row["category"],

            emails=self.decode_json(
                row["emails"]
            ),

            phone_numbers=self.decode_json(
                row["phones"]
            ),

            contact_page=row["contact_page"],

            about_page=row["about_page"],

            write_for_us=row["write_for_us"],

            social_links=self.decode_json(
                row["social_links"]
            ),

            niche=row["niche"],

            summary=row["summary"],

            accepts_guest_posts=bool(
                row["accepts_guest_posts"]
            ),

            backlink_value=row["backlink_value"],

            reason=row["reason"],

            priority_score=row["priority_score"],

            priority=row["priority"],

            status=row["status"],

            notes=row["notes"],

            source=row["source"],

            created_at=row["created_at"],

            last_scanned=row["last_scanned"],
        )

    def _to_record(
        self,
        prospect: Prospect,
    ) -> tuple[Any, ...]:
        """
        Convert Prospect -> SQLite tuple.

        Used for UPSERT and bulk UPSERT.
        """

        now = self.utc_now()

        return (

            prospect.title,

            prospect.url,

            prospect.description,

            prospect.category,

            self.encode_json(
                prospect.emails
            ),

            self.encode_json(
                prospect.phone_numbers
            ),

            prospect.contact_page,

            prospect.about_page,

            prospect.write_for_us,

            self.encode_json(
                prospect.social_links
            ),

            prospect.niche,

            prospect.summary,

            int(
                prospect.accepts_guest_posts
            ),

            prospect.backlink_value,

            prospect.reason,

            prospect.priority_score,

            prospect.priority,

            prospect.status,

            prospect.notes,

            prospect.source,

            prospect.created_at or now,

            prospect.last_scanned or now,
        )
    # =====================================================
    # CRUD
    # =====================================================

    def exists(
        self,
        url: str,
    ) -> bool:
        """
        Check whether a prospect already exists.
        """

        return bool(
            self.fetch_value(
                self.SQL_EXISTS,
                (url,),
            )
        )

    # -----------------------------------------------------

    def count(self) -> int:
        """
        Return total number of prospects.
        """

        return int(
            self.fetch_value(
                self.SQL_COUNT,
            )
            or 0
        )

    # -----------------------------------------------------

    def get(
        self,
        prospect_id: int,
    ) -> Optional[Prospect]:
        """
        Get prospect by primary key.
        """

        row = self.fetch_one(
            self.SQL_GET_BY_ID,
            (prospect_id,),
        )

        if row is None:
            return None

        return self._from_row(row)

    # -----------------------------------------------------

    def get_by_url(
        self,
        url: str,
    ) -> Optional[Prospect]:
        """
        Get prospect by canonical URL.
        """

        row = self.fetch_one(
            self.SQL_GET_BY_URL,
            (url,),
        )

        if row is None:
            return None

        return self._from_row(row)

    # -----------------------------------------------------

    def upsert(
        self,
        prospect: Prospect,
    ) -> None:
        """
        Insert or update a prospect using SQLite UPSERT.
        """

        self.execute(
            self.SQL_UPSERT,
            self._to_record(prospect),
        )

    # -----------------------------------------------------

    def upsert_many(
        self,
        prospects: Iterable[Prospect],
    ) -> int:
        """
        Bulk UPSERT.

        Returns
        -------
        int
            Number of processed prospects.
        """

        records = [
            self._to_record(p)
            for p in prospects
        ]

        if not records:
            return 0

        self.executemany(
            self.SQL_UPSERT,
            records,
        )

        return len(records)

    # -----------------------------------------------------

    def create(
        self,
        prospect: Prospect,
    ) -> None:
        """
        Alias for upsert().
        """

        self.upsert(prospect)

    # -----------------------------------------------------

    def create_many(
        self,
        prospects: Iterable[Prospect],
    ) -> int:
        """
        Alias for upsert_many().
        """

        return self.upsert_many(
            prospects
        )

    # -----------------------------------------------------

    def list(
        self,
    ) -> list[Prospect]:
        """
        Return all prospects ordered by priority score.
        """

        rows = self.fetch_all(
            self.SQL_LIST,
        )

        return [
            self._from_row(row)
            for row in rows
        ]
    # =====================================================
    # Search Helpers
    # =====================================================

    def _build_search_query(
        self,
        filters: SearchFilters,
    ) -> tuple[str, list[Any]]:
        """
        Build a dynamic search query from SearchFilters.
        """

        sql = [
            "SELECT *",
            "FROM prospects",
            "WHERE 1=1",
        ]

        params: list[Any] = []

        # ----------------------------------------------
        # Keyword
        # ----------------------------------------------

        if filters.keyword:

            sql.append(
                """
                AND (
                    title LIKE ?
                    OR url LIKE ?
                    OR description LIKE ?
                    OR niche LIKE ?
                    OR summary LIKE ?
                )
                """
            )

            keyword = f"%{filters.keyword}%"

            params.extend(
                [
                    keyword,
                    keyword,
                    keyword,
                    keyword,
                    keyword,
                ]
            )

        # ----------------------------------------------
        # Category
        # ----------------------------------------------

        if filters.category:

            sql.append(
                "AND category=?"
            )

            params.append(
                filters.category
            )

        # ----------------------------------------------
        # Status
        # ----------------------------------------------

        if filters.status:

            sql.append(
                "AND status=?"
            )

            params.append(
                filters.status
            )

        # ----------------------------------------------
        # Priority
        # ----------------------------------------------

        if getattr(filters, "priority", None):

            sql.append(
                "AND priority=?"
            )

            params.append(
                filters.priority
            )

        # ----------------------------------------------
        # Minimum Score
        # ----------------------------------------------

        if getattr(filters, "minimum_score", None):

            sql.append(
                "AND priority_score>=?"
            )

            params.append(
                filters.minimum_score
            )

        # ----------------------------------------------
        # Guest Posts
        # ----------------------------------------------

        if getattr(
            filters,
            "accepts_guest_posts",
            None,
        ) is not None:

            sql.append(
                "AND accepts_guest_posts=?"
            )

            params.append(
                int(filters.accepts_guest_posts)
            )

        # ----------------------------------------------
        # Source
        # ----------------------------------------------

        if getattr(filters, "source", None):

            sql.append(
                "AND source=?"
            )

            params.append(
                filters.source
            )

        # ----------------------------------------------
        # Order
        # ----------------------------------------------

        sql.append(
            """
            ORDER BY
                priority_score DESC,
                created_at DESC
            """
        )

        return (
            "\n".join(sql),
            params,
        )

    # =====================================================
    # Search
    # =====================================================

    def search(
        self,
        filters: SearchFilters,
    ) -> list[Prospect]:
        """
        Search prospects using SearchFilters.
        """

        sql, params = self._build_search_query(
            filters
        )

        rows = self.fetch_all(
            sql,
            params,
        )

        return [
            self._from_row(row)
            for row in rows
        ]

    # -----------------------------------------------------

    def paginate(
        self,
        page: int = 1,
        page_size: int = 50,
        filters: Optional[SearchFilters] = None,
    ) -> list[Prospect]:
        """
        Return a paginated result set.
        """

        if page < 1:
            page = 1

        if page_size < 1:
            page_size = 50

        if filters is None:
            filters = SearchFilters()

        sql, params = self._build_search_query(
            filters
        )

        sql += "\nLIMIT ? OFFSET ?"

        params.extend(
            [
                page_size,
                (page - 1) * page_size,
            ]
        )

        rows = self.fetch_all(
            sql,
            params,
        )

        return [
            self._from_row(row)
            for row in rows
        ]
    # =====================================================
    # Delete
    # =====================================================

    def delete(
        self,
        prospect_id: int,
    ) -> None:
        """
        Delete a prospect by primary key.
        """

        self.execute(
            self.SQL_DELETE,
            (prospect_id,),
        )

    # -----------------------------------------------------

    def delete_many(
        self,
        prospect_ids: Iterable[int],
    ) -> int:
        """
        Delete multiple prospects.

        Returns
        -------
        int
            Number of requested deletions.
        """

        ids = list(prospect_ids)

        if not ids:
            return 0

        self.executemany(
            self.SQL_DELETE,
            [
                (prospect_id,)
                for prospect_id in ids
            ],
        )

        return len(ids)

    # -----------------------------------------------------

    def truncate(self) -> None:
        """
        Remove all prospects from the table.
        """

        self.execute(
            self.SQL_DELETE_ALL
        )

    # =====================================================
    # Compatibility Aliases
    # =====================================================

    def add(
        self,
        prospect: Prospect,
    ) -> None:
        """
        Backward-compatible alias.

        Existing code calling add()
        will continue to work.
        """

        self.upsert(prospect)

    # -----------------------------------------------------

    def update(
        self,
        prospect: Prospect,
    ) -> None:
        """
        Backward-compatible alias.

        Existing code calling update()
        will continue to work.
        """

        self.upsert(prospect)

    # -----------------------------------------------------

    def delete_all(self) -> None:
        """
        Backward-compatible alias.
        """

        self.truncate()

    # =====================================================
    # Utility
    # =====================================================

    def all(self) -> list[Prospect]:
        """
        Alias for list().
        """

        return self.list()

    # -----------------------------------------------------

    def first(self) -> Optional[Prospect]:
        """
        Return the highest-priority prospect.
        """

        rows = self.fetch_all(
            """
            SELECT *
            FROM prospects
            ORDER BY priority_score DESC
            LIMIT 1
            """
        )

        if not rows:
            return None

        return self._from_row(rows[0])

    # -----------------------------------------------------

    def get_many(
        self,
        urls: Iterable[str],
    ) -> list[Prospect]:
        """
        Fetch multiple prospects by URL.
        """

        urls = list(urls)

        if not urls:
            return []

        placeholders = ",".join(
            "?" for _ in urls
        )

        sql = f"""
        SELECT *
        FROM prospects
        WHERE url IN ({placeholders})
        ORDER BY priority_score DESC
        """

        rows = self.fetch_all(
            sql,
            urls,
        )

        return [
            self._from_row(row)
            for row in rows
        ]
