import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from api.domain.article.routes import router as article_router
from api.domain.feed.routes import router as feed_router
from api.domain.instance.provisioning_service import provision_admin_from_env
from api.domain.instance.routes import router as instance_router
from api.domain.playlist.routes import router as playlist_router
from api.domain.recommendation.routes import router as recommendation_router
from api.domain.user.routes import router as user_router
from api.technical.db import get_db_session
from api.technical.health.routes import router as health_router
from api.technical.logging.middleware import REQUEST_ID_HEADER, CorrelationIdMiddleware
from api.technical.logging.setup import configure_logging
from config.cors import get_cors_config
from worker.technical.webhook import router as webhook_router

configure_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # A boot that cannot reach the schema still has to serve: the migrations are applied against a
    # running container, so refusing to start here would make them impossible to run at all.
    try:
        async for session in get_db_session():
            await provision_admin_from_env(session)
    except SQLAlchemyError:
        logger.warning(
            "could not provision the admin account from the environment; "
            "apply the migrations, then restart the api"
        )
    yield


app = FastAPI(title="Lumia", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_config().allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[REQUEST_ID_HEADER],
)
app.include_router(health_router)

# Added last so it wraps the CORS middleware: a preflight answer carries the id too.
app.add_middleware(CorrelationIdMiddleware)
app.include_router(user_router)
app.include_router(instance_router)
app.include_router(feed_router)
app.include_router(playlist_router)
app.include_router(recommendation_router)
app.include_router(article_router)
app.include_router(webhook_router)
