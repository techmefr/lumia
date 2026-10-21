from uuid import UUID

from pydantic import BaseModel

from api.domain.export.models import ExportKind, ExportStatus


class ExportJobResponse(BaseModel):
    id: UUID
    kind: ExportKind
    status: ExportStatus
    file_name: str | None
