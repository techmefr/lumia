from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.feed.models import Folder
from api.domain.feed.schemas import FolderCreateRequest, FolderResponse
from api.domain.user.models import User
from api.technical.auth.middleware import get_current_user
from api.technical.db import get_db_session

router = APIRouter()


def _to_folder_response(folder: Folder) -> FolderResponse:
    return FolderResponse(id=folder.id, name=folder.name)


@router.get("/folders", response_model=list[FolderResponse])
async def list_folders(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[FolderResponse]:
    folders = await session.scalars(select(Folder).where(Folder.user_id == user.id))
    return [_to_folder_response(folder) for folder in folders]


@router.post(
    "/folders", response_model=FolderResponse, status_code=status.HTTP_201_CREATED
)
async def create_folder(
    payload: FolderCreateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FolderResponse:
    folder = Folder(user_id=user.id, name=payload.name)
    session.add(folder)
    await session.commit()
    return _to_folder_response(folder)
