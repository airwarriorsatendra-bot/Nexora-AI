"""Persisted-only, source-separated Analytics HTTP resources."""
from __future__ import annotations
import csv,io
from datetime import date
from typing import Any,Literal
from fastapi import APIRouter,Query,Request,status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,ConfigDict
from api.errors import APIError
from src.analytics.composition import AnalyticsComposition,AnalyticsSettings
from src.ga4.domain import GA4Dimension
from src.ga4.composition import GA4Composition,GA4Settings
from src.ga4.domain import GA4Property,ReportingPeriod as GA4Period
from src.ga4.dto import GA4ReportRequest
from src.search_console.domain import SearchDimension
from src.search_console.composition import SearchConsoleComposition,SearchConsoleSettings
from src.search_console.domain import ReportingPeriod,SearchConsoleProperty
from src.search_console.dto import SearchAnalyticsRequest

router=APIRouter(prefix="/analytics",tags=["analytics"])
class Page(BaseModel):
 model_config=ConfigDict(extra="forbid");items:list[dict[str,Any]];total:int;limit:int;offset:int;has_more:bool
class AnalyticsSnapshot(BaseModel):
 model_config=ConfigDict(extra="forbid");report:Any=None;gsc:Any=None;ga4:Any=None;history:list[Any];gsc_resources:dict[str,Any];ga4_resources:dict[str,Any]
class GSCRefresh(BaseModel):
 property:str;start_date:date;end_date:date;permission_level:str="siteOwner"
class GA4Refresh(BaseModel):
 property_id:str;start_date:date;end_date:date;display_name:str=""
def build(request:Request):return AnalyticsComposition(AnalyticsSettings(request.app.state.settings.database_path)).build()
def valid_dates(start:date|None,end:date|None):
 if (start is None)!=(end is None) or (start and end and end<start):raise APIError(status.HTTP_422_UNPROCESSABLE_CONTENT,"INVALID_DATE_WINDOW","Provide a valid start_date and end_date window.")
def period_match(snapshot,start,end):return start is None or (snapshot.period.start_date==start and snapshot.period.end_date==end)
async def gsc_snapshot(repo,dims,site,start,end):
 valid_dates(start,end)
 if start is None:return await repo.latest(site_url=site,dimensions=dims)
 return next((x for x in reversed(await repo.history(site_url=site,dimensions=dims,limit=500)) if period_match(x,start,end)),None)
async def ga4_snapshot(repo,dims,property_id,start,end):
 valid_dates(start,end)
 return next((x for x in reversed(await repo.history(dimensions=dims,limit=500)) if (not property_id or x.property.property_id==property_id) and period_match(x,start,end)),None)
def gsc_summary_row(s):
 if not s:return None
 t=s.totals;return {"clicks":t.clicks,"impressions":t.impressions,"ctr":t.ctr,"average_position":t.average_position,"start_date":s.period.start_date,"end_date":s.period.end_date,"property":s.property.site_url,"source":s.source,"provider":s.provider,"observed_at":s.captured_at}
def gsc_rows(s,d):
 if not s:return []
 return [{d.value:r.dimension_value(d),"clicks":r.clicks,"impressions":r.impressions,"ctr":r.ctr,"average_position":r.average_position,"start_date":s.period.start_date,"end_date":s.period.end_date,"property":s.property.site_url,"source":s.source,"provider":s.provider,"observed_at":s.captured_at} for r in s.records]
def ga4_rows(s,d=None):
 if not s:return []
 out=[]
 for r in s.records:
  row={"start_date":s.period.start_date,"end_date":s.period.end_date,"property_id":s.property.property_id,"source":s.source,"provider":s.provider,"observed_at":s.captured_at}
  if d:row[d.value]=r.keys[0] if r.keys else None
  row.update(r.metrics);out.append(row)
 return out
def sorted_rows(rows,field,direction):
 def key(row):
  value=row.get(field);return (value is None,value.casefold() if isinstance(value,str) else value)
 return sorted(rows,key=key,reverse=direction=="desc")
def page(rows,limit,offset):return Page(items=rows[offset:offset+limit],total=len(rows),limit=limit,offset=offset,has_more=offset+limit<len(rows))

