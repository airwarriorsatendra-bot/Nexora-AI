"""SEO HTTP schemas that retain existing domain models."""

from pydantic import BaseModel, ConfigDict

from api.schemas.pagination import PageMetadata
from src.seo.domain.seo_audit import SEOAudit


class SEOAuditPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SEOAudit]
    pagination: PageMetadata
