"""Manual outreach storage smoke script; safe to import during test discovery."""


def main() -> None:
    from tools.outreach_writer import clear_outreach, get_outreach, save_outreach

    url = "https://example.com"
    print("Saving...")
    save_outreach(url, "Hello from Veloura AI")
    print(get_outreach(url))
    print("Clearing...")
    clear_outreach(url)
    print(get_outreach(url))


if __name__ == "__main__":
    main()
