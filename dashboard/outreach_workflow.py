"""Dashboard boundary for explicit source-layer outreach operations."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from src.outreach.composition import OutreachApplication, OutreachComposition, OutreachSettings
from src.outreach.dto.requests import AddCandidateRequest, AddRecipientRequest, CreateCampaignRequest, PrepareMessageRequest, SendMessageRequest


class OutreachDashboardWorkflow:
    def __init__(self, application_factory: Callable[[], OutreachApplication] | None = None) -> None: self._factory=application_factory or (lambda: OutreachComposition(OutreachSettings.from_environment()).build())
    async def create_campaign(self,name:str,description:str,objective):
        app=self._factory()
        try: return await app.service.create_campaign(CreateCampaignRequest(name=name,description=description,objective=objective))
        finally: await app.aclose()
    async def add_candidate(self,url:str,email:str,name:str):
        app=self._factory()
        try: return await app.service.add_candidate(AddCandidateRequest(website_url=url,email=email,contact_name=name))
        finally: await app.aclose()
    async def prepare(self,campaign_id,candidate_id,subject:str,body:str):
        app=self._factory()
        try:
            recipient=await app.service.add_recipient(AddRecipientRequest(campaign_id=campaign_id,candidate_id=candidate_id))
            return await app.service.prepare_message(PrepareMessageRequest(campaign_id=campaign_id,recipient_id=recipient.recipient_id,subject_template=subject,body_template=body))
        finally: await app.aclose()
    async def send(self,message_id, dry_run:bool=True):
        app=self._factory()
        try: return await app.service.send(SendMessageRequest(message_id=message_id,dry_run=dry_run))
        finally: await app.aclose()
    async def snapshot(self):
        app=self._factory()
        try: return await app.service.snapshot()
        finally: await app.aclose()


def messages_to_dataframe(messages:list[object])->pd.DataFrame:
    return pd.DataFrame([message.model_dump(mode="json") for message in messages])

def outreach_frame(items): return pd.DataFrame([item.model_dump(mode="json") if hasattr(item,"model_dump") else item for item in items])
def outreach_report(snapshot):
    analytics=snapshot["analytics"]
    return "# Nexora Outreach Report\n\nOffline evidence and explicit send events only.\n\n"+"\n".join((f"- Prospects: {analytics.prospects}",f"- Contacts: {analytics.contacts}",f"- Messages sent: {analytics.sent}",f"- Replies: {analytics.replies}","- Open rates and guaranteed backlink gains are not claimed."))
