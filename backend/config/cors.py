from functools import lru_cache

from pydantic_settings import BaseSettings


class CorsConfig(BaseSettings):
    # Comma-separated: the web SPA runs on a different origin (Vite dev server, or the
    # static build served by lumia-web) than the API, so the browser enforces CORS even
    # though every request carries its own bearer token rather than a cookie.
    cors_allowed_origins: str = (
        "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,http://127.0.0.1:5174"
    )

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_cors_config() -> CorsConfig:
    return CorsConfig()
