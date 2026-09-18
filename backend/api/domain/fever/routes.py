from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.fever.key_service import (
    has_api_key,
    issue_api_key,
    resolve_user_by_api_key,
    revoke_api_key,
)
from api.domain.fever.schemas import FeverApiKeyResponse, FeverApiKeyStatusResponse
from api.domain.fever.wire_service import (
    apply_mark,
    build_feeds_payload,
    build_groups_payload,
    build_items_payload,
    build_saved_item_ids_payload,
    build_unread_item_ids_payload,
)
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session

FEVER_API_VERSION = 3

router = APIRouter()


@router.post("/fever/api-key", response_model=FeverApiKeyResponse)
async def create_fever_api_key(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FeverApiKeyResponse:
    api_key = await issue_api_key(session, user)
    return FeverApiKeyResponse(api_key=api_key, email=user.email)


@router.get("/fever/api-key", response_model=FeverApiKeyStatusResponse)
async def get_fever_api_key_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FeverApiKeyStatusResponse:
    return FeverApiKeyStatusResponse(configured=await has_api_key(session, user))


@router.delete("/fever/api-key", status_code=204)
async def delete_fever_api_key(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await revoke_api_key(session, user)


@router.post("/fever/")
async def fever_endpoint(
    request: Request,
    api_key: str = Form(default=""),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """The single Fever endpoint: everything is driven by query params and form fields, per the
    protocol every thin Fever client already speaks."""
    user = await resolve_user_by_api_key(session, api_key)
    if user is None:
        return JSONResponse({"api_version": FEVER_API_VERSION, "auth": 0})

    payload: dict[str, Any] = {"api_version": FEVER_API_VERSION, "auth": 1}
    query = request.query_params

    if "groups" in query:
        payload.update(await build_groups_payload(session, user))
    if "feeds" in query:
        payload.update(await build_feeds_payload(session, user))
    if "unread_item_ids" in query:
        payload.update(await build_unread_item_ids_payload(session, user))
    if "saved_item_ids" in query:
        payload.update(await build_saved_item_ids_payload(session, user))
    if "items" in query:
        form = await request.form()
        payload.update(
            await build_items_payload(
                session,
                user,
                since_id=_as_int(query.get("since_id")),
                max_id=_as_int(query.get("max_id")),
                with_ids=query.get("with_ids") or _as_str(form.get("with_ids")),
            )
        )

    form = await request.form()
    mark_type = _as_str(form.get("mark"))
    mark_as = _as_str(form.get("as"))
    mark_id = _as_int(form.get("id"))
    if mark_type is not None and mark_as is not None and mark_id is not None:
        await apply_mark(session, user, mark_type=mark_type, mark_as=mark_as, item_id=mark_id)

    return JSONResponse(payload)


def _as_int(raw: object) -> int | None:
    if raw is None:
        return None
    text = raw if isinstance(raw, str) else None
    if text is None or not text.strip().lstrip("-").isdigit():
        return None
    return int(text)


def _as_str(raw: object) -> str | None:
    return raw if isinstance(raw, str) and raw != "" else None
