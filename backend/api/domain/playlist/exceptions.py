class PlaylistNotFoundError(Exception):
    pass


class ArticleNotFoundError(Exception):
    pass


class BulkItemsFailedError(Exception):
    """Raised when a bulk change was rolled back, so the caller knows nothing was applied."""
