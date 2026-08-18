from pydantic import ConfigDict,Field
from src.ga4.domain import GA4Dimension,GA4Property,ReportingPeriod
from src.shared.base.base_model import NexoraModel
class GA4ReportRequest(NexoraModel):
    model_config=ConfigDict(frozen=True,extra="forbid")
    property: GA4Property; period: ReportingPeriod; dimensions: tuple[GA4Dimension,...]=(); metrics: tuple[str,...]=( "activeUsers","sessions","engagedSessions","engagementRate","eventCount","keyEvents"); limit: int=Field(default=100,ge=1,le=10000)
