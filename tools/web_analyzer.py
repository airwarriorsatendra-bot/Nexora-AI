import re
import requests
from bs4 import BeautifulSoup


EMAIL_PATTERN = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"


def analyze_website(url: str):
    result = {
        "url": url,
        "guest_post": False,
        "contact_page": "",
        "emails": [],
        "status": "ok"
    }

    try:
        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(" ", strip=True).lower()

        # Detect guest-post indicators
        keywords = [
            "write for us",
            "guest post",
            "submit article",
            "contribute"
        ]

        result["guest_post"] = any(k in text for k in keywords)

        # Find contact page
        for link in soup.find_all("a", href=True):
            href = link["href"]
            label = link.get_text(" ", strip=True).lower()

            if "contact" in label or "contact" in href.lower():
                result["contact_page"] = href
                break

        # Find email addresses
        result["emails"] = list(
            set(re.findall(EMAIL_PATTERN, response.text))
        )

    except Exception as e:
        result["status"] = str(e)

    return result