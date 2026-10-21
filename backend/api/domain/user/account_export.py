from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from api.domain.article.models import Article, ArticleShare
from api.domain.feed.models import Feed, Folder
from api.domain.highlight.models import Highlight
from api.domain.playlist.models import Playlist
from api.domain.recommendation.models import UserArticleFeedback, UserFilterRule
from api.domain.user.models import User
from api.domain.user.schemas import (
    AccountExportResponse,
    ExportedAccount,
    ExportedArticle,
    ExportedFeed,
    ExportedFilterRule,
    ExportedHighlight,
    ExportedPlaylist,
    ExportedShare,
)


async def export_account(session: AsyncSession, user: User) -> AccountExportResponse:
    """Gathers everything the reader put into the app, in one readable document.

    Their own choices, not the app's derived state: the learned keyword and feed scores are
    Lumia's opinion about the reader, not data they entered, and an export of them would be
    unreadable noise. What leaves here is what would let them rebuild their setup elsewhere.
    """
    folders = {
        folder.id: folder.name
        for folder in await session.scalars(select(Folder).where(Folder.user_id == user.id))
    }
    feeds = list(await session.scalars(select(Feed).where(Feed.user_id == user.id)))
    rules = list(
        await session.scalars(select(UserFilterRule).where(UserFilterRule.user_id == user.id))
    )
    playlists = list(await session.scalars(select(Playlist).where(Playlist.user_id == user.id)))
    shares = list(
        await session.scalars(select(ArticleShare).where(ArticleShare.user_id == user.id))
    )
    highlights = list(
        await session.scalars(
            select(Highlight)
            .where(Highlight.user_id == user.id)
            .order_by(Highlight.created_at, Highlight.id)
        )
    )

    return AccountExportResponse(
        account=ExportedAccount(
            email=user.email,
            username=user.username,
            role=user.role,
            theme=user.theme,
            preferred_language=user.preferred_language,
            font_base_size=user.font_base_size,
            created_at=user.created_at,
        ),
        feeds=[
            ExportedFeed(
                title=feed.title,
                url=feed.url,
                source_type=feed.source_type,
                folder=folders.get(feed.folder_id) if feed.folder_id else None,
            )
            for feed in feeds
        ],
        filter_rules=[ExportedFilterRule(term=rule.term, mode=rule.mode) for rule in rules],
        playlists=[
            ExportedPlaylist(
                name=playlist.name,
                articles=[_exported_article(item.article) for item in playlist.items],
            )
            for playlist in playlists
        ],
        highlights=[
            ExportedHighlight(
                article_title=highlight.article.title,
                article_url=highlight.article.url,
                quote=highlight.quote,
                note=highlight.note,
                created_at=highlight.created_at,
            )
            for highlight in highlights
        ],
        saved=await _articles_where(session, user, UserArticleFeedback.saved),
        favorites=await _articles_where(session, user, UserArticleFeedback.favorite),
        shares=[
            ExportedShare(
                article_title=share.article.title,
                article_url=share.article.url,
                created_at=share.created_at,
            )
            for share in shares
        ],
    )


async def _articles_where(
    session: AsyncSession, user: User, flag: InstrumentedAttribute[bool]
) -> list[ExportedArticle]:
    articles = await session.scalars(
        select(Article)
        .join(UserArticleFeedback, UserArticleFeedback.article_id == Article.id)
        .where(UserArticleFeedback.user_id == user.id, flag.is_(True))
        .order_by(Article.published_at.desc())
    )
    return [_exported_article(article) for article in articles]


def _exported_article(article: Article) -> ExportedArticle:
    return ExportedArticle(
        title=article.title,
        url=article.url,
        published_at=article.published_at,
        source=article.feed.title,
    )
