from uuid import UUID

from pydantic import BaseModel


class FolderCreateRequest(BaseModel):
    name: str


class FolderResponse(BaseModel):
    id: UUID
    name: str
