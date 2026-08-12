from fastapi import FastAPI

from api.main import app


def test_app_is_a_fastapi_instance() -> None:
    assert isinstance(app, FastAPI)
