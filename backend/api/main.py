from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.domain.article.routes import router as article_router
from api.domain.feed.routes import router as feed_router
from api.domain.playlist.routes import router as playlist_router
from api.domain.recommendation.routes import router as recommendation_router
from api.domain.user.routes import router as user_router
from api.technical.health.routes import router as health_router
from config.cors import get_cors_config
from worker.technical.webhook import router as webhook_router

app = FastAPI(title="Lumia")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_config().allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(user_router)
app.include_router(feed_router)
app.include_router(playlist_router)
app.include_router(recommendation_router)
app.include_router(article_router)
app.include_router(webhook_router)
