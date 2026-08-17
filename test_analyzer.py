"""Manual website-analysis smoke script; safe to import during test discovery."""


def main() -> None:
    from agents.website_analyzer import WebsiteAnalyzer

    result = WebsiteAnalyzer().analyse(
        title="Fibre2Fashion",
        url="https://www.fibre2fashion.com",
        category="Fashion",
        description="Fashion news and textile industry portal",
    )
    print(result)


if __name__ == "__main__":
    main()
