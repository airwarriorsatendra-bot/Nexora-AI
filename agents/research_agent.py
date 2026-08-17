"""
Research Agent
--------------
Discovers backlink opportunities using Tavily Search or directly analyses a
website URL using the WebsiteCrawler.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List
from urllib.parse import urlparse

from providers.tavily_provider import TavilyProvider
from tools.website_crawler import WebsiteCrawler


@dataclass
class Website:
    title: str
    url: str
    category: str
    description: str = ""
    domain_authority: int = 0
    contact_email: str = ""
    contact_page: str = ""
    about_page: str = ""
    write_for_us: str = ""
    phone_number: str = ""
    social_links: list = None


class ResearchAgent:
    def __init__(self):
        self.provider = TavilyProvider()
        self.crawler = WebsiteCrawler()
        self.blocked_domains = [
            "quora.com",
            "reddit.com",
            "medium.com",
            "linkedin.com",
            "facebook.com",
            "instagram.com",
            "youtube.com",
            "fiverr.com",
        ]

    def is_url(self, value: str) -> bool:
        if not value:
            return False
        value = value.strip()
        if not (value.startswith("http://") or value.startswith("https://")):
            return False
        return bool(urlparse(value).netloc)

    def is_blocked(self, url: str) -> bool:
        url = url.lower()
        return any(domain in url for domain in self.blocked_domains)

    def analyze_url(self, url: str) -> Website | None:
        if self.is_blocked(url):
            return None

        print(f"Crawling Website: {url}")
        try:
            crawl = self.crawler.crawl(url)
            emails = crawl.get("emails", [])
            phones = crawl.get("phone_numbers", [])
            category = urlparse(url).netloc.replace("www.", "")
            return Website(
                title=crawl.get("title", category),
                url=url,
                category=category,
                description=crawl.get("description", ""),
                domain_authority=0,
                contact_email=emails[0] if emails else "",
                contact_page=crawl.get("contact_page", ""),
                about_page=crawl.get("about_page", ""),
                write_for_us=crawl.get("write_for_us", ""),
                phone_number=phones[0] if phones else "",
                social_links=crawl.get("social_links", []),
            )
        except Exception as error:
            print(error)
            return None

    def process_result(self, item, keyword):
        url = item.get("link", "")
        if not url or self.is_blocked(url):
            return None

        print(f"Crawling: {url}")
        try:
            crawl = self.crawler.crawl(url)
            emails = crawl.get("emails", [])
            phones = crawl.get("phone_numbers", [])
            return Website(
                title=crawl.get("title") or item.get("title", ""),
                url=url,
                category=keyword,
                description=crawl.get("description") or item.get("snippet", ""),
                domain_authority=0,
                contact_email=emails[0] if emails else "",
                contact_page=crawl.get("contact_page", ""),
                about_page=crawl.get("about_page", ""),
                write_for_us=crawl.get("write_for_us", ""),
                phone_number=phones[0] if phones else "",
                social_links=crawl.get("social_links", []),
            )
        except Exception as error:
            print(error)
            return None

    def search_keyword(self, keyword: str, limit: int = 10) -> List[Website]:
        search_query = (
            f'{keyword} '
            '"write for us" OR '
            '"guest post" OR '
            '"become a contributor" OR '
            '"submit article"'
        )
        response = self.provider.search(query=search_query, num=limit)
        organic = response.get("organic", [])
        websites = []

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(self.process_result, item, keyword)
                for item in organic
            ]
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        websites.append(result)
                except Exception as error:
                    print(error)
        return websites

    def search(self, keyword: str, limit: int = 10) -> List[Website]:
        """Search by keyword or analyse a direct website URL."""
        keyword = keyword.strip()
        if not keyword:
            return []
        if self.is_url(keyword):
            website = self.analyze_url(keyword)
            return [website] if website else []
        return self.search_keyword(keyword, limit)

    def search_multiple(
        self,
        keywords: List[str],
        limit_per_keyword: int = 10,
    ) -> List[Website]:
        all_results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(self.search, keyword, limit_per_keyword)
                for keyword in keywords
            ]
            for future in as_completed(futures):
                try:
                    all_results.extend(future.result())
                except Exception as error:
                    print(error)

        unique = {}
        for website in all_results:
            if website.url not in unique:
                unique[website.url] = website
        return list(unique.values())
