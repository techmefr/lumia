class InvalidRefreshTokenError(Exception):
    pass


class InvalidMagicLinkTokenError(Exception):
    pass


class SsoNotConfiguredError(Exception):
    pass


class InvalidInvitationError(Exception):
    pass


class InstanceFullError(Exception):
    pass


class EmailAlreadyTakenError(Exception):
    pass
