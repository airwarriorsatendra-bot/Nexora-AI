"""Deterministic query generation for research requests."""

from __future__ import annotations

from collections.abc import Iterable

from src.core.enums import ResearchMode
from src.core.interfaces import IQueryGenerator
from src.research.dto.request.research_request import ResearchRequest


class QueryGenerator(IQueryGenerator):
    """Generate stable, de-duplicated queries from a research request."""

    _TEMPLATES: dict[ResearchMode, tuple[str, ...]] = {
        ResearchMode.GUEST_POST: (
            "{industry} guest post",
            "{industry} write for us",
            "{industry} submit article",
            "{industry} become contributor",
            "{industry} guest author",
            "{industry} blogs",
            "{industry} magazine",
            "{industry} news",
            "{industry} resources",
            "{industry} contributors",
        ),
        ResearchMode.DIRECTORY: (
            "{industry} directory",
            "top {industry} companies",
            "best {industry} websites",
            "{industry} listings",
        ),
        ResearchMode.RESOURCE_PAGE: (
            "{industry} resources",
            "{industry} useful links",
            "{industry} recommended sites",
        ),
        ResearchMode.BLOG: (
            "{industry} blog",
            "{industry} blogs",
            "{industry} articles",
            "{industry} websites",
        ),
        ResearchMode.BUSINESS: (
            "{industry} companies",
            "{industry} agency",
            "{industry} services",
            "best {industry}",
        ),
        ResearchMode.LOCAL: (
            "{industry}",
            "{industry} near me",
            "{industry} services",
        ),
        ResearchMode.CUSTOM: (),
        ResearchMode.BROKEN_LINK: (
            "{industry} resources",
            "{industry} useful links",
        ),
        ResearchMode.COMPETITOR: (
            "{industry} competitors",
            "top {industry} websites",
        ),
        ResearchMode.LINK_INSERTION: (
            "{industry} blogs",
            "{industry} articles",
        ),
        ResearchMode.PODCAST: (
            "{industry} podcast",
            "{industry} podcast guest",
        ),
        ResearchMode.NEWS: (
            "{industry} news",
            "{industry} magazine",
        ),
        ResearchMode.FORUM: (
            "{industry} forum",
            "{industry} community",
        ),
        ResearchMode.SAAS: (
            "{industry} software",
            "{industry} saas",
        ),
    }

    @property
    def service_name(self) -> str:
        """Return the service name required by the shared contract."""
        return "QueryGenerator"

    async def generate_queries(self, request: ResearchRequest) -> list[str]:
        """Generate normalized queries while preserving deterministic ordering."""
        if request.custom_queries:
            return self._deduplicate(request.custom_queries)

        industry = self._normalize(request.industry)
        queries: list[str] = []
        for template in self._TEMPLATES[request.research_mode]:
            queries.extend(self._expand_location(template.format(industry=industry), request))
        return self._deduplicate(queries)

    def _expand_location(
        self,
        query: str,
        request: ResearchRequest,
    ) -> tuple[str, ...]:
        """Return generic and progressively more local forms of a query."""
        variants = [query]
        country = self._normalize(request.location.country)
        city = self._normalize(request.location.city)
        state = self._normalize(request.location.state)

        if country:
            variants.append(f"{query} {country}")
        locality = " ".join(part for part in (city, state, country) if part)
        if locality and locality != country:
            variants.append(f"{query} {locality}")
        return tuple(variants)

    @staticmethod
    def _normalize(value: str) -> str:
        """Normalize query text into a search-provider-friendly form."""
        return " ".join(value.lower().split())

    @classmethod
    def _deduplicate(cls, queries: Iterable[str]) -> list[str]:
        """Remove empty and duplicate query strings without changing order."""
        seen: set[str] = set()
        unique: list[str] = []
        for query in queries:
            normalized = cls._normalize(query)
            if len(normalized) < 2 or normalized in seen:
                continue
            seen.add(normalized)
            unique.append(normalized)
        return unique
