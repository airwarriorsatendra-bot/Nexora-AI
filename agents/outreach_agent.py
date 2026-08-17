from providers.groq_provider import client


class OutreachAgent:

    def generate_email(self, website, category):

        prompt = f"""
You are an expert SEO outreach specialist.

Write a professional guest post outreach email.

Website:
{website}

Category:
{category}

Brand:
Veloura Intimate

Requirements:

- Friendly and professional
- Mention the website naturally
- Maximum 180 words
- Explain why Veloura Intimate is a good fit
- Ask if they accept guest posts
- End with a professional signature
"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert SEO outreach specialist."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.5
        )

        return response.choices[0].message.content