@router.get("",response_model=AnalyticsSnapshot)
async def snapshot(request:Request):
 app=build(request)
 try:
  history=await app.repository.history();gsc=await app.search_console_repository.latest(dimensions=());ga4=await app.ga4_repository.latest()
  gr={"summary":gsc_summary_row(gsc),"queries":gsc_rows(await app.search_console_repository.latest(dimensions=(SearchDimension.QUERY,)),SearchDimension.QUERY),"pages":gsc_rows(await app.search_console_repository.latest(dimensions=(SearchDimension.PAGE,)),SearchDimension.PAGE),"history":gsc_rows(await app.search_console_repository.latest(dimensions=(SearchDimension.DATE,)),SearchDimension.DATE)}
  ar={"summary":ga4_rows(ga4)}
  for name,d in GA4_RESOURCES.items():ar[name]=ga4_rows(await app.ga4_repository.latest(dimensions=(d,)),d)
  return AnalyticsSnapshot(report=history[-1] if history else None,gsc=gsc,ga4=ga4,history=history,gsc_resources=gr,ga4_resources=ar)
 finally:await app.aclose()

@router.get("/gsc/summary")
async def gsc_summary(request:Request,property:str|None=Query(None,max_length=2048),start_date:date|None=None,end_date:date|None=None):
 app=build(request)
 try:return gsc_summary_row(await gsc_snapshot(app.search_console_repository,(),property,start_date,end_date))
 finally:await app.aclose()
async def gsc_list(request,d,text,property,start,end,min_i,min_c,sort_by,direction,limit,offset):
 app=build(request)
 try:
  rows=gsc_rows(await gsc_snapshot(app.search_console_repository,(d,),property,start,end),d)
  if text:rows=[r for r in rows if text.casefold() in str(r[d.value] or "").casefold()]
  rows=[r for r in rows if r["impressions"]>=min_i and r["clicks"]>=min_c]
  return page(sorted_rows(rows,sort_by,direction),limit,offset)
 finally:await app.aclose()
@router.get("/gsc/queries",response_model=Page)
async def gsc_queries(request:Request,query:str|None=Query(None,max_length=512),property:str|None=Query(None,max_length=2048),start_date:date|None=None,end_date:date|None=None,minimum_impressions:int=Query(0,ge=0),minimum_clicks:int=Query(0,ge=0),sort_by:Literal["clicks","impressions","ctr","average_position","query","observed_at"]="clicks",direction:Literal["asc","desc"]="desc",limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0)):return await gsc_list(request,SearchDimension.QUERY,query,property,start_date,end_date,minimum_impressions,minimum_clicks,sort_by,direction,limit,offset)
@router.get("/gsc/pages",response_model=Page)
async def gsc_pages(request:Request,page_filter:str|None=Query(None,alias="page",max_length=2048),property:str|None=Query(None,max_length=2048),start_date:date|None=None,end_date:date|None=None,minimum_impressions:int=Query(0,ge=0),minimum_clicks:int=Query(0,ge=0),sort_by:Literal["clicks","impressions","ctr","average_position","page","observed_at"]="clicks",direction:Literal["asc","desc"]="desc",limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0)):return await gsc_list(request,SearchDimension.PAGE,page_filter,property,start_date,end_date,minimum_impressions,minimum_clicks,sort_by,direction,limit,offset)
@router.get("/gsc/history",response_model=Page)
async def gsc_history(request:Request,date_filter:str|None=Query(None,alias="date",max_length=10),property:str|None=Query(None,max_length=2048),start_date:date|None=None,end_date:date|None=None,minimum_impressions:int=Query(0,ge=0),minimum_clicks:int=Query(0,ge=0),sort_by:Literal["clicks","impressions","ctr","average_position","date","observed_at"]="date",direction:Literal["asc","desc"]="asc",limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0)):return await gsc_list(request,SearchDimension.DATE,date_filter,property,start_date,end_date,minimum_impressions,minimum_clicks,sort_by,direction,limit,offset)

