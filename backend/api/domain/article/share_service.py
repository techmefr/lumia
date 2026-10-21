from uuid import UUID

import nh3
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article, ArticleShare
from api.domain.user.models import User
from api.technical.auth.tokens import generate_opaque_token, hash_token


class PublicSharingDisabledError(Exception):
    """The instance admin has not allowed links that anyone can open."""


async def active_share(session: AsyncSession, user: User, article_id: UUID) -> ArticleShare | None:
    shares = await session.scalars(
        select(ArticleShare)
        .where(ArticleShare.user_id == user.id, ArticleShare.article_id == article_id)
        .order_by(ArticleShare.created_at.desc())
    )
    return shares.first()


async def create_share(
    session: AsyncSession, user: User, article: Article, *, sharing_enabled: bool
) -> tuple[ArticleShare, str]:
    """Issues a fresh link for the article, retiring the one it had.

    One live link per article: the old token is unrecoverable (only its hash is kept), so a reader
    who lost it asks for a new one, and the one that may have leaked stops working.
    """
    if not sharing_enabled:
        raise PublicSharingDisabledError
    await revoke_shares(session, user, article.id)
    raw_token = generate_opaque_token()
    share = ArticleShare(user_id=user.id, article_id=article.id, token_hash=hash_token(raw_token))
    session.add(share)
    await session.commit()
    return share, raw_token


async def revoke_shares(session: AsyncSession, user: User, article_id: UUID) -> None:
    await session.execute(
        delete(ArticleShare).where(
            ArticleShare.user_id == user.id, ArticleShare.article_id == article_id
        )
    )
    await session.commit()


async def find_shared_article(session: AsyncSession, raw_token: str) -> Article | None:
    """The article a token opens, or nothing: an unknown token and a revoked one look alike."""
    articles = await session.scalars(
        select(Article)
        .join(ArticleShare, ArticleShare.article_id == Article.id)
        .where(ArticleShare.token_hash == hash_token(raw_token))
    )
    return articles.first()


def sanitize_shared_html(html: str) -> str:
    """Strips everything active from the stored body before it leaves the instance.

    The reader's own screen sanitizes in the browser; a public page is also read by clients that
    do not, so the server does it first. `nh3` drops scripts, event handlers, forms and
    `javascript:` urls by construction, and the anchors are forced to open without a referrer.
    """
    return nh3.clean(html, link_rel="noopener noreferrer nofollow")
