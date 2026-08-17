"""Manual provider smoke script; safe to import during test discovery."""


def main() -> None:
    from providers.groq_provider import chat

    print(chat("You are helpful.", "Say Hello"))


if __name__ == "__main__":
    main()
