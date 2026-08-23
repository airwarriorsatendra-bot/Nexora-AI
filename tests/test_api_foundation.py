from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from api.config import APISettings
from api.main import create_app
from src.core.constants import APP_VERSION
from src.core.exceptions import ConfigurationError


class APISettingsTests(unittest.TestCase):
    def test_rejects_wildcard_cors_origin(self) -> None:
        with self.assertRaises(ConfigurationError):
            APISettings.from_environment({"NEXORA_ALLOWED_ORIGINS": "*"})


class APIFoundationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        settings = APISettings(
            allowed_origins=("http://localhost:3000",),
            database_path=Path(self.temporary_directory.name) / "api.db",
        )
        self.client = TestClient(create_app(settings))

    def tearDown(self) -> None:
        self.client.close()
        self.temporary_directory.cleanup()

    def test_health_is_side_effect_free(self) -> None:
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["version"], APP_VERSION)
        self.assertTrue(response.headers["x-request-id"])
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertIn("default-src 'none'", response.headers["content-security-policy"])

    def test_readiness_checks_sqlite(self) -> None:
        response = self.client.get("/api/v1/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")

    def test_version(self) -> None:
        response = self.client.get("/api/v1/version")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], APP_VERSION)

    def test_dashboard_uses_empty_persisted_state_without_external_calls(self) -> None:
        response = self.client.get("/api/v1/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [metric["value"] for metric in response.json()["metrics"]],
            [0, 0, 0, 0],
        )

    def test_seo_audit_list_is_paginated_and_offline(self) -> None:
        response = self.client.get("/api/v1/seo/audits?page=1&limit=10")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
        self.assertEqual(response.json()["pagination"]["limit"], 10)

    def test_seo_pagination_rejects_unsafe_limit(self) -> None:
        response = self.client.get("/api/v1/seo/audits?limit=1000")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_backlinks_snapshot_is_offline_and_data_honest(self) -> None:
        response = self.client.get("/api/v1/backlinks")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["backlinks"], [])
        self.assertEqual(response.json()["prospects"], [])

    def test_backlink_detail_resources_are_persisted_only(self) -> None:
        for path in ("profile", "authority", "prospects", "reclamation", "history"):
            with self.subTest(path=path):
                response = self.client.get(f"/api/v1/backlinks/{path}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), [])
        referring = self.client.get("/api/v1/backlinks/referring-domains?target_domain=example.com")
        self.assertEqual(referring.status_code, 200)
        self.assertEqual(referring.json(), [])

    def test_backlink_authority_preview_and_provider_gate(self) -> None:
        payload = {"targets": ["https://example.test/"], "scope": "url", "force": False}
        preview = self.client.post("/api/v1/backlinks/authority/preview", json=payload)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["preview"]["provider_calls"], 1)
        enrich = self.client.post("/api/v1/backlinks/authority/enrich", json=payload)
        self.assertEqual(enrich.status_code, 409)
        self.assertEqual(enrich.json()["error"]["code"], "PROVIDER_NOT_CONFIGURED")
        payload["scope"] = "invalid"
        self.assertEqual(self.client.post("/api/v1/backlinks/authority/preview", json=payload).status_code, 422)

    def test_provider_settings_expose_presence_only(self) -> None:
        isolated = TestClient(create_app(APISettings(
            allowed_origins=("http://localhost:3000",),
            database_path=Path(self.temporary_directory.name) / "settings.db",
            environment=(("GSC_REFRESH_TOKEN", "sentinel-refresh-token"), ("GSC_CLIENT_SECRET", "sentinel-client-secret"), ("GSC_CLIENT_ID", "sentinel-client-id")),
        )))
        response = isolated.get("/api/v1/settings/providers")
        isolated.close()
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["authentication"], "DEFERRED_TO_SAAS_FOUNDATION")
        serialized = response.text.lower()
        self.assertIn('"status":"configured"', serialized)
        self.assertNotIn("sentinel-refresh-token", serialized)
        self.assertNotIn("sentinel-client-secret", serialized)
        self.assertNotIn("refresh_token\":", serialized)
        self.assertNotIn("client_secret\":", serialized)

    def test_workspace_summaries_do_not_trigger_providers(self) -> None:
        for workspace in ("ai-visibility", "outreach", "local-seo", "analytics", "google-ads", "meta-ads"):
            with self.subTest(workspace=workspace):
                response = self.client.get(f"/api/v1/workspaces/{workspace}")
                self.assertEqual(response.status_code, 200)

    def test_unknown_route_uses_sanitized_error_contract(self) -> None:
        response = self.client.get("/api/v1/does-not-exist")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")
        self.assertTrue(response.json()["error"]["request_id"])

    def test_rank_tracking_read_add_history_and_provider_gate(self) -> None:
        empty = self.client.get("/api/v1/rank-tracking")
        self.assertEqual(empty.status_code, 200)
        self.assertFalse(empty.json()["configured"])
        added = self.client.post("/api/v1/rank-tracking/keywords", json={"keyword": "enterprise seo", "target_domain": "example.com", "country": "US", "device": "desktop"})
        self.assertEqual(added.status_code, 201)
        keyword_id = added.json()["keyword_id"]
        snapshot = self.client.get("/api/v1/rank-tracking")
        self.assertEqual(len(snapshot.json()["rows"]), 1)
        history = self.client.get(f"/api/v1/rank-tracking/keywords/{keyword_id}/history")
        self.assertEqual(history.json(), [])
        check = self.client.post("/api/v1/rank-tracking/check", json={"depth": 20})
        self.assertEqual(check.status_code, 409)
        self.assertEqual(check.json()["error"]["code"], "PROVIDER_NOT_CONFIGURED")

    def test_rank_tracking_validates_depth_and_missing_keyword(self) -> None:
        invalid = self.client.post("/api/v1/rank-tracking/check", json={"depth": 101})
        self.assertEqual(invalid.status_code, 422)
        missing = self.client.get("/api/v1/rank-tracking/keywords/00000000-0000-0000-0000-000000000000/history")
        self.assertEqual(missing.status_code, 404)

    def test_site_crawl_history_detail_and_validation_are_offline(self) -> None:
        history = self.client.get("/api/v1/site-crawl/runs")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json(), {"items": [], "latest": None})
        missing = self.client.get("/api/v1/site-crawl/runs/00000000-0000-0000-0000-000000000000")
        self.assertEqual(missing.status_code, 404)
        invalid = self.client.post("/api/v1/site-crawl/runs", json={"start_url": "not-a-url", "max_pages": 501})
        self.assertEqual(invalid.status_code, 422)

    def test_persisted_analysis_workflow_targets_are_offline(self) -> None:
        for route in ("competitor-gaps", "content", "aeo-geo"):
            with self.subTest(route=route):
                response = self.client.get(f"/api/v1/{route}/targets")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), [])

    def test_aeo_geo_detail_resources_preserve_unavailable_states(self) -> None:
        history = self.client.get("/api/v1/aeo-geo/history")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["status"], "HISTORY_UNAVAILABLE")
        sources = self.client.get("/api/v1/aeo-geo/sources")
        self.assertEqual(sources.status_code, 200)
        self.assertEqual(sources.json()["status"], "UNAVAILABLE")
        exported = self.client.get("/api/v1/aeo-geo/export?target_domain=example.com")
        self.assertEqual(exported.status_code, 200)
        self.assertIn("AEO & GEO Readiness Report", exported.text)

    def test_persisted_analysis_inputs_are_bounded(self) -> None:
        self.assertEqual(self.client.get("/api/v1/competitor-gaps/report?target_domain=").status_code, 422)
        self.assertEqual(self.client.get("/api/v1/aeo-geo/report?target_domain=").status_code, 422)
        self.assertEqual(self.client.post("/api/v1/content/briefs", json={"target_domain": "", "keyword": ""}).status_code, 422)

    def test_content_targets_page_and_history_are_honest(self) -> None:
        targets = self.client.get("/api/v1/content/targets/page?limit=10")
        self.assertEqual(targets.status_code, 200)
        self.assertEqual(targets.json()["pagination"]["page"], 1)
        history = self.client.get("/api/v1/content/history")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["status"], "HISTORY_UNAVAILABLE")

    def test_ai_visibility_reads_and_prompt_creation_are_offline(self) -> None:
        snapshot = self.client.get("/api/v1/ai-visibility")
        self.assertEqual(snapshot.status_code, 200)
        self.assertEqual(snapshot.json(), {"providers": [], "prompts": [], "history": []})
        created = self.client.post("/api/v1/ai-visibility/prompts", json={"text": "best enterprise seo platforms"})
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["text"], "best enterprise seo platforms")
        self.assertEqual(len(self.client.get("/api/v1/ai-visibility").json()["prompts"]), 1)

    def test_ai_visibility_detail_resources_are_persisted_only(self) -> None:
        for path in ("history", "source-domains", "stability"):
            with self.subTest(path=path):
                response = self.client.get(f"/api/v1/ai-visibility/{path}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), [])
        page = self.client.get("/api/v1/ai-visibility/page-intelligence?target_domain=example.com")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.json(), [])

    def test_ai_visibility_preview_is_bounded_and_execution_is_gated(self) -> None:
        prompt = self.client.post("/api/v1/ai-visibility/prompts", json={"text": "what is Nexora"}).json()
        payload = {"brand_name": "Nexora", "target_domain": "nexora.test", "prompt_ids": [prompt["prompt_id"]], "provider_names": ["OFFLINE"], "repetitions": 2}
        preview = self.client.post("/api/v1/ai-visibility/runs/preview", json=payload)
        self.assertEqual(preview.json()["total_api_calls"], 2)
        blocked = self.client.post("/api/v1/ai-visibility/runs", json=payload)
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.json()["error"]["code"], "PROVIDER_NOT_CONFIGURED")
        payload["repetitions"] = 4
        self.assertEqual(self.client.post("/api/v1/ai-visibility/runs/preview", json=payload).status_code, 422)

    def test_outreach_snapshot_and_explicit_reply_gate_are_offline(self) -> None:
        snapshot=self.client.get("/api/v1/outreach")
        self.assertEqual(snapshot.status_code,200)
        self.assertFalse(snapshot.json()["gmail_configured"])
        self.assertEqual(snapshot.json()["messages"],[])
        replies=self.client.post("/api/v1/outreach/replies/check")
        self.assertEqual(replies.status_code,409)
        self.assertEqual(replies.json()["error"]["code"],"PROVIDER_NOT_CONFIGURED")

    def test_outreach_paginated_resources_are_read_only(self) -> None:
        for resource in ("prospects", "contacts", "campaigns", "sequences", "messages", "replies", "history", "suppression"):
            with self.subTest(resource=resource):
                response = self.client.get(f"/api/v1/outreach/resources/{resource}?page=1&limit=25")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["items"], [])
                self.assertEqual(response.json()["pagination"]["limit"], 25)

    def test_local_seo_snapshot_and_gbp_gate_are_offline(self) -> None:
        snapshot=self.client.get("/api/v1/local-seo")
        self.assertEqual(snapshot.status_code,200)
        self.assertFalse(snapshot.json()["gbp_configured"])
        self.assertEqual(snapshot.json()["data"]["locations"],[])
        refresh=self.client.post("/api/v1/local-seo/gbp/refresh")
        self.assertEqual(refresh.status_code,409)
        self.assertEqual(refresh.json()["error"]["code"],"PROVIDER_NOT_CONFIGURED")

    def test_analytics_snapshot_is_persisted_only_and_source_distinct(self) -> None:
        response=self.client.get("/api/v1/analytics")
        self.assertEqual(response.status_code,200)
        payload=response.json()
        self.assertEqual({key:payload[key] for key in ("report","gsc","ga4","history")},{"report":None,"gsc":None,"ga4":None,"history":[]})
        self.assertEqual(payload["gsc_resources"],{"summary":None,"queries":[],"pages":[],"history":[]})
        self.assertEqual(payload["ga4_resources"]["summary"],[])

    def test_paid_media_history_is_offline_and_imports_are_validated(self) -> None:
        self.assertEqual(self.client.get("/api/v1/google-ads").json(),[])
        self.assertEqual(self.client.get("/api/v1/meta-ads").json(),[])
        self.assertEqual(self.client.post("/api/v1/google-ads/import",json={}).status_code,422)
        self.assertEqual(self.client.post("/api/v1/meta-ads/import",json={}).status_code,422)

    def test_cors_allows_configured_web_origin(self) -> None:
        response = self.client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:3000",
        )

    def test_cors_rejects_unconfigured_web_origin(self) -> None:
        response = self.client.options(
            "/api/v1/health",
            headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "GET"},
        )
        self.assertNotIn("access-control-allow-origin", response.headers)


if __name__ == "__main__":
    unittest.main()