GA4_RESOURCES={"traffic":GA4Dimension.DATE,"pages":GA4Dimension.LANDING_PAGE,"acquisition":GA4Dimension.CHANNEL,"events":GA4Dimension.EVENT,"devices":GA4Dimension.DEVICE,"countries":GA4Dimension.COUNTRY}
@router.get("/ga4/summary")
async def ga4_summary(request:Request,property_id:str|None=Query(None,max_length=128),start_date:date|None=None,end_date:date|None=None):
 app=build(request)
 try:
  rows=ga4_rows(await ga4_snapshot(app.ga4_repository,(),property_id,start_date,end_date));return rows[0] if rows else None
 finally:await app.aclose()
@router.get("/ga4/{resource}",response_model=Page)
async def ga4_resource(request:Request,resource:Literal["traffic","pages","acquisition","events","devices","countries"],value:str|None=Query(None,max_length=2048),property_id:str|None=Query(None,max_length=128),start_date:date|None=None,end_date:date|None=None,sort_by:str=Query("sessions",max_length=64),direction:Literal["asc","desc"]="desc",limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0)):
 d=GA4_RESOURCES[resource];app=build(request)
 try:
  rows=ga4_rows(await ga4_snapshot(app.ga4_repository,(d,),property_id,start_date,end_date),d);allowed={d.value,"observed_at"}|{k for row in rows for k in row if k not in {"start_date","end_date","property_id","source","provider"}}
  if sort_by not in allowed:raise APIError(status.HTTP_422_UNPROCESSABLE_CONTENT,"INVALID_SORT","The GA4 sort field is not persisted for this resource.")
  if value:rows=[r for r in rows if value.casefold() in str(r[d.value] or "").casefold()]
  return page(sorted_rows(rows,sort_by,direction),limit,offset)
 finally:await app.aclose()

@router.get("/comparison/{source}")
async def comparison(request:Request,source:Literal["gsc","ga4"]):
 app=build(request)
 try:
  repo=app.search_console_repository if source=="gsc" else app.ga4_repository;history=await repo.history(dimensions=(),limit=500)
  if len(history)<2:return {"status":"HISTORY_UNAVAILABLE","current":None,"previous":None,"changes":None}
  current=history[-1];previous=next((x for x in reversed(history[:-1]) if x.property==current.property and (x.period.end_date-x.period.start_date)==(current.period.end_date-current.period.start_date)),None)
  if previous is None:return {"status":"HISTORY_UNAVAILABLE","current":None,"previous":None,"changes":None}
  if source=="gsc":
   c,p=current.totals,previous.totals;changes={"clicks":c.clicks-p.clicks,"impressions":c.impressions-p.impressions,"ctr":c.ctr-p.ctr,"average_position":c.average_position-p.average_position};current_row=gsc_summary_row(current);previous_row=gsc_summary_row(previous)
  else:
   current_row=ga4_rows(current)[0] if ga4_rows(current) else {};previous_row=ga4_rows(previous)[0] if ga4_rows(previous) else {};changes={k:current.totals[k]-previous.totals.get(k,0) for k in current.metrics if k in previous.metrics}
  return {"status":"AVAILABLE","current":current_row,"previous":previous_row,"changes":changes}
 finally:await app.aclose()

@router.get("/cross-source/pages",response_model=Page)
async def cross_source_pages(request:Request,limit:int=Query(25,ge=1,le=100),offset:int=Query(0,ge=0)):
 from urllib.parse import urljoin,urlsplit,urlunsplit
 app=build(request)
 try:
  g=await app.search_console_repository.latest(dimensions=(SearchDimension.PAGE,));a=await app.ga4_repository.latest(dimensions=(GA4Dimension.LANDING_PAGE,))
  if not g or not a or g.period.start_date!=a.period.start_date or g.period.end_date!=a.period.end_date:return page([],limit,offset)
  def norm(value,base):
   u=urlsplit(urljoin(base,value));return urlunsplit((u.scheme.casefold(),u.netloc.casefold(),u.path or "/",u.query,""))
  host=urlsplit(g.property.site_url).netloc.casefold();ga={norm(r.keys[0],g.property.site_url):r for r in a.records if r.keys and urlsplit(norm(r.keys[0],g.property.site_url)).netloc.casefold()==host};rows=[]
  for r in g.records:
   url=norm(r.dimension_value(SearchDimension.PAGE) or "",g.property.site_url);match=ga.get(url)
   if match:rows.append({"page":url,"search_evidence":{"clicks":r.clicks,"impressions":r.impressions,"ctr":r.ctr,"average_position":r.average_position,"source":g.source},"behavior_evidence":{"metrics":match.metrics,"source":a.source},"window":{"start_date":str(g.period.start_date),"end_date":str(g.period.end_date)},"attribution":"NOT_INFERRED"})
  return page(rows,limit,offset)
 finally:await app.aclose()

