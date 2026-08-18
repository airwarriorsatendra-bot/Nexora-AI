"""Streamlit-safe adapter for explicit site crawls and persisted reads."""
from __future__ import annotations

import os
from dotenv import load_dotenv

from src.site_crawl.composition import SiteCrawlComposition, SiteCrawlSettings
from src.site_crawl.domain import SiteCrawlRequest


class SiteCrawlDashboardWorkflow:
    def __init__(self, factory=None): self._factory = factory or self._build

    @staticmethod
    def _build():
        load_dotenv(); return SiteCrawlComposition(SiteCrawlSettings.from_environment(dict(os.environ))).build()

    async def run(self, start_url: str, max_pages: int, max_depth: int, concurrency: int):
        app = self._factory()
        try: return await app.service.run(SiteCrawlRequest(start_url=start_url, max_pages=max_pages, max_depth=max_depth, max_concurrency=concurrency))
        finally: await app.aclose()

    async def latest(self):
        app = self._factory()
        try: return await app.service.latest()
        finally: await app.aclose()

    async def history(self):
        app = self._factory()
        try: return await app.service.history()
        finally: await app.aclose()

    async def comparison(self, current):
        history = await self.history(); compatible = [item for item in history if item.request.start_url == current.request.start_url and item.crawl_id != current.crawl_id]
        return app_compare(current, compatible[-1] if compatible else None)


def app_compare(current, previous):
    from src.site_crawl.service import SiteCrawlService
    return SiteCrawlService.compare(current, previous)

