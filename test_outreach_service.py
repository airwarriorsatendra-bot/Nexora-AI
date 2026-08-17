"""Manual outreach-service smoke script; safe to import during test discovery."""


def main() -> None:
    from tools.outreach_service import generate_outreach

    print(
        generate_outreach(
            website="Fibre2Fashion",
            category="Fashion",
            contact_email="editor@example.com",
        )
    )


if __name__ == "__main__":
    main()
