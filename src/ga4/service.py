from src.ga4.domain import GA4Snapshot,GA4Dimension
from src.ga4.dto import GA4ReportRequest
class GA4Service:
 def __init__(self,provider,repository):self.provider,self.repository=provider,repository
 async def list_properties(self):return await self.provider.list_properties()
 async def refresh(self,request:GA4ReportRequest):
  records=await self.provider.run_report(request);snapshot=GA4Snapshot(property=request.property,period=request.period,dimensions=request.dimensions,metrics=request.metrics,records=records);await self.repository.save(snapshot);return snapshot
 async def refresh_standard_views(self,request):
  return {dimensions:await self.refresh(request.model_copy(update={'dimensions':dimensions})) for dimensions in ((),(GA4Dimension.CHANNEL,),(GA4Dimension.LANDING_PAGE,),(GA4Dimension.EVENT,),(GA4Dimension.DEVICE,),(GA4Dimension.COUNTRY,),(GA4Dimension.DATE,))}
