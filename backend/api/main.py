from fastapi import FastAPI

from api.domain.user.routes import router as user_router

app = FastAPI(title="Lumia")
app.include_router(user_router)
