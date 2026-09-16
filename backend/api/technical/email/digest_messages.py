from dataclasses import dataclass
from html import escape

from api.domain.user.models import DigestFrequency
from api.technical.email.messages import FALLBACK_LANGUAGE, EmailContent


@dataclass(frozen=True)
class DigestItem:
    """One article as the mail shows it, already reduced to what a reader needs to decide."""

    title: str
    url: str
    source: str
    summary: str | None


@dataclass(frozen=True)
class _DigestStrings:
    daily_subject: str
    weekly_subject: str
    intro: str
    settings_notice: str
    settings_link_label: str


# The reading interface covers ten locales; a mail that fell back to English for four of them
# would be the one place the product forgets which language the reader chose.
_DIGEST_STRINGS: dict[str, _DigestStrings] = {
    "en": _DigestStrings(
        daily_subject="Your Lumia daily digest",
        weekly_subject="Your Lumia weekly digest",
        intro="Here is what stands out in your unread articles.",
        settings_notice="You receive this digest because you asked for it.",
        settings_link_label="Change or stop the digest",
    ),
    "fr": _DigestStrings(
        daily_subject="Votre résumé Lumia du jour",
        weekly_subject="Votre résumé Lumia de la semaine",
        intro="Voici ce qui ressort de vos articles non lus.",
        settings_notice="Vous recevez ce résumé parce que vous l'avez demandé.",
        settings_link_label="Modifier ou arrêter le résumé",
    ),
    "es": _DigestStrings(
        daily_subject="Tu resumen diario de Lumia",
        weekly_subject="Tu resumen semanal de Lumia",
        intro="Esto es lo que destaca entre tus artículos sin leer.",
        settings_notice="Recibes este resumen porque lo solicitaste.",
        settings_link_label="Cambiar o detener el resumen",
    ),
    "de": _DigestStrings(
        daily_subject="Ihre tägliche Lumia-Übersicht",
        weekly_subject="Ihre wöchentliche Lumia-Übersicht",
        intro="Das fällt aus Ihren ungelesenen Artikeln heraus.",
        settings_notice="Sie erhalten diese Übersicht, weil Sie darum gebeten haben.",
        settings_link_label="Übersicht ändern oder beenden",
    ),
    "it": _DigestStrings(
        daily_subject="Il tuo riepilogo Lumia di oggi",
        weekly_subject="Il tuo riepilogo Lumia della settimana",
        intro="Ecco cosa spicca tra i tuoi articoli non letti.",
        settings_notice="Ricevi questo riepilogo perché lo hai richiesto.",
        settings_link_label="Modificare o interrompere il riepilogo",
    ),
    "pt": _DigestStrings(
        daily_subject="O seu resumo diário do Lumia",
        weekly_subject="O seu resumo semanal do Lumia",
        intro="Eis o que se destaca nos seus artigos por ler.",
        settings_notice="Recebe este resumo porque o pediu.",
        settings_link_label="Alterar ou parar o resumo",
    ),
    "ru": _DigestStrings(
        daily_subject="Ваш ежедневный дайджест Lumia",
        weekly_subject="Ваш еженедельный дайджест Lumia",
        intro="Вот что выделяется среди ваших непрочитанных статей.",
        settings_notice="Вы получаете этот дайджест, потому что сами его запросили.",
        settings_link_label="Изменить или отключить дайджест",
    ),
    "ar": _DigestStrings(
        daily_subject="ملخّصك اليومي من Lumia",
        weekly_subject="ملخّصك الأسبوعي من Lumia",
        intro="إليك أبرز ما في مقالاتك غير المقروءة.",
        settings_notice="تصلك هذه الرسالة لأنك طلبت الملخّص.",
        settings_link_label="تغيير الملخّص أو إيقافه",
    ),
    "zh": _DigestStrings(
        daily_subject="您的 Lumia 每日摘要",
        weekly_subject="您的 Lumia 每周摘要",
        intro="以下是您未读文章中值得一看的内容。",
        settings_notice="您收到此摘要，是因为您主动订阅了它。",
        settings_link_label="修改或停止摘要",
    ),
    "mg": _DigestStrings(
        daily_subject="Ny famintinana Lumia androany",
        weekly_subject="Ny famintinana Lumia amin'ity herinandro ity",
        intro="Ireto no miavaka amin'ireo lahatsoratra mbola tsy novakianao.",
        settings_notice="Mahazo ity famintinana ity ianao satria nangataka azy.",
        settings_link_label="Ovay na ajanony ny famintinana",
    ),
}


def render_digest_email(
    *,
    language: str,
    frequency: DigestFrequency,
    items: list[DigestItem],
    settings_url: str,
) -> EmailContent:
    """Builds both alternatives of the digest.

    No image is embedded and no url is rewritten, so there is nothing here that reports back when
    the mail is opened or when a link is followed: the reader's inbox is not a measurement surface.
    """
    strings = _DIGEST_STRINGS.get(language, _DIGEST_STRINGS[FALLBACK_LANGUAGE])
    subject = (
        strings.weekly_subject if frequency is DigestFrequency.WEEKLY else strings.daily_subject
    )
    return EmailContent(
        subject=subject,
        text_body=_text_body(strings, items, settings_url),
        html_body=_html_body(strings, items, settings_url),
    )


def _text_body(strings: _DigestStrings, items: list[DigestItem], settings_url: str) -> str:
    blocks = [strings.intro]
    for item in items:
        lines = [f"{item.title} — {item.source}"]
        if item.summary:
            lines.append(item.summary)
        lines.append(item.url)
        blocks.append("\n".join(lines))
    blocks.append(f"{strings.settings_notice}\n{strings.settings_link_label}: {settings_url}")
    return "\n\n".join(blocks)


def _html_body(strings: _DigestStrings, items: list[DigestItem], settings_url: str) -> str:
    safe_settings_url = escape(settings_url, quote=True)
    entries = []
    for item in items:
        summary = f"<p>{escape(item.summary)}</p>" if item.summary else ""
        entries.append(
            "<li>"
            f'<p><a href="{escape(item.url, quote=True)}">{escape(item.title)}</a></p>'
            f"<p>{escape(item.source)}</p>"
            f"{summary}"
            "</li>"
        )
    return (
        f"<p>{escape(strings.intro)}</p>"
        f"<ul>{''.join(entries)}</ul>"
        f"<p>{escape(strings.settings_notice)} "
        f'<a href="{safe_settings_url}">{escape(strings.settings_link_label)}</a></p>'
    )
