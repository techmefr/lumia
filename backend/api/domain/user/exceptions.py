class InvalidRefreshTokenError(Exception):
    pass


class InvalidMagicLinkTokenError(Exception):
    pass


class SsoNotConfiguredError(Exception):
    pass


class InvalidSsoLoginAttemptError(Exception):
    pass


class InvalidInvitationError(Exception):
    pass


class InstanceFullError(Exception):
    pass


class EmailAlreadyTakenError(Exception):
    pass
