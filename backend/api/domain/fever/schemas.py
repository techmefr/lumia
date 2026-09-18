from pydantic import BaseModel


class FeverApiKeyResponse(BaseModel):
    """The key is shown once, at issuance: Lumia never stores it, only its md5 digest."""

    api_key: str
    email: str


class FeverApiKeyStatusResponse(BaseModel):
    configured: bool
