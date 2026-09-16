class InvalidRefreshTokenError(Exception):
    pass


class InvalidMagicLinkTokenError(Exception):
    pass


class InvalidCurrentPasswordError(Exception):
    pass


class TotpRequiredError(Exception):
    """The account has a second factor and the request carried none."""


class InvalidTotpCodeError(Exception):
    pass


class TotpNotEnrolledError(Exception):
    pass


class TotpAlreadyEnabledError(Exception):
    pass


class SsoNotConfiguredError(Exception):
    pass


class SsoSubjectMismatchError(Exception):
    pass


class InvalidSsoLoginAttemptError(Exception):
    pass


class InvalidInvitationError(Exception):
    pass


class InstanceFullError(Exception):
    pass


class EmailAlreadyTakenError(Exception):
    pass


class LastAdminError(Exception):
    pass
