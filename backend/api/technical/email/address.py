from typing import Annotated

from pydantic import AfterValidator, EmailStr


def normalise_email(email: str) -> str:
    return email.strip().lower()


NormalizedEmail = Annotated[EmailStr, AfterValidator(normalise_email)]
