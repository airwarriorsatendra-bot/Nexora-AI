"""
Manager Agent
-------------
Coordinates the complete backlink discovery pipeline.
"""

from agents.research_agent import ResearchAgent
from agents.website_analyzer import WebsiteAnalyzer
from agents.scoring_agent import ScoringAgent
from dashboard.database import prospects
from dashboard.models import Prospect


class ManagerAgent:

    def __init__(self):

        self.research = ResearchAgent()
        self.analyzer = WebsiteAnalyzer()
        self.scorer = ScoringAgent()

    def run(
        self,
        keyword,
        limit=20,
    ):
        """
        Run complete workflow.

        Returns
        -------
        list[dict]
            Results ready for the Streamlit UI.
        """

        websites = self.research.search(
            keyword,
            limit,
        )

        results = []

        for site in websites:

            analysis = self.analyzer.analyse(
                title=site.title,
                url=site.url,
                category=site.category,
                description=site.description,
            )

            score = self.scorer.calculate_score(
                domain_authority=site.domain_authority,
                accepts_guest_posts=analysis.get(
                    "accepts_guest_posts",
                    False,
                ),
                category=analysis.get(
                    "niche",
                    site.category,
                ),
                backlink_value=analysis.get(
                    "backlink_value",
                    "Unknown",
                ),
                contact_email=site.contact_email,
            )

            priority = self.scorer.priority(score)

            # --------------------------------------------------
            # Persist Website
            # --------------------------------------------------

            site.priority_score = score
            site.priority = priority

            try:
                prospects.add(
                    Prospect(
                        title=site.title,
                        url=site.url,
                        category=site.category,
                        description=site.description,
                        emails=[site.contact_email] if site.contact_email else [],
                        phone_numbers=[site.phone_number] if site.phone_number else [],
                        contact_page=site.contact_page,
                        about_page=site.about_page,
                        write_for_us=site.write_for_us,
                        social_links=site.social_links or [],
                        niche=analysis.get("niche", site.category),
                        summary=analysis.get("summary", ""),
                        accepts_guest_posts=analysis.get("accepts_guest_posts", False),
                        backlink_value=analysis.get("backlink_value", "Unknown"),
                        reason=analysis.get("reason", ""),
                        priority_score=score,
                        priority=priority,
                    )
                )
            except Exception as error:
                print(f"Database Error: {error}")

            # --------------------------------------------------
            # UI Result
            # --------------------------------------------------

            results.append(
                {
                    "title": site.title,
                    "url": site.url,
                    "category": site.category,
                    "description": site.description,
                    "domain_authority": site.domain_authority,
                    "contact_email": site.contact_email,
                    "contact_page": site.contact_page,
                    "about_page": site.about_page,
                    "write_for_us": site.write_for_us,
                    "phone_number": site.phone_number,
                    "social_links": site.social_links,
                    "analysis": analysis,
                    "priority_score": score,
                    "priority": priority,
                }
            )

        return results
