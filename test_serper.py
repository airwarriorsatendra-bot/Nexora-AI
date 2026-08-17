"""Manual Serper smoke script; safe to import during test discovery."""


def main() -> None:
    from providers.serper_provider import SerperProvider

    print(SerperProvider().search("fashion blogs India", num=5))


if __name__ == "__main__":
    main()
