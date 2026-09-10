import logging
from dataclasses import replace
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.article.models import Article, ArticleKeyword, Author, Category, Keyword, Lang
from api.domain.feed.models import Feed, SourceType
from api.domain.user.models import ReadingLang, User
from api.domain.user.providers import chat_client_for, translator_for
from worker.domain.extraction.stemming_en import stem_en
from worker.domain.extraction.stemming_fr import stem_fr
from worker.domain.extraction.tfidf import extract_keywords
from worker.domain.summarizer.extractive import summarize_extractive
from worker.technical.ai.base import LlmApiError, Summarizer
from worker.technical.connectors.base import RawArticle
from worker.technical.content_extraction import ContentExtractor, TrafilaturaContentExtractor
from worker.technical.db import worker_session
from worker.technical.html import extract_first_image, strip_html
from worker.technical.lang_detect import detect_lang
from worker.technical.translation.base import TranslationApiError, Translator

logger = logging.getLogger(__name__)


async def enrich_article(
    _ctx: dict[str, Any],
    raw_article: RawArticle,
    *,
    translator: Translator | None = None,
    content_extractor: ContentExtractor | None = None,
) -> None:
    content_extractor = content_extractor or TrafilaturaContentExtractor()
    clean_content = await content_extractor.extract(raw_article.url, raw_article.content)
    raw_article = replace(raw_article, content=clean_content)
    plain_text = strip_html(raw_article.content)
    image_url = extract_first_image(raw_article.content)
    lang = Lang.FR if detect_lang(plain_text) == "fr" else Lang.EN
    stems = stem_fr(plain_text) if lang == Lang.FR else stem_en(plain_text)
    keywords = extract_keywords(stems)
    translated_cache: dict[ReadingLang, tuple[str, str]] = {}

    async with worker_session() as session:
        author = await _get_or_create_author(session, raw_article.author_name)
        category = await _get_or_create_category(session, raw_article.category_name)

        feeds = await session.scalars(
            select(Feed).where(
                Feed.source_type == SourceType(raw_article.source_type),
                Feed.external_feed_id == raw_article.feed_external_id,
            )
        )
        for feed in feeds:
            user = await session.get(User, feed.user_id)
            target_lang = user.preferred_language if user is not None else ReadingLang(lang.value)
            title, content, summary_source = await _localize(
                raw_article,
                plain_text,
                lang,
                target_lang,
                translator if translator is not None else translator_for(user),
                translated_cache,
            )
            await _create_article_if_new(
                session,
                feed=feed,
                raw_article=raw_article,
                author=author,
                category=category,
                title=title,
                content=content,
                summary=await _summarize(summary_source, chat_client_for(user)),
                image_url=image_url,
                keywords=keywords,
                original_lang=lang,
                keyword_lang=lang,
            )

        await session.commit()


async def _summarize(text: str, summarizer: Summarizer | None) -> str:
    if summarizer is None:
        return summarize_extractive(text)
    try:
        summary = await summarizer.summarize(text)
    except (LlmApiError, httpx.HTTPError) as exc:
        # A dead provider or a rejected key must not cost the article its summary.
        logger.warning("llm summary failed, falling back to the extractive one: %s", exc)
        return summarize_extractive(text)
    return summary.strip() or summarize_extractive(text)


async def _localize(
    raw_article: RawArticle,
    plain_text: str,
    detected_lang: Lang,
    target_lang: ReadingLang,
    translator: Translator | None,
    translated_cache: dict[ReadingLang, tuple[str, str]],
) -> tuple[str, str, str]:
    # Compared on the code rather than the enum: the two are different types on purpose, one being
    # the language an article is in and the other one a reader's target.
    if (
        target_lang.value == detected_lang.value
        or translator is None
        or not translator.supports(target_lang.value)
    ):
        return raw_article.title, raw_article.content, plain_text
    if target_lang not in translated_cache:
        try:
            translated_title = await translator.translate(
                raw_article.title, target_lang=target_lang.value
            )
            translated_content = await translator.translate(
                plain_text, target_lang=target_lang.value
            )
        except (TranslationApiError, httpx.HTTPError) as exc:
            # A rejected key or a dead provider costs the translation, never the article.
            logger.warning("translation failed, keeping the original text: %s", exc)
            return raw_article.title, raw_article.content, plain_text
        translated_cache[target_lang] = (translated_title, translated_content)
    translated_title, translated_content = translated_cache[target_lang]
    return translated_title, translated_content, translated_content


async def _create_article_if_new(
    session: AsyncSession,
    *,
    feed: Feed,
    raw_article: RawArticle,
    author: Author | None,
    category: Category | None,
    title: str,
    content: str,
    summary: str,
    image_url: str | None,
    keywords: list[tuple[str, float]],
    original_lang: Lang,
    keyword_lang: Lang,
) -> None:
    existing = await session.scalar(
        select(Article).where(
            Article.feed_id == feed.id,
            Article.external_entry_id == raw_article.external_entry_id,
        )
    )
    if existing is not None:
        return

    article = Article(
        feed_id=feed.id,
        author_id=author.id if author else None,
        category_id=category.id if category else None,
        external_entry_id=raw_article.external_entry_id,
        title=title,
        url=raw_article.url,
        content=content,
        summary=summary,
        image_url=image_url,
        original_lang=original_lang,
        published_at=raw_article.published_at,
    )
    session.add(article)
    await session.flush()

    for term, weight in keywords:
        keyword = await _get_or_create_keyword(session, term, keyword_lang)
        session.add(ArticleKeyword(article_id=article.id, keyword_id=keyword.id, weight=weight))


async def _get_or_create_author(session: AsyncSession, name: str | None) -> Author | None:
    if not name:
        return None
    author = await session.scalar(select(Author).where(Author.name == name))
    if author is None:
        author = Author(name=name)
        session.add(author)
        await session.flush()
    return author


async def _get_or_create_category(session: AsyncSession, name: str | None) -> Category | None:
    if not name:
        return None
    category = await session.scalar(select(Category).where(Category.name == name))
    if category is None:
        category = Category(name=name)
        session.add(category)
        await session.flush()
    return category


async def _get_or_create_keyword(session: AsyncSession, term: str, lang: Lang) -> Keyword:
    keyword = await session.scalar(
        select(Keyword).where(Keyword.term == term, Keyword.lang == lang)
    )
    if keyword is None:
        keyword = Keyword(term=term, lang=lang)
        session.add(keyword)
        await session.flush()
    return keyword
