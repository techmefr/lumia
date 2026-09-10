from typing import Literal

from fastapi import APIRouter, Depends, Response, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api.technical.db import get_db_session
from api.technical.health.schemas import HealthResponse, ReadinessResponse
from config.redis import get_redis_config

router = APIRouter()

ServiceState = Literal["ok", "down"]


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Liveness: the process answers. Deliberately free of I/O.

    A liveness probe that touches the database restarts a healthy API whenever the database is
    briefly unavailable, which is the opposite of what it is for — that question is /ready's.
    """
    return HealthResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def get_readiness(
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> ReadinessResponse:
    """Readiness: the API can actually serve, so its two backing services have to answer."""
    database = await _probe_database(session)
    redis = await _probe_redis()
    if database == "down" or redis == "down":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(database=database, redis=redis)


async def _probe_database(session: AsyncSession) -> ServiceState:
    try:
        await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        return "down"
    return "ok"


async def _probe_redis() -> ServiceState:
    """Pings on a connection of its own rather than borrowing the queue's pool.

    That pool is a process-wide singleton bound to the loop that created it, and a probe has no
    business keeping it alive or being the first thing to open it.
    """
    client = Redis.from_url(get_redis_config().redis_url)
    try:
        await client.ping()
    except (RedisError, OSError):
        return "down"
    finally:
        await client.aclose()
    return "ok"
