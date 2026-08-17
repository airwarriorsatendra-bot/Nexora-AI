"""
Website Analyzer Agent
----------------------
Uses AI to analyse a website and determine whether it is a good
backlink opportunity for Veloura Intimate.
"""

import json
from providers.groq_provider import chat


class WebsiteAnalyzer:

    def __init__(self):
        self.system_prompt = """
You are an SEO expert.

Analyse the website information and return ONLY valid JSON.

JSON format:

{
    "summary":"",
    "niche":"",
    "accepts_guest_posts":true,
    "backlink_value":"High",
    "reason":""
}

Do not return markdown.
Do not explain anything.
Return only JSON.
"""

    def analyse(
        self,
        title: str,
        url: str,
        category: str,
        description: str = "",
    ):

        prompt = f"""
Website Title:
{title}

Website URL:
{url}

Category:
{category}

Description:
{description}

Analyse this website for backlink outreach.
"""

        try:

            response = chat(
                system_prompt=self.system_prompt,
                user_prompt=prompt,
                temperature=0.2,
            )

            return json.loads(response)

        except Exception:

            return {
                "summary": "",
                "niche": category,
                "accepts_guest_posts": False,
                "backlink_value": "Unknown",
                "reason": "AI analysis failed.",
            }