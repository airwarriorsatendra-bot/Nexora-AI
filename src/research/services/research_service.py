"""Application service coordinating the research workflow.

This module contains orchestration only. Search, crawling, AI analysis, and
persistence remain behind their existing injected interfaces.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse
from uuid import UUID

from pydantic import ValidationError as PydanticValidationError

from src.core.enums import ResearchPhase, ResearchStatus
from src.core.exceptions import ResearchError
from src.core.interfaces import (
    IAIAnalysisService,
    ICrawlerService,
    IProspectRepository,
    IQueryGenerator,
    IResearchService,
    ISearchProvider,
)
from src.research.domain.prospect import Prospect
from src.research.domain.research_session import ResearchSession
from src.research.dto.request.research_request import ResearchRequest
from src.research.dto.response.research_progress import ResearchProgress
from src.research.dto.response.research_response import ResearchResponse
from src.research.dto.response.research_statistics import ResearchStatistics


class _ResearchCancelled(Exception):
    """Internal, non-error signal for a user-cancelled session."""


@dataclass(slots=True)
class _SessionControl:
    """Transient controls associated with one in-process session."""

    pause_gate: asyncio.Event = field(default_factory=asyncio.Event)
    cancelled: bool = False

    def __post_init__(self) -> None:
        self.pause_gate.set()


class ResearchService(IResearchService):
    """Coordinate a complete research request using immutable domain objects."""

    def __init__(
        self,
        query_generator: IQueryGenerator,
        search_provider: ISearchProvider,
        crawler_service: ICrawlerService,
        ai_analysis_service: IAIAnalysisService,
        prospect_repository: IProspectRepository,
        logger: logging.Logger | None = None,
    ) -> None:
        self._query_generator = query_generator
        self._search_provider = search_provider
        self._crawler_service = crawler_service
        self._ai_analysis_service = ai_analysis_service
        self._prospect_repository = prospect_repository
        self._logger = logger or logging.getLogger(__name__)
        self._sessions: dict[UUID, ResearchSession] = {}
        self._controls: dict[UUID, _SessionControl] = {}

    @property
    def service_name(self) -> str:
        """Return the application-service name."""
        return "ResearchService"

    async def start_research(self, request: ResearchRequest) -> ResearchResponse:
        """Execute research and return its final immutable response."""
        session = self._store(self._initialize_session(request).start())
        self._controls[session.session_id] = _SessionControl()
        self._logger.info(
            "Research session started.",
            extra={
                "session_id": str(session.session_id),
                "request_id": str(request.request_id),
                "industry": request.industry,
                "mode": request.research_mode.value,
            },
        )

        try:
            await self._run_pipeline(session.session_id)
            session = self._get_session(session.session_id)
            if session.status == ResearchStatus.RUNNING:
                self._store(session.complete())
                self._update_progress(
                    session.session_id,
                    phase=ResearchPhase.COMPLETED,
                    percentage=100.0,
                    processed=session.statistics.queries_completed,
                    total=session.statistics.queries_generated,
                    message="Research completed.",
                )
        except _ResearchCancelled:
            self._logger.info(
                "Research session cancelled.",
                extra={"session_id": str(session.session_id)},
            )
        except asyncio.CancelledError:
            await self.cancel_research(str(session.session_id))
            raise
        except Exception as exc:
            self._logger.exception(
                "Research session failed.",
                extra={"session_id": str(session.session_id)},
            )
            self._store(self._get_session(session.session_id).fail(str(exc)))
        finally:
            final_session = self._finalize_session(self._get_session(session.session_id))
            self._log_session_summary(final_session)

        return self._build_response(self._get_session(session.session_id))

    async def pause_research(self, session_id: str) -> None:
        """Pause a running session at its next asynchronous checkpoint."""
        session = self._get_session_from_text(session_id)
        if session.status != ResearchStatus.RUNNING:
            raise ResearchError("Only a running research session can be paused.")

        self._controls[session.session_id].pause_gate.clear()
        self._store(session.model_copy(update={"status": ResearchStatus.PAUSED}))
        self._logger.info("Research session paused.", extra={"session_id": session_id})

    async def resume_research(self, session_id: str) -> None:
        """Resume a paused session."""
        session = self._get_session_from_text(session_id)
        if session.status != ResearchStatus.PAUSED:
            raise ResearchError("Only a paused research session can be resumed.")

        self._store(session.model_copy(update={"status": ResearchStatus.RUNNING}))
        self._controls[session.session_id].pause_gate.set()
        self._logger.info("Research session resumed.", extra={"session_id": session_id})

    async def cancel_research(self, session_id: str) -> None:
        """Cancel a non-terminal session and unblock a paused workflow."""
        session = self._get_session_from_text(session_id)
        if session.status in {
            ResearchStatus.CANCELLED,
            ResearchStatus.COMPLETED,
            ResearchStatus.FAILED,
        }:
            return

        control = self._controls[session.session_id]
        control.cancelled = True
        control.pause_gate.set()
        session = self._store(session.cancel())
        self._update_progress(
            session.session_id,
            phase=session.progress.phase if session.progress else ResearchPhase.INITIALIZING,
            percentage=session.progress.percentage if session.progress else 0.0,
            message="Research cancelled.",
        )

    async def get_progress(self, session_id: str) -> ResearchProgress:
        """Return the latest progress snapshot for a retained session."""
        progress = self._get_session_from_text(session_id).progress
        if progress is None:
            raise ResearchError("Research session has no progress information.")
        return progress

    async def aclose(self) -> None:
        """Release retained, in-process session state during application shutdown."""
        for control in self._controls.values():
            control.cancelled = True
            control.pause_gate.set()
        self._sessions.clear()
        self._controls.clear()

    async def _run_pipeline(self, session_id: UUID) -> None:
        self._update_progress(
            session_id,
            phase=ResearchPhase.GENERATING_QUERIES,
            percentage=5.0,
            message="Generating search queries...",
        )
        await self._checkpoint(session_id)
        request = self._get_session(session_id).request
        queries = await self._query_generator.generate_queries(request)
        await self._checkpoint(session_id)
        self._update_statistics(session_id, queries_generated=len(queries))

        if not queries:
            self._add_warning(session_id, "No research queries were generated.")
            return

        for query_index, query in enumerate(queries, start=1):
            await self._checkpoint(session_id)
            self._update_progress(
                session_id,
                phase=ResearchPhase.SEARCHING,
                percentage=5.0 + ((query_index - 1) / len(queries)) * 70.0,
                processed=query_index - 1,
                total=len(queries),
                current_query=query,
                message=f"Searching: {query}",
            )
            try:
                results = await self._search_provider.search(
                    query=query,
                    max_results=request.max_results,
                )
                await self._checkpoint(session_id)
            except _ResearchCancelled:
                raise
            except Exception as exc:
                self._handle_item_failure(
                    session_id,
                    f"Search failed for '{query}': {exc}",
                    query=query,
                )
            else:
                stats = self._get_session(session_id).statistics
                self._update_statistics(
                    session_id,
                    queries_completed=query_index,
                    websites_discovered=stats.websites_discovered + len(results),
                )
                await self._process_search_results(
                    session_id=session_id,
                    query=query,
                    results=results,
                    query_index=query_index,
                    total_queries=len(queries),
                )

            self._update_progress(
                session_id,
                phase=ResearchPhase.SEARCHING,
                percentage=5.0 + (query_index / len(queries)) * 70.0,
                processed=query_index,
                total=len(queries),
                current_query=query,
                message=f"Completed search {query_index} of {len(queries)}.",
            )

    async def _process_search_results(
        self,
        *,
        session_id: UUID,
        query: str,
        results: list[dict[str, Any]],
        query_index: int,
        total_queries: int,
    ) -> None:
        for result_index, result in enumerate(results, start=1):
            await self._checkpoint(session_id)
            prospect = self._create_prospect(
                result,
                query,
                self._get_session(session_id).request,
            )
            if prospect is None or await self._is_duplicate(session_id, prospect):
                continue

            percentage = self._result_percentage(
                query_index,
                result_index,
                len(results),
                total_queries,
            )
            try:
                prospect = await self._enrich_prospect(
                    session_id,
                    query,
                    prospect,
                    percentage,
                )
                await self._checkpoint(session_id)
                self._update_progress(
                    session_id,
                    phase=ResearchPhase.SAVING_RESULTS,
                    percentage=percentage,
                    current_query=query,
                    current_url=str(prospect.url),
                    message=f"Saving {prospect.domain}...",
                )
                saved_prospect = await self._prospect_repository.save(prospect)
                await self._checkpoint(session_id)
            except _ResearchCancelled:
                raise
            except Exception as exc:
                self._increment(session_id, "failed_websites")
                self._handle_item_failure(
                    session_id,
                    f"Could not process {prospect.domain}: {exc}",
                    url=str(prospect.url),
                )
                continue

            self._store(
                self._get_session(session_id).add_prospect(saved_prospect)
            )
            stats = self._get_session(session_id).statistics
            self._update_statistics(
                session_id,
                prospects_found=stats.prospects_found + 1,
                prospects_saved=stats.prospects_saved + 1,
            )

    async def _enrich_prospect(
        self,
        session_id: UUID,
        query: str,
        prospect: Prospect,
        percentage: float,
    ) -> Prospect:
        options = self._get_session(session_id).request.options
        if options.enable_crawling:
            self._update_progress(
                session_id,
                phase=ResearchPhase.CRAWLING,
                percentage=percentage,
                current_query=query,
                current_url=str(prospect.url),
                message=f"Crawling {prospect.domain}...",
            )
            crawl_data = await self._crawler_service.crawl(str(prospect.url))
            await self._checkpoint(session_id)
            prospect = self._apply_crawl_data(prospect, crawl_data)
            self._increment(session_id, "websites_crawled")

        if options.enable_ai_analysis:
            self._update_progress(
                session_id,
                phase=ResearchPhase.AI_ANALYSIS,
                percentage=percentage,
                current_query=query,
                current_url=str(prospect.url),
                message=f"Analyzing {prospect.domain}...",
            )
            analysis = await self._ai_analysis_service.analyze(
                prospect.model_dump(mode="json")
            )
            await self._checkpoint(session_id)
            prospect = self._apply_ai_analysis(prospect, analysis)
            self._record_ai_score(session_id, prospect.ai_score)

        return prospect

    async def _is_duplicate(self, session_id: UUID, prospect: Prospect) -> bool:
        request = self._get_session(session_id).request
        if not request.options.deduplicate_results:
            return False

        if any(
            item.domain == prospect.domain
            for item in self._get_session(session_id).prospects
        ):
            self._increment(session_id, "duplicates_removed")
            return True

        try:
            exists = await self._prospect_repository.exists_by_domain(
                prospect.domain
            )
        except Exception as exc:
            raise ResearchError(
                f"Unable to check duplicate prospect '{prospect.domain}'."
            ) from exc

        if exists:
            self._increment(session_id, "duplicates_removed")
        return exists

    def _create_prospect(
        self,
        result: dict[str, Any],
        query: str,
        request: ResearchRequest,
    ) -> Prospect | None:
        url = str(result.get("url") or result.get("link") or "").strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            self._logger.warning("Ignoring search result with invalid URL.")
            return None

        domain = parsed.hostname.lower().removeprefix("www.")
        if not self._domain_is_allowed(domain, request):
            return None

        try:
            return Prospect(
                domain=domain,
                url=url,
                title=str(result.get("title") or ""),
                description=str(
                    result.get("description") or result.get("snippet") or ""
                ),
                category=str(result.get("category") or request.industry),
                provider=str(self._search_provider.provider_name),
                research_query=query,
            )
        except PydanticValidationError as exc:
            self._logger.warning(
                "Ignoring invalid normalized search result.",
                extra={"url": url, "error": str(exc)},
            )
            return None

    def _domain_is_allowed(
        self,
        domain: str,
        request: ResearchRequest,
    ) -> bool:
        included = request.included_domains
        excluded = request.excluded_domains
        return (
            (not included or any(self._domain_matches(domain, item, request.options.include_subdomains) for item in included))
            and not any(self._domain_matches(domain, item, request.options.include_subdomains) for item in excluded)
        )

    @staticmethod
    def _domain_matches(domain: str, rule: str, include_subdomains: bool) -> bool:
        hostname = urlparse(
            rule if "://" in rule else f"//{rule}"
        ).hostname
        normalized = (hostname or rule).lower().removeprefix("www.")
        return domain == normalized or (
            include_subdomains and domain.endswith(f".{normalized}")
        )

    @staticmethod
    def _result_percentage(
        query_index: int,
        result_index: int,
        result_count: int,
        total_queries: int,
    ) -> float:
        completed_query_fraction = query_index - 1
        result_fraction = result_index / max(result_count, 1)
        return min(
            95.0,
            75.0 + ((completed_query_fraction + result_fraction) / total_queries) * 20.0,
        )

    @staticmethod
    def _apply_crawl_data(prospect: Prospect, crawl_data: dict[str, Any]) -> Prospect:
        values = {
            key: crawl_data[key]
            for key in (
                "email",
                "phone",
                "facebook",
                "instagram",
                "linkedin",
                "twitter",
                "youtube",
            )
            if crawl_data.get(key)
        }
        for key in ("about_page", "contact_page"):
            if crawl_data.get(key):
                values[key] = urljoin(str(prospect.url), str(crawl_data[key]))
        return Prospect.model_validate({**prospect.model_dump(), **values})

    @staticmethod
    def _apply_ai_analysis(prospect: Prospect, analysis: dict[str, Any]) -> Prospect:
        fields = {
            key: analysis[key]
            for key in (
                "ai_score",
                "guest_post_probability",
                "priority",
                "category",
            )
            if analysis.get(key) is not None
        }
        if analysis.get("summary") is not None:
            fields["ai_summary"] = analysis["summary"]
        return Prospect.model_validate({**prospect.model_dump(), **fields})

    async def _checkpoint(self, session_id: UUID) -> None:
        control = self._controls[session_id]
        if control.cancelled:
            raise _ResearchCancelled()
        await control.pause_gate.wait()
        if control.cancelled:
            raise _ResearchCancelled()

    def _initialize_session(self, request: ResearchRequest) -> ResearchSession:
        now = datetime.now(UTC)
        return ResearchSession(
            session_id=request.request_id,
            request=request,
            progress=ResearchProgress(
                session_id=request.request_id,
                phase=ResearchPhase.INITIALIZING,
                message="Initializing research session...",
                started_at=now,
                updated_at=now,
            ),
            statistics=ResearchStatistics(),
        )

    def _update_progress(
        self,
        session_id: UUID,
        *,
        phase: ResearchPhase,
        percentage: float,
        message: str,
        processed: int | None = None,
        total: int | None = None,
        current_query: str | None = None,
        current_url: str | None = None,
    ) -> ResearchSession:
        session = self._get_session(session_id)
        previous = session.progress
        if previous is None:
            raise ResearchError("Research session progress was not initialized.")
        progress = ResearchProgress(
            session_id=session_id,
            phase=phase,
            percentage=max(0.0, min(100.0, percentage)),
            processed=previous.processed if processed is None else processed,
            total=previous.total if total is None else total,
            current_query=current_query,
            current_url=current_url,
            message=message,
            started_at=previous.started_at,
            updated_at=datetime.now(UTC),
        )
        return self._store(session.update_progress(progress))

    def _update_statistics(self, session_id: UUID, **values: Any) -> ResearchSession:
        session = self._get_session(session_id)
        statistics = session.statistics.model_copy(update=values)
        return self._store(session.update_statistics(statistics))

    def _increment(self, session_id: UUID, field_name: str) -> None:
        statistics = self._get_session(session_id).statistics
        self._update_statistics(
            session_id,
            **{field_name: getattr(statistics, field_name) + 1},
        )

    def _record_ai_score(self, session_id: UUID, score: float | None) -> None:
        statistics = self._get_session(session_id).statistics
        processed = statistics.ai_processed + 1
        average = statistics.average_ai_score
        if score is not None:
            average = (
                (statistics.average_ai_score * statistics.ai_processed) + score
            ) / processed
        self._update_statistics(
            session_id,
            ai_processed=processed,
            average_ai_score=round(average, 2),
        )

    def _add_warning(self, session_id: UUID, warning: str) -> None:
        self._store(self._get_session(session_id).add_warning(warning))

    def _handle_item_failure(
        self,
        session_id: UUID,
        warning: str,
        **context: str,
    ) -> None:
        self._add_warning(session_id, warning)
        self._logger.warning(
            "Research item failed.",
            extra={"session_id": str(session_id), **context},
        )

    def _finalize_session(self, session: ResearchSession) -> ResearchSession:
        elapsed = max(0.0, (datetime.now(UTC) - session.started_at).total_seconds())
        statistics = session.statistics.model_copy(
            update={"elapsed_seconds": elapsed}
        )
        return self._store(session.update_statistics(statistics))

    def _build_response(self, session: ResearchSession) -> ResearchResponse:
        return ResearchResponse(
            success=session.status == ResearchStatus.COMPLETED,
            session_id=session.session_id,
            progress=session.progress,
            statistics=session.statistics,
            results=session.prospects,
            warnings=session.warnings,
            errors=session.errors,
            message=self._build_status_message(session),
        )

    @staticmethod
    def _build_status_message(session: ResearchSession) -> str:
        messages = {
            ResearchStatus.PENDING: "Research is pending.",
            ResearchStatus.RUNNING: "Research is currently running.",
            ResearchStatus.PAUSED: "Research has been paused.",
            ResearchStatus.CANCELLED: "Research was cancelled.",
            ResearchStatus.FAILED: "Research failed.",
        }
        if session.status == ResearchStatus.COMPLETED:
            return f"Research completed successfully. {len(session.prospects)} prospects discovered."
        return messages[session.status]

    def _store(self, session: ResearchSession) -> ResearchSession:
        self._sessions[session.session_id] = session
        return session

    def _get_session(self, session_id: UUID) -> ResearchSession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise ResearchError(f"Research session '{session_id}' was not found.") from exc

    def _get_session_from_text(self, session_id: str) -> ResearchSession:
        try:
            return self._get_session(UUID(session_id))
        except ValueError as exc:
            raise ResearchError("Invalid research session ID.") from exc

    def _log_session_summary(self, session: ResearchSession) -> None:
        self._logger.info(
            "Research session finished.",
            extra={
                "session_id": str(session.session_id),
                "status": session.status.value,
                "prospects_saved": session.statistics.prospects_saved,
                "queries_completed": session.statistics.queries_completed,
                "elapsed_seconds": session.statistics.elapsed_seconds,
            },
        )
