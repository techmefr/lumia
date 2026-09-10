from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.instance.access_request_service import (
    approve_access_request,
    list_access_requests,
    reject_access_request,
    request_access,
)
from api.domain.instance.exceptions import (
    AccessRequestAlreadyDecidedError,
    AccessRequestNotFoundError,
    AccessRequestsClosedError,
    EmailAlreadyRegisteredError,
    InstanceNotProvisionedError,
    MaxAccountsBelowCurrentCountError,
)
from api.domain.instance.models import AccessRequest, AccessRequestStatus
from api.domain.instance.schemas import (
    AccessRequestCreateRequest,
    AccessRequestResponse,
    AccountUsageResponse,
    InstanceAccessModeResponse,
    InstanceSettingsResponse,
    InstanceSettingsUpdateRequest,
)
from api.domain.instance.settings_service import get_instance, update_instance_settings
from api.domain.instance.usage_service import list_account_usages
from api.domain.user.dependencies import require_admin
from api.domain.user.exceptions import InstanceFullError
from api.domain.user.invitation_service import count_accounts
from api.domain.user.models import Instance, User
from api.technical.db import get_db_session

router = APIRouter()


async def _require_instance(session: AsyncSession) -> Instance:
    try:
        return await get_instance(session)
    except InstanceNotProvisionedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette instance n'est pas encore initialisée",
        ) from exc


def _to_access_request_response(access_request: AccessRequest) -> AccessRequestResponse:
    return AccessRequestResponse(
        id=access_request.id,
        email=access_request.email,
        username=access_request.username,
        status=access_request.status,
        created_at=access_request.created_at,
        decided_at=access_request.decided_at,
    )


@router.get("/instance/access-mode", response_model=InstanceAccessModeResponse)
async def read_access_mode(
    session: AsyncSession = Depends(get_db_session),
) -> InstanceAccessModeResponse:
    instance = await _require_instance(session)
    return InstanceAccessModeResponse(access_mode=instance.access_mode)


@router.get("/instance/settings", response_model=InstanceSettingsResponse)
async def read_instance_settings(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> InstanceSettingsResponse:
    instance = await _require_instance(session)
    return InstanceSettingsResponse(
        max_accounts=instance.max_accounts,
        disk_quota_mb=instance.disk_quota_mb,
        access_mode=instance.access_mode,
        account_count=await count_accounts(session, instance.id),
    )


@router.patch("/instance/settings", response_model=InstanceSettingsResponse)
async def patch_instance_settings(
    payload: InstanceSettingsUpdateRequest,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> InstanceSettingsResponse:
    instance = await _require_instance(session)
    try:
        instance = await update_instance_settings(
            session,
            instance,
            max_accounts=payload.max_accounts,
            disk_quota_mb=payload.disk_quota_mb,
            access_mode=payload.access_mode,
        )
    except MaxAccountsBelowCurrentCountError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Le plafond demandé est inférieur au nombre de comptes existants",
        ) from exc
    return InstanceSettingsResponse(
        max_accounts=instance.max_accounts,
        disk_quota_mb=instance.disk_quota_mb,
        access_mode=instance.access_mode,
        account_count=await count_accounts(session, instance.id),
    )


@router.get("/instance/accounts", response_model=list[AccountUsageResponse])
async def read_accounts(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> list[AccountUsageResponse]:
    instance = await _require_instance(session)
    usages = await list_account_usages(session)
    return [
        AccountUsageResponse(
            id=usage.user_id,
            email=usage.email,
            username=usage.username,
            role=usage.role,
            used_mb=usage.used_mb,
            quota_mb=instance.disk_quota_mb,
        )
        for usage in usages
    ]


@router.post(
    "/access-requests",
    response_model=AccessRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_access_request(
    payload: AccessRequestCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> AccessRequestResponse:
    await _require_instance(session)
    try:
        access_request = await request_access(session, payload.email, payload.username)
    except AccessRequestsClosedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette instance n'accepte pas les demandes d'accès",
        ) from exc
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette adresse est déjà connue de l'instance",
        ) from exc
    return _to_access_request_response(access_request)


@router.get("/access-requests", response_model=list[AccessRequestResponse])
async def read_access_requests(
    request_status: AccessRequestStatus | None = None,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> list[AccessRequestResponse]:
    requests = await list_access_requests(session, request_status)
    return [_to_access_request_response(access_request) for access_request in requests]


@router.post("/access-requests/{request_id}/approve", status_code=status.HTTP_204_NO_CONTENT)
async def approve_request(
    request_id: UUID,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await approve_access_request(session, request_id, admin)
    except AccessRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except AccessRequestAlreadyDecidedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Cette demande a déjà été traitée"
        ) from exc
    except InstanceFullError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="L'instance a atteint son nombre maximum de comptes",
        ) from exc
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette adresse est déjà utilisée par un compte",
        ) from exc


@router.post("/access-requests/{request_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_request(
    request_id: UUID,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await reject_access_request(session, request_id, admin)
    except AccessRequestNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    except AccessRequestAlreadyDecidedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Cette demande a déjà été traitée"
        ) from exc
