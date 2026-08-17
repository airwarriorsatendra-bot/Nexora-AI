"""
Scoring Agent
-------------
Calculates a priority score for backlink opportunities.
"""


class ScoringAgent:

    def __init__(self):
        pass

    def calculate_score(
        self,
        domain_authority=0,
        accepts_guest_posts=False,
        category="",
        backlink_value="Unknown",
        contact_email="",
    ):
        """
        Returns a priority score between 0 and 100.
        """

        score = 0

        # ----------------------------
        # Domain Authority
        # ----------------------------

        if domain_authority >= 80:
            score += 40

        elif domain_authority >= 60:
            score += 30

        elif domain_authority >= 40:
            score += 20

        elif domain_authority >= 20:
            score += 10

        # ----------------------------
        # Guest Post
        # ----------------------------

        if accepts_guest_posts:
            score += 20

        # ----------------------------
        # Category Relevance
        # ----------------------------

        category = category.lower()

        relevant_categories = [
            "fashion",
            "lingerie",
            "beauty",
            "women",
            "lifestyle",
            "shopping",
            "clothing",
            "apparel",
            "luxury",
        ]

        if any(word in category for word in relevant_categories):
            score += 20

        # ----------------------------
        # AI Backlink Value
        # ----------------------------

        backlink_value = backlink_value.lower()

        if backlink_value == "high":
            score += 15

        elif backlink_value == "medium":
            score += 10

        elif backlink_value == "low":
            score += 5

        # ----------------------------
        # Contact Email
        # ----------------------------

        if contact_email.strip():
            score += 5

        return min(score, 100)

    def priority(self, score):
        """
        Convert numeric score into priority label.
        """

        if score >= 80:
            return "High"

        if score >= 60:
            return "Medium"

        if score >= 40:
            return "Low"

        return "Ignore"