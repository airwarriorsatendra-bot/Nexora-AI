import asyncio
from crawl4ai import AsyncWebCrawler


async def crawl_page(url: str):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)

        return {
            "url": url,
            "markdown": result.markdown,
            "title": result.metadata.get("title", "")
        }


def crawl(url: str):
    return asyncio.run(crawl_page(url))