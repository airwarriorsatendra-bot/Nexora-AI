"""Async SQLite storage for safe campaign delivery state."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from src.core.enums import CampaignStatus, MessageStatus, RecipientStatus, SuppressionReason
from src.core.exceptions import RepositoryError
from src.outreach.domain.models import Campaign, CampaignRecipient, OutreachCandidate, OutreachMessage
from src.research.repositories.sqlite_repository import SQLiteRepository


class OutreachAutomationRepository(SQLiteRepository[Campaign]):
    """Idempotent persistence; email/campaign/step is the delivery identity."""

    @property
    def schema_statements(self) -> Sequence[str]:
        return (
            "CREATE TABLE IF NOT EXISTS outreach_candidates (candidate_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE, domain TEXT NOT NULL, candidate_json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS outreach_campaigns (campaign_id TEXT PRIMARY KEY, status TEXT NOT NULL, updated_at TEXT NOT NULL, campaign_json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS outreach_recipients (recipient_id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, candidate_id TEXT NOT NULL, status TEXT NOT NULL, recipient_json TEXT NOT NULL, UNIQUE(campaign_id, candidate_id), FOREIGN KEY(campaign_id) REFERENCES outreach_campaigns(campaign_id), FOREIGN KEY(candidate_id) REFERENCES outreach_candidates(candidate_id))",
            "CREATE TABLE IF NOT EXISTS outreach_messages (message_id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL, recipient_id TEXT NOT NULL, sequence_step INTEGER NOT NULL, status TEXT NOT NULL, message_json TEXT NOT NULL, UNIQUE(campaign_id, recipient_id, sequence_step), FOREIGN KEY(campaign_id) REFERENCES outreach_campaigns(campaign_id), FOREIGN KEY(recipient_id) REFERENCES outreach_recipients(recipient_id))",
            "CREATE TABLE IF NOT EXISTS outreach_delivery_attempts (attempt_id TEXT PRIMARY KEY, message_id TEXT NOT NULL, provider TEXT NOT NULL, status TEXT NOT NULL, provider_message_id TEXT, error_code TEXT, error_message TEXT, attempted_at TEXT NOT NULL, UNIQUE(message_id, provider, status), FOREIGN KEY(message_id) REFERENCES outreach_messages(message_id))",
            "CREATE TABLE IF NOT EXISTS outreach_suppressions (email TEXT PRIMARY KEY COLLATE NOCASE, reason TEXT NOT NULL, created_at TEXT NOT NULL)",
            "CREATE INDEX IF NOT EXISTS idx_outreach_recipients_campaign ON outreach_recipients(campaign_id)",
            "CREATE INDEX IF NOT EXISTS idx_outreach_messages_status ON outreach_messages(status)",
            "CREATE INDEX IF NOT EXISTS idx_outreach_attempts_message ON outreach_delivery_attempts(message_id)",
        )

    def __init__(self, database_path: str | Path) -> None: super().__init__(database_path)
    async def save_candidate(self, value: OutreachCandidate) -> OutreachCandidate:
        await self.initialize(); await self._save("outreach_candidates", "candidate_id", value.candidate_id, value, (str(value.email), value.domain), "email=excluded.email, domain=excluded.domain, candidate_json=excluded.candidate_json"); return value
    async def save_campaign(self, value: Campaign) -> Campaign:
        await self.initialize(); await self._save("outreach_campaigns", "campaign_id", value.campaign_id, value, (value.status.value, value.updated_at.isoformat()), "status=excluded.status, updated_at=excluded.updated_at, campaign_json=excluded.campaign_json"); return value
    async def save_recipient(self, value: CampaignRecipient) -> CampaignRecipient:
        await self.initialize(); payload=json.dumps(value.model_dump(mode="json"), separators=(",",":")); await self._execute("INSERT INTO outreach_recipients(recipient_id,campaign_id,candidate_id,status,recipient_json) VALUES(?,?,?,?,?) ON CONFLICT(campaign_id,candidate_id) DO UPDATE SET status=excluded.status,recipient_json=excluded.recipient_json", (str(value.recipient_id),str(value.campaign_id),str(value.candidate_id),value.status.value,payload),operation_name="save recipient"); return value
    async def save_message(self, value: OutreachMessage) -> OutreachMessage:
        await self.initialize(); payload=json.dumps(value.model_dump(mode="json"), separators=(",",":")); await self._execute("INSERT INTO outreach_messages(message_id,campaign_id,recipient_id,sequence_step,status,message_json) VALUES(?,?,?,?,?,?) ON CONFLICT(campaign_id,recipient_id,sequence_step) DO UPDATE SET status=excluded.status,message_json=excluded.message_json", (str(value.message_id),str(value.campaign_id),str(value.recipient_id),value.sequence_step,value.status.value,payload),operation_name="save message"); return value
    async def _save(self, table: str, key: str, identifier: UUID, value: object, values: tuple[str,...], update: str) -> None:
        payload=json.dumps(value.model_dump(mode="json"), separators=(",",":")); columns=f"{key}, " + ("email, domain" if table.endswith("candidates") else "status, updated_at") + ", " + ("candidate_json" if table.endswith("candidates") else "campaign_json"); await self._execute(f"INSERT INTO {table}({columns}) VALUES(?,?,?,?) ON CONFLICT({key}) DO UPDATE SET {update}",(str(identifier),*values,payload),operation_name=f"save {table}")
    async def get_candidate(self, candidate_id: UUID) -> OutreachCandidate | None: return await self._get("outreach_candidates","candidate_id",candidate_id,OutreachCandidate,"candidate_json")
    async def find_candidate_by_email(self, email: str) -> OutreachCandidate | None:
        await self.initialize(); row=await self._fetchone("SELECT candidate_json FROM outreach_candidates WHERE email=?",(email.lower(),),operation_name="find candidate email"); return None if row is None else OutreachCandidate.model_validate_json(row["candidate_json"])
    async def get_campaign(self, campaign_id: UUID) -> Campaign | None: return await self._get("outreach_campaigns","campaign_id",campaign_id,Campaign,"campaign_json")
    async def get_recipient(self, recipient_id: UUID) -> CampaignRecipient | None: return await self._get("outreach_recipients","recipient_id",recipient_id,CampaignRecipient,"recipient_json")
    async def find_recipient(self, campaign_id: UUID, candidate_id: UUID) -> CampaignRecipient | None:
        await self.initialize(); row=await self._fetchone("SELECT recipient_json FROM outreach_recipients WHERE campaign_id=? AND candidate_id=?",(str(campaign_id),str(candidate_id)),operation_name="find campaign recipient"); return None if row is None else CampaignRecipient.model_validate_json(row["recipient_json"])
    async def get_message(self, message_id: UUID) -> OutreachMessage | None: return await self._get("outreach_messages","message_id",message_id,OutreachMessage,"message_json")
    async def find_message(self, campaign_id: UUID, recipient_id: UUID, step: int) -> OutreachMessage | None:
        await self.initialize(); row=await self._fetchone("SELECT message_json FROM outreach_messages WHERE campaign_id=? AND recipient_id=? AND sequence_step=?",(str(campaign_id),str(recipient_id),step),operation_name="find outreach message"); return None if row is None else OutreachMessage.model_validate_json(row["message_json"])
    async def _get(self, table: str,key: str,identifier: UUID,model,field: str):
        await self.initialize(); row=await self._fetchone(f"SELECT {field} FROM {table} WHERE {key}=?",(str(identifier),),operation_name=f"get {table}"); return None if row is None else model.model_validate_json(row[field])
    async def is_suppressed(self,email:str)->bool:
        await self.initialize(); return (await self._fetch_value("SELECT 1 FROM outreach_suppressions WHERE email=?",(email.lower(),),operation_name="check suppression")) is not None
    async def suppress(self,email:str,reason:SuppressionReason)->None:
        await self.initialize(); await self._execute("INSERT INTO outreach_suppressions(email,reason,created_at) VALUES(?,?,?) ON CONFLICT(email) DO UPDATE SET reason=excluded.reason",(email.lower(),reason.value,datetime.now(UTC).isoformat()),operation_name="suppress recipient")
    async def sent_attempt_exists(self,message_id:UUID)->bool:
        return (await self._fetch_value("SELECT 1 FROM outreach_delivery_attempts WHERE message_id=? AND status='accepted'",(str(message_id),),operation_name="check sent attempt")) is not None
    async def save_attempt(self,message_id:UUID,provider:str,status:str,provider_message_id:str|None=None,error_code:str|None=None,error_message:str|None=None)->None:
        from uuid import uuid4
        await self.initialize(); await self._execute("INSERT OR IGNORE INTO outreach_delivery_attempts(attempt_id,message_id,provider,status,provider_message_id,error_code,error_message,attempted_at) VALUES(?,?,?,?,?,?,?,?)",(str(uuid4()),str(message_id),provider,status,provider_message_id,error_code,error_message,datetime.now(UTC).isoformat()),operation_name="save delivery attempt")
    async def list_messages(self,campaign_id:UUID,limit:int=100)->list[OutreachMessage]:
        await self.initialize(); rows=await self._fetchall("SELECT message_json FROM outreach_messages WHERE campaign_id=? ORDER BY sequence_step LIMIT ?",(str(campaign_id),max(1,min(limit,500))),operation_name="list messages"); return [OutreachMessage.model_validate_json(row["message_json"]) for row in rows]
    async def summary_counts(self) -> dict[str, int]:
        """Return observable persisted outreach counts without implying delivery metrics."""
        await self.initialize()
        tables = {"campaigns": "outreach_campaigns", "recipients": "outreach_recipients", "messages": "outreach_messages", "suppressions": "outreach_suppressions"}
        return {name: int(await self._fetch_value(f"SELECT COUNT(*) FROM {table}", operation_name=f"count {name}") or 0) for name, table in tables.items()}
