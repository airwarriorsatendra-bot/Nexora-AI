import os
import json

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Create OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def analyze(markdown: str):
    """
    Analyse a website and return structured SEO information.
    """

    # Limit content to reduce token usage
    content = markdown[:5000]

    prompt = f"""
You are an expert SEO strategist and backlink outreach specialist.

Analyse the following website.

Website Content:
----------------
{content}

Determine:

1. Website category
2. Whether the site accepts guest posts
3. Relevance score (0-100)
4. Priority (High / Medium / Low)
5. Short reason

Return ONLY valid JSON.

Example:

{{
    "category": "Fashion",
    "accepts_guest_posts": true,
    "relevance_score": 92,
    "priority": "High",
    "reason": "Highly relevant fashion blog that accepts guest posts."
}}
"""

    try:

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert SEO strategist. "
                        "Always return ONLY valid JSON."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=300
        )

        result = response.choices[0].message.content

        return json.loads(result)

    except Exception as e:

        return {
            "category": "Unknown",
            "accepts_guest_posts": False,
            "relevance_score": 0,
            "priority": "Low",
            "reason": str(e)
        }


# Test directly
if __name__ == "__main__":

    sample = """
    Welcome to our fashion magazine.
    We accept guest posts from fashion experts.
    Contact us for collaborations.
    """

    print(json.dumps(analyze(sample), indent=4))