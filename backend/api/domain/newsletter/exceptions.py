class UnknownInboxError(Exception):
    """No live inbox answers to this token: unknown and revoked look alike."""


class EmptyMessageError(Exception):
    """The message carries neither an HTML nor a text body, so there is nothing to read."""
