from collections.abc import Mapping

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.fever import key_service, sync_service
from api.domain.fever.schemas import FeverKeyCreatedResponse, FeverKeyStatusResponse
from api.domain.fever.sync_service import MarkState, MarkTarget
from api.domain.user.dependencies import get_current_user
from api.domain.user.models import User
from api.technical.db import get_db_session

router = APIRouter()

API_VERSION = 3

JsonObject = dict[str, object]


def _ids(csv: str | None) -> list[int]:
    return [int(part) for part in (csv or "").split(",") if part.strip().isdigit()]


def _joined(ids: list[int]) -> str:
    return ",".join(str(item) for item in ids)


def _int(value: str | None) -> int | None:
    return int(value) if value is not None and value.lstrip("-").isdigit() else None


async def _parameters(request: Request) -> Mapping[str, str]:
    """The query string and the form body merged: clients put the same arguments in either."""
    merged: dict[str, str] = dict(request.query_params)
    if request.method == "POST":
        form = await request.form()
        merged.update({name: value for name, value in form.items() if isinstance(value, str)})
    return merged


async def _apply_mark(session: AsyncSession, user: User, params: Mapping[str, str]) -> None:
    try:
        target = MarkTarget(params["mark"])
        state = MarkState(params["as"])
    except (KeyError, ValueError):
        return
    target_id = _int(params.get("id"))
    if target_id is None:
        return
    await sync_service.mark(
        session,
        user.id,
        target=target,
        state=state,
        target_id=target_id,
        before=_int(params.get("before")),
    )


@router.api_route("/fever/", methods=["GET", "POST"], name="fever")
@router.api_route("/fever", methods=["GET", "POST"], include_in_schema=False)
async def fever(request: Request, session: AsyncSession = Depends(get_db_session)) -> JsonObject:
    """The Fever sync endpoint third-party reader apps talk to.

    Failed authentication is a 200 with `auth: 0`, not a 401: that is what the protocol's clients
    look for, and several treat an HTTP error as a dead server rather than a wrong key.
    """
    params = await _parameters(request)
    user = await key_service.authenticate(session, params.get("api_key", ""))
    if user is None:
        return {"api_version": API_VERSION, "auth": 0}

    await _apply_mark(session, user, params)

    response: JsonObject = {
        "api_version": API_VERSION,
        "auth": 1,
        "last_refreshed_on_time": await sync_service.last_refreshed(session, user.id),
    }
    if "groups" in params:
        groups = await sync_service.list_groups(session, user.id)
        response["groups"] = [{"id": group.id, "title": group.title} for group in groups]
        response["feeds_groups"] = [
            {"group_id": group.id, "feed_ids": _joined(group.feed_ids)} for group in groups
        ]
    if "feeds" in params:
        feeds = await sync_service.list_feeds(session, user.id)
        response["feeds"] = [
            {
                "id": feed.id,
                "favicon_id": 0,
                "title": feed.title,
                "url": feed.url,
                "site_url": feed.url,
                "is_spark": 0,
                "last_updated_on_time": feed.last_updated_on_time,
            }
            for feed in feeds
        ]
        if "groups" not in params:
            groups = await sync_service.list_groups(session, user.id)
            response["feeds_groups"] = [
                {"group_id": group.id, "feed_ids": _joined(group.feed_ids)} for group in groups
            ]
    if "favicons" in params:
        response["favicons"] = []
    if "links" in params:
        response["links"] = []
    if "items" in params:
        with_ids = _ids(params["with_ids"]) if "with_ids" in params else None
        items = await sync_service.list_items(
            session,
            user.id,
            since_id=_int(params.get("since_id")),
            max_id=_int(params.get("max_id")),
            with_ids=with_ids,
        )
        response["total_items"] = await sync_service.count_items(session, user.id)
        response["items"] = [
            {
                "id": item.id,
                "feed_id": item.feed_id,
                "title": item.title,
                "author": item.author,
                "html": item.html,
                "url": item.url,
                "is_saved": int(item.is_saved),
                "is_read": int(item.is_read),
                "created_on_time": item.created_on_time,
            }
            for item in items
        ]
    if "unread_item_ids" in params:
        response["unread_item_ids"] = _joined(await sync_service.unread_item_ids(session, user.id))
    if "saved_item_ids" in params:
        response["saved_item_ids"] = _joined(await sync_service.saved_item_ids(session, user.id))
    return response


@router.get("/me/fever", response_model=FeverKeyStatusResponse)
async def read_fever_key(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FeverKeyStatusResponse:
    key = await key_service.get_key(session, user)
    return FeverKeyStatusResponse(
        enabled=key is not None, created_at=key.created_at if key else None
    )


@router.post(
    "/me/fever", response_model=FeverKeyCreatedResponse, status_code=status.HTTP_201_CREATED
)
async def create_fever_key(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> FeverKeyCreatedResponse:
    key, secret = await key_service.issue_key(session, user)
    return FeverKeyCreatedResponse(email=user.email, secret=secret, created_at=key.created_at)


@router.delete("/me/fever", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_fever_key(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    if await key_service.get_key(session, user) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    await key_service.revoke_key(session, user)
