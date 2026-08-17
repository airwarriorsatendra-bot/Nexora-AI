"""Manual crawler smoke script; safe to import during test discovery."""


def main() -> None:
    from tools.website_crawler import WebsiteCrawler

    print(WebsiteCrawler().crawl("https://www.fibre2fashion.com"))


if __name__ == "__main__":
    main()
