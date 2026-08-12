from fastapi import FastAPI

from api.domain.feed.routes import router as feed_router
from api.domain.user.routes import router as user_router

app = FastAPI(title="Lumia")
app.include_router(user_router)
app.include_router(feed_router)
