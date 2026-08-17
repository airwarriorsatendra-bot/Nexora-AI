"""Manual manager-agent smoke script; safe to import during test discovery."""


def main() -> None:
    from agents.manager_agent import ManagerAgent

    manager = ManagerAgent()
    results = manager.run("fashion blogs India guest post", limit=3)
    for site in results:
        print(site)


if __name__ == "__main__":
    main()
