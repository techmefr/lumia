from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.domain.recommendation.models import FilterMode, UserFilterRule


async def list_rules(session: AsyncSession, user_id: UUID) -> list[UserFilterRule]:
    rows = await session.scalars(
        select(UserFilterRule)
        .where(UserFilterRule.user_id == user_id)
        .order_by(UserFilterRule.mode, UserFilterRule.term)
    )
    return list(rows)


async def add_rule(
    session: AsyncSession, user_id: UUID, *, term: str, mode: FilterMode
) -> UserFilterRule:
    """Idempotent: asking twice for the same term and mode returns the existing rule.

    Terms are normalised to lowercase here rather than at the matching site, so the uniqueness
    constraint actually prevents `Rust` and `rust` from coexisting.
    """
    normalised = term.strip().lower()
    existing = await session.scalar(
        select(UserFilterRule).where(
            UserFilterRule.user_id == user_id,
            UserFilterRule.term == normalised,
            UserFilterRule.mode == mode,
        )
    )
    if existing is not None:
        return existing

    rule = UserFilterRule(user_id=user_id, term=normalised, mode=mode)
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


async def delete_rule(session: AsyncSession, user_id: UUID, rule_id: UUID) -> bool:
    rule = await session.scalar(
        select(UserFilterRule).where(
            UserFilterRule.id == rule_id, UserFilterRule.user_id == user_id
        )
    )
    if rule is None:
        return False
    await session.delete(rule)
    await session.commit()
    return True
