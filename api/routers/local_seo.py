"""Persisted Local SEO workspace and explicit GBP refresh."""
from typing import Any
from fastapi import APIRouter,Request,status
from pydantic import BaseModel, ConfigDict
from api.errors import APIError
from src.local_seo.composition import LocalSEOComposition,LocalSEOSettings
from src.core.exceptions import AuthenticationError, AuthorizationError, ExternalAPIError
router=APIRouter(prefix="/local-seo",tags=["local-seo"])
class LocalSEOSnapshot(BaseModel):
 model_config=ConfigDict(extra="forbid")
 gbp_configured: bool
 data: Any
class GBPRefreshResponse(BaseModel):
 model_config=ConfigDict(extra="allow")
 status: str = "REFRESHED"
def build(request:Request):
 environment=request.app.state.settings.environment_dict();environment["DATABASE_URL"]=str(request.app.state.settings.database_path);settings=LocalSEOSettings.from_environment(environment);return settings,LocalSEOComposition(settings).build()
@router.get("", response_model=LocalSEOSnapshot)
async def snapshot(request:Request):
 settings,app=build(request)
 try:return {"gbp_configured":settings.gbp_configured,"data":await app.snapshot()}
 finally:await app.aclose()
@router.post("/gbp/refresh", response_model=GBPRefreshResponse)
async def refresh(request:Request):
 settings,app=build(request)
 try:
  if not settings.gbp_configured:raise APIError(status.HTTP_409_CONFLICT,"PROVIDER_NOT_CONFIGURED","Google Business Profile refresh is not configured.")
  try:
   return {"status":"REFRESHED","data":await app.refresh_business_profile()}
  except (AuthenticationError, AuthorizationError) as error:
   return {"status":"ACCESS_BLOCKED","message":str(error)}
  except ExternalAPIError as error:
   message=str(error)
   return {"status":"QUOTA_BLOCKED" if "429" in message or "quota" in message.casefold() else "ACCESS_BLOCKED","message":message}
 finally:await app.aclose()
