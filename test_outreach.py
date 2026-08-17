"""Manual outreach-agent smoke script; safe to import during test discovery."""


def main() -> None:
    from agents.outreach_agent import OutreachAgent
    from tools.outreach_writer import save_outreach

    website = "Esty Lingerie"
    category = "Lingerie"
    url = "https://estylingerie.com"
    email = OutreachAgent().generate_email(website=website, category=category)
    print(email)
    save_outreach(url, email)


if __name__ == "__main__":
    main()
