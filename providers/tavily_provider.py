"""
Tavily Provider
---------------
AI-powered web search provider.
Compatible with ResearchAgent.
"""

import os

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()


class TavilyProvider:
    """Wrapper for the Tavily Search API."""

    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")

        if not api_key:
            raise ValueError("TAVILY_API_KEY not found in .env")

        self.client = TavilyClient(api_key=api_key)

    def search(self, query: str, num: int = 10):
        """
        Search Tavily.

        Returns a dictionary compatible with Serper:
        {
            "organic": [
                {
                    "title": "...",
                    "link": "...",
                    "snippet": "..."
                }
            ]
        }
        """

        response = self.client.search(
            query=query,
            search_depth="advanced",
            max_results=num,
        )

        organic = []

        for item in response.get("results", []):
            organic.append(
                {
                    "title": item.get("title", ""),
                    "link": item.get("url", ""),
                    "snippet": item.get("content", ""),
                }
            )

        return {
            "organic": organic
        }