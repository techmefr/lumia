from collections import defaultdict
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import ArticleKeyword, Keyword
from api.domain.tag.exceptions import TagNameTakenError, TagNotFoundError
from api.domain.tag.models import ArticleTag, Tag
from api.domain.tag.schemas import TagSuggestionResponse

KEYWORD_SUGGESTIONS = 3
USED_SUGGESTIONS = 5


def slugify(name: str) -> str:
    return name.casefold()


async def list_tags(session: AsyncSession, user_id: UUID) -> list[tuple[Tag, int]]:
    rows = await session.execute(
        select(Tag, func.count(ArticleTag.article_id))
        .outerjoin(ArticleTag, ArticleTag.tag_id == Tag.id)
        .where(Tag.user_id == user_id)
        .group_by(Tag.id)
        .order_by(func.lower(Tag.name))
    )
    return [(tag, count) for tag, count in rows.all()]


async def get_tag(session: AsyncSession, user_id: UUID, tag_id: UUID) -> Tag:
    tag = await session.scalar(select(Tag).where(Tag.id == tag_id, Tag.user_id == user_id))
    if tag is None:
        raise TagNotFoundError
    return tag


async def _find_by_name(session: AsyncSession, user_id: UUID, name: str) -> Tag | None:
    tag = await session.scalar(select(Tag).where(Tag.user_id == user_id, Tag.slug == slugify(name)))
    return tag


async def create_tag(session: AsyncSession, user_id: UUID, name: str) -> Tag:
    if await _find_by_name(session, user_id, name) is not None:
        raise TagNameTakenError
    tag = Tag(user_id=user_id, name=name, slug=slugify(name))
    session.add(tag)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise TagNameTakenError from exc
    return tag


async def rename_tag(session: AsyncSession, user_id: UUID, tag_id: UUID, name: str) -> Tag:
    tag = await get_tag(session, user_id, tag_id)
    clash = await _find_by_name(session, user_id, name)
    if clash is not None and clash.id != tag.id:
        raise TagNameTakenError
    tag.name = name
    tag.slug = slugify(name)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise TagNameTakenError from exc
    return tag


async def delete_tag(session: AsyncSession, user_id: UUID, tag_id: UUID) -> None:
    tag = await get_tag(session, user_id, tag_id)
    await session.execute(delete(ArticleTag).where(ArticleTag.tag_id == tag.id))
    await session.delete(tag)
    await session.commit()


async def count_articles(session: AsyncSession, tag_id: UUID) -> int:
    return (
        await session.scalar(
            select(func.count()).select_from(ArticleTag).where(ArticleTag.tag_id == tag_id)
        )
        or 0
    )


async def tags_for_articles(
    session: AsyncSession, user_id: UUID, article_ids: list[UUID]
) -> dict[UUID, list[Tag]]:
    if not article_ids:
        return {}
    rows = await session.execute(
        select(ArticleTag.article_id, Tag)
        .join(Tag, Tag.id == ArticleTag.tag_id)
        .where(ArticleTag.article_id.in_(article_ids), Tag.user_id == user_id)
        .order_by(func.lower(Tag.name))
    )
    grouped: dict[UUID, list[Tag]] = defaultdict(list)
    for article_id, tag in rows.all():
        grouped[article_id].append(tag)
    return grouped


async def attach_by_name(
    session: AsyncSession, user_id: UUID, article_id: UUID, name: str
) -> list[Tag]:
    """Tags an article, creating the tag on first use; idempotent for a tag it already carries."""
    tag = await _find_by_name(session, user_id, name)
    if tag is None:
        tag = await _create_or_find(session, user_id, name)
    if await session.get(ArticleTag, (article_id, tag.id)) is None:
        session.add(ArticleTag(article_id=article_id, tag_id=tag.id))
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
    return (await tags_for_articles(session, user_id, [article_id])).get(article_id, [])


async def _create_or_find(session: AsyncSession, user_id: UUID, name: str) -> Tag:
    tag = Tag(user_id=user_id, name=name, slug=slugify(name))
    try:
        async with session.begin_nested():
            session.add(tag)
    except IntegrityError:
        existing = await _find_by_name(session, user_id, name)
        if existing is None:
            raise
        return existing
    return tag


async def detach(session: AsyncSession, user_id: UUID, article_id: UUID, tag_id: UUID) -> list[Tag]:
    tag = await get_tag(session, user_id, tag_id)
    await session.execute(
        delete(ArticleTag).where(ArticleTag.article_id == article_id, ArticleTag.tag_id == tag.id)
    )
    await session.commit()
    return (await tags_for_articles(session, user_id, [article_id])).get(article_id, [])


def _without(names: list[str], excluded: set[str]) -> list[str]:
    return [name for name in names if slugify(name) not in excluded]


async def carried_slugs(session: AsyncSession, user_id: UUID, article_id: UUID) -> set[str]:
    tags = (await tags_for_articles(session, user_id, [article_id])).get(article_id, [])
    return {tag.slug for tag in tags}


async def suggest_tags(
    session: AsyncSession, user_id: UUID, article_id: UUID
) -> list[TagSuggestionResponse]:
    """Suggestions only: nothing here writes, the reader accepts or ignores each one.

    The article's own keywords come first because they are about this article; the reader's most
    used tags follow so an existing vocabulary gets reused instead of a near-duplicate coined.
    """
    carried = await carried_slugs(session, user_id, article_id)
    keyword_terms = list(
        await session.scalars(
            select(Keyword.term)
            .join(ArticleKeyword, ArticleKeyword.keyword_id == Keyword.id)
            .where(ArticleKeyword.article_id == article_id)
            .order_by(ArticleKeyword.weight.desc())
        )
    )
    suggestions = [
        TagSuggestionResponse(name=term, source="keyword")
        for term in _without(keyword_terms, carried)[:KEYWORD_SUGGESTIONS]
    ]
    taken = carried | {slugify(item.name) for item in suggestions}
    used = await session.scalars(
        select(Tag.name)
        .join(ArticleTag, ArticleTag.tag_id == Tag.id)
        .where(Tag.user_id == user_id)
        .group_by(Tag.id)
        .order_by(func.count().desc(), func.lower(Tag.name))
    )
    suggestions += [
        TagSuggestionResponse(name=name, source="used")
        for name in _without(list(used), taken)[:USED_SUGGESTIONS]
    ]
    return suggestions
