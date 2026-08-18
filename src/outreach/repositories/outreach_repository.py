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
from src.outreach.domain.crm import OutreachContact,OutreachHistoryEvent,OutreachProspect,OutreachReply,OutreachSequence,SequenceStep
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
            "CREATE TABLE IF NOT EXISTS outreach_prospects (prospect_id TEXT PRIMARY KEY,domain TEXT NOT NULL,state TEXT NOT NULL,prospect_json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS outreach_contacts (contact_id TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE COLLATE NOCASE,prospect_id TEXT,contact_json TEXT NOT NULL,FOREIGN KEY(prospect_id) REFERENCES outreach_prospects(prospect_id))",
            "CREATE TABLE IF NOT EXISTS outreach_sequences (sequence_id TEXT PRIMARY KEY,status TEXT NOT NULL,sequence_json TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS outreach_sequence_steps (step_id TEXT PRIMARY KEY,sequence_id TEXT NOT NULL,step_number INTEGER NOT NULL,step_json TEXT NOT NULL,UNIQUE(sequence_id,step_number),FOREIGN KEY(sequence_id) REFERENCES outreach_sequences(sequence_id))",
            "CREATE TABLE IF NOT EXISTS outreach_replies (reply_id TEXT PRIMARY KEY,message_id TEXT NOT NULL UNIQUE,classification TEXT NOT NULL,received_at TEXT NOT NULL,reply_json TEXT NOT NULL,FOREIGN KEY(message_id) REFERENCES outreach_messages(message_id))",
            "CREATE TABLE IF NOT EXISTS outreach_history (event_id TEXT PRIMARY KEY,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,event_type TEXT NOT NULL,occurred_at TEXT NOT NULL,event_json TEXT NOT NULL)",
            "CREATE INDEX IF NOT EXISTS idx_outreach_prospects_state ON outreach_prospects(state)",
            "CREATE INDEX IF NOT EXISTS idx_outreach_history_entity ON outreach_history(entity_type,entity_id,occurred_at DESC)",
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

    async def _save_json(self,query:str,parameters:tuple[object,...],operation:str)->None:
        await self.initialize();await self._execute(query,parameters,operation_name=operation)
    async def save_prospect(self,value:OutreachProspect)->OutreachProspect:
        await self._save_json("INSERT INTO outreach_prospects(prospect_id,domain,state,prospect_json) VALUES(?,?,?,?) ON CONFLICT(prospect_id) DO UPDATE SET domain=excluded.domain,state=excluded.state,prospect_json=excluded.prospect_json",(str(value.prospect_id),value.domain,value.state.value,value.model_dump_json()),"save outreach prospect");return value
    async def save_contact(self,value:OutreachContact)->OutreachContact:
        await self._save_json("INSERT INTO outreach_contacts(contact_id,email,prospect_id,contact_json) VALUES(?,?,?,?) ON CONFLICT(email) DO UPDATE SET prospect_id=excluded.prospect_id,contact_json=excluded.contact_json",(str(value.contact_id),str(value.email).lower(),str(value.prospect_id) if value.prospect_id else None,value.model_dump_json()),"save outreach contact");return value
    async def save_sequence(self,value:OutreachSequence)->OutreachSequence:
        await self._save_json("INSERT INTO outreach_sequences(sequence_id,status,sequence_json) VALUES(?,?,?) ON CONFLICT(sequence_id) DO UPDATE SET status=excluded.status,sequence_json=excluded.sequence_json",(str(value.sequence_id),value.status,value.model_dump_json()),"save outreach sequence");return value
    async def save_sequence_step(self,value:SequenceStep)->SequenceStep:
        await self._save_json("INSERT INTO outreach_sequence_steps(step_id,sequence_id,step_number,step_json) VALUES(?,?,?,?) ON CONFLICT(sequence_id,step_number) DO UPDATE SET step_json=excluded.step_json",(str(value.step_id),str(value.sequence_id),value.step_number,value.model_dump_json()),"save outreach sequence step");return value
    async def save_reply(self,value:OutreachReply)->OutreachReply:
        await self._save_json("INSERT INTO outreach_replies(reply_id,message_id,classification,received_at,reply_json) VALUES(?,?,?,?,?) ON CONFLICT(message_id) DO UPDATE SET classification=excluded.classification,received_at=excluded.received_at,reply_json=excluded.reply_json",(str(value.reply_id),str(value.message_id),value.classification.value,value.received_at.isoformat(),value.model_dump_json()),"save outreach reply");return value
    async def save_history(self,value:OutreachHistoryEvent)->OutreachHistoryEvent:
        await self._save_json("INSERT OR IGNORE INTO outreach_history(event_id,entity_type,entity_id,event_type,occurred_at,event_json) VALUES(?,?,?,?,?,?)",(str(value.event_id),value.entity_type,str(value.entity_id),value.event_type,value.occurred_at.isoformat(),value.model_dump_json()),"save outreach history");return value
    async def _list_json(self,table:str,field:str,model,limit:int=1000):
        await self.initialize();rows=await self._fetchall(f"SELECT {field} FROM {table} ORDER BY rowid DESC LIMIT ?",(max(1,min(limit,10000)),),operation_name=f"list {table}");return [model.model_validate_json(row[field]) for row in rows]
    async def list_prospects(self,limit:int=1000):return await self._list_json("outreach_prospects","prospect_json",OutreachProspect,limit)
    async def list_contacts(self,limit:int=1000):return await self._list_json("outreach_contacts","contact_json",OutreachContact,limit)
    async def list_campaigns(self,limit:int=1000):return await self._list_json("outreach_campaigns","campaign_json",Campaign,limit)
    async def list_sequences(self,limit:int=1000):return await self._list_json("outreach_sequences","sequence_json",OutreachSequence,limit)
    async def list_sequence_steps(self,limit:int=1000):return await self._list_json("outreach_sequence_steps","step_json",SequenceStep,limit)
    async def list_all_messages(self,limit:int=1000):return await self._list_json("outreach_messages","message_json",OutreachMessage,limit)
    async def list_replies(self,limit:int=1000):return await self._list_json("outreach_replies","reply_json",OutreachReply,limit)
    async def list_history(self,limit:int=1000):return await self._list_json("outreach_history","event_json",OutreachHistoryEvent,limit)
    async def list_suppressions(self,limit:int=1000):
        await self.initialize();rows=await self._fetchall("SELECT email,reason,created_at FROM outreach_suppressions ORDER BY created_at DESC LIMIT ?",(max(1,min(limit,10000)),),operation_name="list suppressions");return [dict(row) for row in rows]
