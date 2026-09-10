class InvalidRefreshTokenError(Exception):
    pass


class InvalidMagicLinkTokenError(Exception):
    pass


class SsoNotConfiguredError(Exception):
    pass


class SsoSubjectMismatchError(Exception):
    pass
