"""
Serper Provider
---------------
Google Search API wrapper.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")


class SerperProvider:
    """Wrapper for the Serper Google Search API."""

    BASE_URL = "https://google.serper.dev/search"

    def search(self, query: str, num: int = 10):
        """
        Search Google using the Serper API.
        """

        if not SERPER_API_KEY:
            raise ValueError("SERPER_API_KEY not found in .env file.")

        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json",
        }

        payload = {
            "q": query,
            "num": num,
        }

        response = requests.post(
            self.BASE_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )

        print("Status Code:", response.status_code)
        print("Response:", response.text)

        response.raise_for_status()

        return response.json()