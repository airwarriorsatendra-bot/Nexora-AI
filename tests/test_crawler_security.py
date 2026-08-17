"""Offline security tests for research crawler destination validation."""

from __future__ import annotations

import unittest

from src.core.exceptions import CrawlError
from src.research.services.crawler_service import CrawlerService


class CrawlerSecurityTests(unittest.TestCase):
    def test_rejects_non_public_and_non_http_destinations(self) -> None:
        for url in (
            "http://localhost/", "http://127.0.0.1/", "http://0.0.0.0/",
            "http://[::1]/", "http://10.0.0.1/", "http://172.16.0.1/",
            "http://192.168.1.1/", "http://169.254.1.1/", "file:///etc/passwd",
            "ftp://example.com/file", "javascript:alert(1)",
        ):
            with self.subTest(url=url), self.assertRaises(CrawlError):
                CrawlerService._validate_url(url)

    def test_accepts_structurally_valid_public_http_url(self) -> None:
        self.assertEqual(CrawlerService._validate_url("https://example.com/path"), "https://example.com/path")
