class BulkFeedbackFailedError(Exception):
    """Raised when a bulk write was rolled back, so the caller knows nothing was applied."""
