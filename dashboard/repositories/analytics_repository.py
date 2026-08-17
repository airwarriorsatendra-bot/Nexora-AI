"""
==========================================================
NEXORA AI
Analytics Repository
==========================================================

Read-only analytics repository.

Responsibilities
----------------
- Dashboard metrics
- Charts
- Reports
- Data export

This repository NEVER performs INSERT,
UPDATE or DELETE operations.
"""

from __future__ import annotations

from typing import Any

from dashboard.models import DashboardMetrics
from dashboard.repositories.base_repository import BaseRepository


class AnalyticsRepository(BaseRepository):
    """
    Read-only analytics and reporting repository.
    """

    TABLE_NAME = "prospects"

    # =====================================================
    # SQL
    # =====================================================

    SQL_TOTAL = """
    SELECT COUNT(*)
    FROM prospects
    """

    SQL_HIGH_PRIORITY = """
    SELECT COUNT(*)
    FROM prospects
    WHERE priority='High'
    """

    SQL_WITH_EMAIL = """
    SELECT COUNT(*)
    FROM prospects
    WHERE emails IS NOT NULL
      AND emails!='[]'
    """

    SQL_WITH_PHONE = """
    SELECT COUNT(*)
    FROM prospects
    WHERE phones IS NOT NULL
      AND phones!='[]'
    """

    SQL_AVERAGE_SCORE = """
    SELECT AVG(priority_score)
    FROM prospects
    """

    SQL_RECENT = """
    SELECT *
    FROM prospects
    ORDER BY created_at DESC
    LIMIT ?
    """

    SQL_TOP_PRIORITY = """
    SELECT *
    FROM prospects
    ORDER BY priority_score DESC
    LIMIT ?
    """

    SQL_EXPORT = """
    SELECT *
    FROM prospects
    ORDER BY priority_score DESC
    """

    # =====================================================
    # Constructor
    # =====================================================

    def __init__(self, db):

        super().__init__(db)

    # =====================================================
    # Private Helpers
    # =====================================================

    def _scalar(
        self,
        sql: str,
        params: tuple[Any, ...] | None = None,
        default: Any = 0,
    ) -> Any:
        """
        Execute a scalar query and return
        a default value when NULL.
        """

        value = self.fetch_value(
            sql,
            params,
        )

        return default if value is None else value

    # -----------------------------------------------------

    def _distribution(
        self,
        column: str,
    ) -> list:
        """
        Return grouped counts for a column.

        Only approved columns are allowed.
        """

        allowed = {
            "priority",
            "status",
            "category",
            "accepts_guest_posts",
        }

        if column not in allowed:
            raise ValueError(
                f"Unsupported analytics column: {column}"
            )

        sql = f"""
        SELECT
            {column},
            COUNT(*) AS count
        FROM prospects
        GROUP BY {column}
        ORDER BY count DESC
        """

        return self.fetch_all(sql)
    # =====================================================
    # Dashboard Metrics
    # =====================================================

    def dashboard_metrics(self) -> DashboardMetrics:
        """
        Return dashboard summary metrics.
        """

        total = int(
            self._scalar(
                self.SQL_TOTAL
            )
        )

        high_priority = int(
            self._scalar(
                self.SQL_HIGH_PRIORITY
            )
        )

        with_email = int(
            self._scalar(
                self.SQL_WITH_EMAIL
            )
        )

        with_phone = int(
            self._scalar(
                self.SQL_WITH_PHONE
            )
        )

        average_score = float(
            self._scalar(
                self.SQL_AVERAGE_SCORE,
                default=0.0,
            )
        )

        return DashboardMetrics(

            total=total,

            high_priority=high_priority,

            with_email=with_email,

            with_phone=with_phone,

            average_score=round(
                average_score,
                2,
            ),
        )

    # =====================================================
    # Email Coverage
    # =====================================================

    def email_statistics(self) -> dict[str, float]:
        """
        Return email coverage statistics.
        """

        total = int(
            self._scalar(
                self.SQL_TOTAL
            )
        )

        with_email = int(
            self._scalar(
                self.SQL_WITH_EMAIL
            )
        )

        coverage = (
            round(
                (with_email * 100) / total,
                2,
            )
            if total
            else 0.0
        )

        return {

            "total": total,

            "with_email": with_email,

            "coverage_percent": coverage,
        }

    # =====================================================
    # Distribution Reports
    # =====================================================

    def priority_distribution(self):
        """
        Distribution of priority values.
        """

        return self._distribution(
            "priority"
        )

    # -----------------------------------------------------

    def status_distribution(self):
        """
        Distribution of prospect status.
        """

        return self._distribution(
            "status"
        )

    # -----------------------------------------------------

    def category_distribution(self):
        """
        Distribution of prospect categories.
        """

        return self._distribution(
            "category"
        )

    # -----------------------------------------------------

    def guest_post_statistics(self):
        """
        Distribution of guest-post acceptance.
        """

        return self._distribution(
            "accepts_guest_posts"
        )

    # =====================================================
    # Score Analytics
    # =====================================================

    def score_distribution(self):
        """
        Return all priority scores.

        Useful for charts,
        histograms and dashboards.
        """

        return self.fetch_all(
            """
            SELECT
                priority_score
            FROM prospects
            ORDER BY priority_score DESC
            """
        )
    # =====================================================
    # Reports
    # =====================================================

    def recent_prospects(
        self,
        limit: int = 10,
    ):
        """
        Return the most recently created prospects.
        """

        limit = max(1, int(limit))

        return self.fetch_all(
            self.SQL_RECENT,
            (limit,),
        )

    # -----------------------------------------------------

    def top_priority(
        self,
        limit: int = 25,
    ):
        """
        Return highest scoring prospects.
        """

        limit = max(1, int(limit))

        return self.fetch_all(
            self.SQL_TOP_PRIORITY,
            (limit,),
        )

    # =====================================================
    # Export
    # =====================================================

    def export_dataframe(self):
        """
        Export all prospects as a pandas DataFrame.
        """

        return self.dataframe(
            self.SQL_EXPORT,
        )

    # =====================================================
    # Summary Helpers
    # =====================================================

    def total_prospects(self) -> int:
        """
        Convenience wrapper.
        """

        return int(
            self._scalar(
                self.SQL_TOTAL
            )
        )

    # -----------------------------------------------------

    def average_priority_score(self) -> float:
        """
        Convenience wrapper.
        """

        return round(
            float(
                self._scalar(
                    self.SQL_AVERAGE_SCORE,
                    default=0.0,
                )
            ),
            2,
        )

    # -----------------------------------------------------

    def email_coverage_percent(self) -> float:
        """
        Return email coverage percentage.
        """

        stats = self.email_statistics()

        return float(
            stats["coverage_percent"]
        )

    # -----------------------------------------------------

    def phone_coverage_percent(self) -> float:
        """
        Return phone coverage percentage.
        """

        total = int(
            self._scalar(
                self.SQL_TOTAL
            )
        )

        with_phone = int(
            self._scalar(
                self.SQL_WITH_PHONE
            )
        )

        if total == 0:
            return 0.0

        return round(
            (with_phone * 100) / total,
            2,
        )

    # -----------------------------------------------------

    def has_data(self) -> bool:
        """
        Returns True when the prospects table
        contains at least one record.
        """

        return self.total_prospects() > 0