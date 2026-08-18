"""Cautious, non-attribution comparison of matching GSC and GA4 page evidence."""
from __future__ import annotations
from urllib.parse import urlsplit
from src.search_console.domain import SearchPerformanceSnapshot,SearchDimension
from src.ga4.domain import GA4Snapshot,GA4Dimension
def _path(value:str)->str:return urlsplit(value).path.rstrip('/') or '/'
def insights(gsc:SearchPerformanceSnapshot,ga4:GA4Snapshot)->list[dict[str,str]]:
 if (gsc.period.start_date,gsc.period.end_date)!=(ga4.period.start_date,ga4.period.end_date):return []
 if gsc.dimensions!=(SearchDimension.PAGE,) or ga4.dimensions!=(GA4Dimension.LANDING_PAGE,):return []
 by_path={_path(row.keys[0]):row for row in ga4.records if row.keys}
 result=[]
 for row in gsc.records:
  if not row.keys or _path(row.keys[0]) not in by_path:continue
  behavior=by_path[_path(row.keys[0])].metrics;engagement=behavior.get('engagementRate',0)
  if row.impressions>=1000 and row.ctr<=0.05 and engagement>=0.6: result.append({'page':row.keys[0],'title':'CTR optimization opportunity','evidence':'High search visibility with strong on-site engagement across separate measurement systems.','recommendation':'Review title and snippet relevance; this is not cross-platform attribution.'})
  elif row.clicks>=100 and engagement<=0.3: result.append({'page':row.keys[0],'title':'Landing page review opportunity','evidence':'Strong search clicks and weak GA4 engagement are separate signals.','recommendation':'Review content and experience; GSC clicks are not GA4 sessions.'})
 return result
