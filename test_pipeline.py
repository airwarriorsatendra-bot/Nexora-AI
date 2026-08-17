"""Manual research pipeline smoke script; safe to import during test discovery."""


def main() -> None:
    from agents.research_agent import ResearchAgent

    results = ResearchAgent().search("fashion blogs India guest post", limit=3)
    for site in results:
        print("=" * 80)
        print("Title :", site.title)
        print("URL :", site.url)
        print("Email :", site.contact_email)
        print("Phone :", site.phone_number)
        print("Contact :", site.contact_page)
        print("About :", site.about_page)
        print("Write For Us :", site.write_for_us)
        print("Social :", site.social_links)


if __name__ == "__main__":
    main()
