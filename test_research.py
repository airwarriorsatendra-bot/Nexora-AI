"""Manual research-agent smoke script; safe to import during test discovery."""


def main() -> None:
    from agents.research_agent import ResearchAgent

    results = ResearchAgent().search(
        keyword="fashion blogs India guest post",
        limit=5,
    )
    print(f"\nFound {len(results)} websites\n")
    for index, site in enumerate(results, start=1):
        print("=" * 70)
        print(f"{index}. {site.title}")
        print(f"URL        : {site.url}")
        print(f"Category   : {site.category}")
        print(f"Description: {site.description}")


if __name__ == "__main__":
    main()
