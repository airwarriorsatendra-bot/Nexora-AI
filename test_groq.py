"""Manual Groq smoke script; safe to import during test discovery."""


def main() -> None:
    from providers.groq_provider import chat

    sample = """
Welcome to Fashion Weekly.

We accept guest posts.

Contact us for collaboration.
"""
    print(chat("Analyze this website content.", sample))


if __name__ == "__main__":
    main()
