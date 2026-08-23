from __future__ import annotations
import hashlib,json
from pathlib import Path
from src.research.repositories.sqlite_repository import SQLiteRepository
from src.ai_visibility.domain import AIVisibilityObservation,AIVisibilityRun,MonitoredPrompt
class AIVisibilityRepository(SQLiteRepository[object]):
 @property
 def schema_statements(self):return ("CREATE TABLE IF NOT EXISTS ai_visibility_prompts(prompt_id TEXT PRIMARY KEY,prompt_key TEXT UNIQUE NOT NULL,prompt_json TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)","CREATE TABLE IF NOT EXISTS ai_visibility_runs(run_id TEXT PRIMARY KEY,created_at TEXT NOT NULL,run_json TEXT NOT NULL)","CREATE TABLE IF NOT EXISTS ai_visibility_observations(observation_id TEXT PRIMARY KEY,observation_key TEXT UNIQUE NOT NULL,run_id TEXT NOT NULL,prompt_id TEXT NOT NULL,provider TEXT NOT NULL,model TEXT NOT NULL,state TEXT NOT NULL,observed_at TEXT NOT NULL,observation_json TEXT NOT NULL,FOREIGN KEY(run_id) REFERENCES ai_visibility_runs(run_id),FOREIGN KEY(prompt_id) REFERENCES ai_visibility_prompts(prompt_id))","CREATE INDEX IF NOT EXISTS idx_ai_visibility_history ON ai_visibility_observations(prompt_id,provider,model,observed_at)",)
 async def save_prompt(self,prompt):
  await self.initialize();key=hashlib.sha256((prompt.text.casefold()+"|"+prompt.category.value+"|"+prompt.context).encode()).hexdigest();existing=await self._fetchone("SELECT prompt_json FROM ai_visibility_prompts WHERE prompt_key=?",(key,),operation_name="find visibility prompt")
  if existing:return MonitoredPrompt.model_validate_json(existing["prompt_json"])
  await self._execute("INSERT INTO ai_visibility_prompts(prompt_id,prompt_key,prompt_json) VALUES(?,?,?)",(str(prompt.prompt_id),key,prompt.model_dump_json()),operation_name="save visibility prompt");return prompt
 async def list_prompts(self):
  await self.initialize();rows=await self._fetchall("SELECT prompt_json FROM ai_visibility_prompts ORDER BY created_at,prompt_id",operation_name="list visibility prompts");return [MonitoredPrompt.model_validate_json(r["prompt_json"]) for r in rows]
 async def count_prompts(self):
  await self.initialize();row=await self._fetchone("SELECT COUNT(*) AS count FROM ai_visibility_prompts",operation_name="count visibility prompts");return int(row["count"])
 async def save_run(self,run):
  await self.initialize();base=run.model_copy(update={"observations":()});await self._execute("INSERT INTO ai_visibility_runs(run_id,created_at,run_json) VALUES(?,?,?) ON CONFLICT(run_id) DO NOTHING",(str(run.run_id),run.created_at.isoformat(),base.model_dump_json()),operation_name="save visibility run")
  for o in run.observations:
   key=hashlib.sha256((str(run.run_id)+str(o.prompt_id)+o.provider+o.model+o.observed_at.isoformat()).encode()).hexdigest();await self._execute("INSERT INTO ai_visibility_observations(observation_id,observation_key,run_id,prompt_id,provider,model,state,observed_at,observation_json) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(observation_key) DO NOTHING",(str(o.observation_id),key,str(run.run_id),str(o.prompt_id),o.provider,o.model,o.state.value,o.observed_at.isoformat(),o.model_dump_json()),operation_name="save visibility observation")
  return run
 async def history(self,limit=10000):
  await self.initialize();rows=await self._fetchall("SELECT observation_json FROM ai_visibility_observations ORDER BY observed_at,rowid LIMIT ?",(min(10000,max(1,limit)),),operation_name="visibility history");return [AIVisibilityObservation.model_validate_json(r["observation_json"]) for r in rows]
 async def count_observations(self):
  await self.initialize();row=await self._fetchone("SELECT COUNT(*) AS count FROM ai_visibility_observations",operation_name="count visibility observations");return int(row["count"])
