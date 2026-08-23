"""Cross-vertical persisted workspace summary contract."""

from pydantic import BaseModel, ConfigDict

from api.schemas.dashboard import DashboardMetric


class WorkspaceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace: str
    metrics: list[DashboardMetric]
    note: str
