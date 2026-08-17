"""Manual AI analysis smoke script; safe to import during test discovery."""


def main() -> None:
    from agents.ai_analyzer import analyze
    from tools.crawler import crawl

    page = crawl("https://theformalclub.in")
    print(analyze(page["markdown"]))


if __name__ == "__main__":
    main()
