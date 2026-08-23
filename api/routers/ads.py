"""Imported-data-only paid media workflow APIs."""
from fastapi import APIRouter,Request
from src.google_ads.composition import GoogleAdsComposition,GoogleAdsSettings
from src.google_ads.dto import GoogleAdsAuditRequest,GoogleAdsAuditResponse
from src.google_ads.repository import GoogleAdsRepository
from src.google_ads.domain import GoogleAdsAudit
from src.meta_ads.composition import MetaAdsComposition,MetaAdsSettings
from src.meta_ads.dto import MetaAdsAuditRequest,MetaAdsAuditResponse
from src.meta_ads.repository import MetaAdsRepository
from src.meta_ads.domain import MetaAudit
router=APIRouter(tags=["paid-media"])
@router.get("/google-ads",response_model=list[GoogleAdsAudit])
async def google_history(request:Request):return await GoogleAdsRepository(request.app.state.settings.database_path).list_recent()
@router.post("/google-ads/import",response_model=GoogleAdsAuditResponse)
async def google_import(payload:GoogleAdsAuditRequest,request:Request):return await GoogleAdsComposition(GoogleAdsSettings(request.app.state.settings.database_path)).build().analyze(payload)
@router.get("/meta-ads",response_model=list[MetaAudit])
async def meta_history(request:Request):return await MetaAdsRepository(request.app.state.settings.database_path).list_recent()
@router.post("/meta-ads/import",response_model=MetaAdsAuditResponse)
async def meta_import(payload:MetaAdsAuditRequest,request:Request):return await MetaAdsComposition(MetaAdsSettings(request.app.state.settings.database_path)).build().analyze(payload)
