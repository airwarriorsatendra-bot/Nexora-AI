"""Site Crawl API contracts."""

from pydantic import BaseModel, ConfigDict

from src.site_crawl.domain import CrawlComparison, SiteCrawl


class SiteCrawlHistory(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[SiteCrawl]
    latest: SiteCrawl | None


class SiteCrawlDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    crawl: SiteCrawl
    comparison: CrawlComparison
