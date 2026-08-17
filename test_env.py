"""Manual environment inspection script; safe to import during test discovery."""


def main() -> None:
    from dotenv import dotenv_values

    config = dotenv_values(".env")
    print("Configured keys:", ", ".join(sorted(config)))


if __name__ == "__main__":
    main()
