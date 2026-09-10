class InstanceNotProvisionedError(Exception):
    pass


class InstanceFullError(Exception):
    pass


class MaxAccountsBelowCurrentCountError(Exception):
    pass


class EmailAlreadyRegisteredError(Exception):
    pass


class AccessRequestNotFoundError(Exception):
    pass


class AccessRequestAlreadyDecidedError(Exception):
    pass


class AccessRequestsClosedError(Exception):
    pass


class AccountQuotaExceededError(Exception):
    """The account already stores as much as its instance allows it to."""

    def __init__(self, used_mb: int, quota_mb: int) -> None:
        super().__init__(f"account storage {used_mb} MB reached the {quota_mb} MB quota")
        self.used_mb = used_mb
        self.quota_mb = quota_mb
