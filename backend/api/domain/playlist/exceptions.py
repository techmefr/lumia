class PlaylistNotFoundError(Exception):
    pass


class ArticleNotFoundError(Exception):
    pass


class BulkItemsFailedError(Exception):
    """Raised when a bulk change was rolled back, so the caller knows nothing was applied."""


class PlaylistForbiddenError(Exception):
    """The account sees the playlist but its role does not allow this change."""


class MemberUserNotFoundError(Exception):
    pass


class CannotShareWithOwnerError(Exception):
    pass


class MembershipNotFoundError(Exception):
    pass