@router.post("/refresh/gsc")
async def refresh_gsc(payload:GSCRefresh,request:Request):
 valid_dates(payload.start_date,payload.end_date);env=request.app.state.settings.environment_dict();settings=SearchConsoleSettings.from_environment({**env,"DATABASE_URL":str(request.app.state.settings.database_path)});app=SearchConsoleComposition(settings).build()
 try:
  if not settings.configured:raise APIError(status.HTTP_409_CONFLICT,"PROVIDER_NOT_CONFIGURED","Google Search Console refresh is not configured.")
  prop=SearchConsoleProperty(site_url=payload.property,permission_level=payload.permission_level);return await app.service.refresh(property=prop,request=SearchAnalyticsRequest(property=prop,period=ReportingPeriod(start_date=payload.start_date,end_date=payload.end_date)))
 finally:await app.aclose()

@router.post("/refresh/ga4")
async def refresh_ga4(payload:GA4Refresh,request:Request):
 valid_dates(payload.start_date,payload.end_date);env=request.app.state.settings.environment_dict();settings=GA4Settings.from_environment({**env,"DATABASE_URL":str(request.app.state.settings.database_path),"GA4_PROPERTY_ID":payload.property_id});app=GA4Composition(settings).build()
 try:
  if not all((settings.client_id,settings.client_secret,settings.refresh_token)):raise APIError(status.HTTP_409_CONFLICT,"PROVIDER_NOT_CONFIGURED","Google Analytics 4 refresh is not configured.")
  prop=GA4Property(property_id=payload.property_id,display_name=payload.display_name);return await app.service.refresh_all(GA4ReportRequest(property=prop,period=GA4Period(start_date=payload.start_date,end_date=payload.end_date)))
 finally:await app.aclose()

@router.get("/exports/{resource}")
async def export_resource(request:Request,resource:Literal["gsc-queries","gsc-pages","gsc-history","ga4-traffic","ga4-pages","ga4-acquisition","ga4-events"],value:str|None=Query(None,max_length=2048),start_date:date|None=None,end_date:date|None=None,sort_by:str|None=Query(None,max_length=64),direction:Literal["asc","desc"]="desc"):
 app=build(request)
 try:
  if resource.startswith("gsc-"):
   d={"gsc-queries":SearchDimension.QUERY,"gsc-pages":SearchDimension.PAGE,"gsc-history":SearchDimension.DATE}[resource];rows=gsc_rows(await gsc_snapshot(app.search_console_repository,(d,),None,start_date,end_date),d);allowed={"clicks","impressions","ctr","average_position",d.value,"observed_at"}
  else:
   d={"ga4-traffic":GA4Dimension.DATE,"ga4-pages":GA4Dimension.LANDING_PAGE,"ga4-acquisition":GA4Dimension.CHANNEL,"ga4-events":GA4Dimension.EVENT}[resource];rows=ga4_rows(await ga4_snapshot(app.ga4_repository,(d,),None,start_date,end_date),d);allowed={d.value,"observed_at"}|{k for row in rows for k in row}
  if value:rows=[r for r in rows if value.casefold() in str(r[d.value] or "").casefold()]
  if sort_by:
   if sort_by not in allowed:raise APIError(status.HTTP_422_UNPROCESSABLE_CONTENT,"INVALID_SORT","The export sort field is unavailable.")
   rows=sorted_rows(rows,sort_by,direction)
  output=io.StringIO()
  if rows:
   writer=csv.DictWriter(output,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
  return StreamingResponse(iter([output.getvalue()]),media_type="text/csv",headers={"Content-Disposition":f'attachment; filename="nexora_{resource}.csv"'})
 finally:await app.aclose()
