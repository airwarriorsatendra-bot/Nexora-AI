"""
Website Crawler
---------------
High-performance crawler for backlink prospect enrichment.
"""

import re
import requests

from bs4 import BeautifulSoup

from urllib.parse import (
    urljoin,
    urlparse,
)

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class WebsiteCrawler:

    def __init__(self):

        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }

        retry = Retry(
            total=1,
            connect=1,
            read=1,
            backoff_factor=0.3,
            status_forcelist=[
                429,
                500,
                502,
                503,
                504,
            ],
            allowed_methods=["GET"],
        )

        self.session = requests.Session()

        adapter = HTTPAdapter(
            max_retries=retry,
            pool_connections=50,
            pool_maxsize=50,
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    # ----------------------------------------------------
    # Download Page
    # ----------------------------------------------------

    def fetch(self, url):

        if not url:
            return ""

        try:

            response = self.session.get(
                url,
                headers=self.headers,
                timeout=5,
                allow_redirects=True,
            )

            if response.status_code != 200:
                return ""

            content_type = response.headers.get(
                "Content-Type",
                "",
            ).lower()

            if "text/html" not in content_type:
                return ""

            return response.text

        except Exception:
            return ""

    # ----------------------------------------------------
    # HTML Parser
    # ----------------------------------------------------

    def soup(self, html):

        if not html:
            return None

        return BeautifulSoup(
            html,
            "lxml",
        )

    # ----------------------------------------------------
    # Domain
    # ----------------------------------------------------

    def domain(self, url):
        return urlparse(url).netloc.lower()

    # ----------------------------------------------------
    # Normalize URL
    # ----------------------------------------------------

    def normalize(
        self,
        base_url,
        href,
    ):

        if not href:
            return ""

        href = href.strip()

        if href.startswith("#"):
            return ""

        if href.startswith("mailto:"):
            return ""

        if href.startswith("javascript:"):
            return ""

        return urljoin(
            base_url,
            href,
        )

    # ----------------------------------------------------
    # Title
    # ----------------------------------------------------

    def extract_title(
        self,
        soup,
    ):

        if soup and soup.title:
            return soup.title.text.strip()

        return ""

    # ----------------------------------------------------
    # Meta Description
    # ----------------------------------------------------

    def extract_description(
        self,
        soup,
    ):

        if soup is None:
            return ""

        meta = soup.find(
            "meta",
            attrs={
                "name": "description"
            },
        )

        if meta:
            return meta.get(
                "content",
                "",
            ).strip()

        return ""
    # ----------------------------------------------------
    # Extract Emails
    # ----------------------------------------------------

    def extract_emails(
        self,
        html,
        soup,
    ):

        emails = set()

        if html:

            pattern = re.compile(
                r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
            )

            emails.update(
                email.lower()
                for email in pattern.findall(html)
            )

        if soup:

            for link in soup.select("a[href^='mailto:']"):

                href = link.get("href", "")

                email = (
                    href.replace("mailto:", "")
                    .split("?")[0]
                    .strip()
                    .lower()
                )

                if email:
                    emails.add(email)

        blocked = {
            "example@example.com",
            "test@test.com",
            "your@email.com",
            "admin@example.com",
        }

        return sorted(
            e for e in emails
            if e not in blocked
        )

    # ----------------------------------------------------
    # Extract Phone Numbers
    # ----------------------------------------------------

    def extract_phone_numbers(
        self,
        html,
    ):

        if not html:
            return []

        phones = set()

        pattern = re.compile(
            r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,5}\)?[\s-]?)?\d{3,5}[\s-]?\d{3,5}"
        )

        for phone in pattern.findall(html):

            digits = re.sub(r"\D", "", phone)

            if 10 <= len(digits) <= 15:
                phones.add(phone.strip())

        return sorted(phones)

    # ----------------------------------------------------
    # Find Important Pages
    # ----------------------------------------------------

    def find_pages(
        self,
        base_url,
        soup,
    ):

        pages = {
            "contact_page": "",
            "about_page": "",
            "write_for_us": "",
        }

        if soup is None:
            return pages

        for link in soup.find_all("a", href=True):

            href = self.normalize(
                base_url,
                link["href"],
            )

            if not href:
                continue

            lower = href.lower()

            if (
                not pages["contact_page"]
                and "contact" in lower
            ):
                pages["contact_page"] = href

            elif (
                not pages["about_page"]
                and "about" in lower
            ):
                pages["about_page"] = href

            elif (
                not pages["write_for_us"]
                and any(
                    key in lower
                    for key in (
                        "write-for-us",
                        "write_for_us",
                        "guest-post",
                        "guest-posting",
                        "submit-article",
                        "submit-post",
                        "submit-your-post",
                        "contribute",
                    )
                )
            ):
                pages["write_for_us"] = href

            if (
                pages["contact_page"]
                and pages["about_page"]
                and pages["write_for_us"]
            ):
                break

        return pages

    # ----------------------------------------------------
    # Extract Social Links
    # ----------------------------------------------------

    def extract_social_links(
        self,
        soup,
    ):

        if soup is None:
            return []

        socials = set()

        allowed = (
            "facebook.com",
            "instagram.com",
            "linkedin.com",
            "youtube.com",
            "twitter.com",
            "x.com",
            "pinterest.com",
        )

        for link in soup.find_all("a", href=True):

            href = link.get("href", "").strip()

            if any(site in href for site in allowed):
                socials.add(href)

        return sorted(socials)
    # ----------------------------------------------------
    # Crawl Website
    # ----------------------------------------------------

    def crawl(self, url):
        """
        High-performance website crawler.
        """

        result = {
            "title": "",
            "description": "",
            "emails": [],
            "phone_numbers": [],
            "contact_page": "",
            "about_page": "",
            "write_for_us": "",
            "social_links": [],
        }

        html = self.fetch(url)

        if not html:
            return result

        soup = self.soup(html)

        result["title"] = self.extract_title(soup)
        result["description"] = self.extract_description(soup)

        emails = set(
            self.extract_emails(
                html,
                soup,
            )
        )

        phones = set(
            self.extract_phone_numbers(
                html,
            )
        )

        socials = set(
            self.extract_social_links(
                soup,
            )
        )

        pages = self.find_pages(
            url,
            soup,
        )

        result["contact_page"] = pages["contact_page"]
        result["about_page"] = pages["about_page"]
        result["write_for_us"] = pages["write_for_us"]

        # --------------------------------------------------
        # FAST EXIT
        # --------------------------------------------------

        if emails:

            result["emails"] = sorted(emails)
            result["phone_numbers"] = sorted(phones)
            result["social_links"] = sorted(socials)

            return result

        # --------------------------------------------------
        # Crawl Contact Page Only
        # --------------------------------------------------

        if pages["contact_page"]:

            page_html = self.fetch(
                pages["contact_page"]
            )

            if page_html:

                page_soup = self.soup(page_html)

                emails.update(
                    self.extract_emails(
                        page_html,
                        page_soup,
                    )
                )

                phones.update(
                    self.extract_phone_numbers(
                        page_html,
                    )
                )

                socials.update(
                    self.extract_social_links(
                        page_soup,
                    )
                )

        # --------------------------------------------------
        # FAST EXIT AGAIN
        # --------------------------------------------------

        if emails:

            result["emails"] = sorted(emails)
            result["phone_numbers"] = sorted(phones)
            result["social_links"] = sorted(socials)

            return result

        # --------------------------------------------------
        # Last Chance
        # --------------------------------------------------

        for page in (
            pages["about_page"],
            pages["write_for_us"],
        ):

            if not page:
                continue

            page_html = self.fetch(page)

            if not page_html:
                continue

            page_soup = self.soup(page_html)

            emails.update(
                self.extract_emails(
                    page_html,
                    page_soup,
                )
            )

            phones.update(
                self.extract_phone_numbers(
                    page_html,
                )
            )

            socials.update(
                self.extract_social_links(
                    page_soup,
                )
            )

            if emails:
                break

        result["emails"] = sorted(emails)
        result["phone_numbers"] = sorted(phones)
        result["social_links"] = sorted(socials)

        return result