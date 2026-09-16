from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from api.domain.feed.models import SourceType


class FolderCreateRequest(BaseModel):
    name: str


class FolderResponse(BaseModel):
    id: UUID
    name: str


class FeedCreateRequest(BaseModel):
    source_type: SourceType
    external_feed_id: str
    title: str
    url: str
    folder_id: UUID | None = None


class FeedAddByUrlRequest(BaseModel):
    url: str
    folder_id: UUID | None = None


class FolderUpdateRequest(BaseModel):
    name: str


#: Anything under five minutes hammers the publisher for no gain, and a fortnight is already
#: "practically never" — a reader wanting less should unsubscribe.
MIN_REFRESH_INTERVAL_MINUTES = 5
MAX_REFRESH_INTERVAL_MINUTES = 20160


class FeedUpdateRequest(BaseModel):
    """Every field is optional; folder_id=None explicitly unfiles the feed and
    refresh_interval_minutes=None hands the pace back to Miniflux, so the route has to distinguish
    'not sent' from 'sent as null' via model_fields_set."""

    title: str | None = None
    folder_id: UUID | None = None
    refresh_interval_minutes: int | None = Field(
        default=None, ge=MIN_REFRESH_INTERVAL_MINUTES, le=MAX_REFRESH_INTERVAL_MINUTES
    )


class UnreadCountsResponse(BaseModel):
    total: int
    feeds: dict[UUID, int]
    folders: dict[UUID, int]


class DiscoverSuggestionResponse(BaseModel):
    title: str
    url: str
    site_url: str
    description: str
    language: str
    topics: list[str]
    #: None when nothing is known about the reader yet, rather than a misleading 0.
    affinity: float | None


class InstanceFeedResponse(BaseModel):
    """A feed the Miniflux instance polls that the reader has no subscription to."""

    external_feed_id: str
    title: str
    url: str
    #: The Miniflux category, or None for a feed filed nowhere.
    category: str | None


class InstanceFeedAttachRequest(BaseModel):
    external_feed_ids: list[str]


class FeedResponse(BaseModel):
    id: UUID
    folder_id: UUID | None
    source_type: SourceType
    external_feed_id: str
    title: str
    url: str
    error_count: int
    #: A fixed category (e.g. "unreachable", "not_found"), never the provider's raw message.
    error_reason: str | None
    error_since: datetime | None
    #: None means the feed keeps whatever pace Miniflux picks for it.
    refresh_interval_minutes: int | None
    #: When a fetch was last asked for — not when articles last arrived, which happens later.
    last_refreshed_at: datetime | None


class FeedRefreshAllResponse(BaseModel):
    """The outcome of asking Miniflux to fetch everything.

    `feeds_requested` counts the feeds a refresh was asked for, deliberately not articles: the
    entries land over the webhook after this response is already sent, so no honest article count
    exists at this point.
    """

    feeds_requested: int
    requested_at: datetime
