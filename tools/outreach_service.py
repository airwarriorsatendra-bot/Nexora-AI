"""
Outreach Service
----------------
Generates AI-powered outreach emails using the Groq provider.
"""

from providers.groq_provider import chat


SYSTEM_PROMPT = """
You are an expert SEO outreach specialist.

Your task is to write professional guest post outreach emails.

Rules:
- Professional and friendly tone.
- Mention the website naturally.
- Mention Veloura Intimate.
- Maximum 180 words.
- Never sound spammy.
- Finish with a professional closing.
"""


def build_prompt(
    website: str,
    category: str,
    contact_email: str = "",
):
    """
    Build the user prompt.
    """

    return f"""
Website:
{website}

Category:
{category}

Contact Email:
{contact_email}

Brand:
Veloura Intimate

Write a personalised outreach email requesting a guest posting opportunity.

Return only the email.
"""


def generate_outreach(
    website: str,
    category: str,
    contact_email: str = "",
):
    """
    Generate outreach email.
    """

    prompt = build_prompt(
        website=website,
        category=category,
        contact_email=contact_email,
    )

    return chat(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt,
        temperature=0.4,
    )