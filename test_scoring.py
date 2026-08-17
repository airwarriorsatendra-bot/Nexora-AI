"""Manual scoring smoke script; safe to import during test discovery."""


def main() -> None:
    from agents.scoring_agent import ScoringAgent

    agent = ScoringAgent()
    score = agent.calculate_score(
        domain_authority=72,
        accepts_guest_posts=True,
        category="Fashion Blog",
        backlink_value="High",
        contact_email="editor@example.com",
    )
    print("Score:", score)
    print("Priority:", agent.priority(score))


if __name__ == "__main__":
    main()
