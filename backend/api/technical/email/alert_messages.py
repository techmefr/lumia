from dataclasses import dataclass
from html import escape

from api.technical.email.messages import FALLBACK_LANGUAGE, EmailContent


@dataclass(frozen=True)
class _AlertStrings:
    subject: str
    intro: str
    settings_notice: str
    settings_link_label: str


# Same ten locales as the digest: a keyword alert is the digest's per-search sibling, and a mail
# that only speaks eight of the reader's ten interface languages would be a visible regression.
_ALERT_STRINGS: dict[str, _AlertStrings] = {
    "en": _AlertStrings(
        subject='New match for "{name}"',
        intro='A new article matches your saved search "{name}".',
        settings_notice="You receive this alert because you turned it on for this search.",
        settings_link_label="Manage your saved searches",
    ),
    "fr": _AlertStrings(
        subject='Nouveau résultat pour « {name} »',
        intro='Un nouvel article correspond à votre recherche enregistrée « {name} ».',
        settings_notice="Vous recevez cette alerte car vous l'avez activée pour cette recherche.",
        settings_link_label="Gérer vos recherches enregistrées",
    ),
    "es": _AlertStrings(
        subject='Nuevo resultado para "{name}"',
        intro='Un nuevo artículo coincide con tu búsqueda guardada "{name}".',
        settings_notice="Recibes esta alerta porque la activaste para esta búsqueda.",
        settings_link_label="Gestionar tus búsquedas guardadas",
    ),
    "de": _AlertStrings(
        subject='Neuer Treffer für „{name}“',
        intro='Ein neuer Artikel passt zu Ihrer gespeicherten Suche „{name}“.',
        settings_notice="Sie erhalten diese Meldung, weil Sie sie für diese Suche aktiviert haben.",
        settings_link_label="Gespeicherte Suchen verwalten",
    ),
    "it": _AlertStrings(
        subject='Nuovo risultato per "{name}"',
        intro='Un nuovo articolo corrisponde alla tua ricerca salvata "{name}".',
        settings_notice="Ricevi questo avviso perché lo hai attivato per questa ricerca.",
        settings_link_label="Gestisci le tue ricerche salvate",
    ),
    "pt": _AlertStrings(
        subject='Novo resultado para "{name}"',
        intro='Um novo artigo corresponde à sua pesquisa guardada "{name}".',
        settings_notice="Recebe este alerta porque o ativou para esta pesquisa.",
        settings_link_label="Gerir as suas pesquisas guardadas",
    ),
    "ru": _AlertStrings(
        subject='Новое совпадение для «{name}»',
        intro='Новая статья соответствует вашему сохранённому поиску «{name}».',
        settings_notice="Вы получаете это уведомление, так как включили его для этого поиска.",
        settings_link_label="Управление сохранёнными поисками",
    ),
    "ar": _AlertStrings(
        subject='نتيجة جديدة لـ "{name}"',
        intro='توجد مقالة جديدة تطابق بحثك المحفوظ "{name}".',
        settings_notice="تصلك هذه التنبيهات لأنك فعّلتها لهذا البحث.",
        settings_link_label="إدارة عمليات البحث المحفوظة",
    ),
    "zh": _AlertStrings(
        subject='"{name}" 有新的匹配结果',
        intro='有一篇新文章匹配您保存的搜索 "{name}"。',
        settings_notice="您收到此提醒，是因为您为该搜索开启了提醒功能。",
        settings_link_label="管理已保存的搜索",
    ),
    "mg": _AlertStrings(
        subject='Valiny vaovao ho an\'ny "{name}"',
        intro='Misy lahatsoratra vaovao mifanaraka amin\'ny fikarohana voatahiry "{name}".',
        settings_notice="Mahazo ity fampandrenesana ity ianao satria nasianao izany io fikarohana io.",
        settings_link_label="Hitantana ny fikarohana voatahiry",
    ),
}


def render_alert_email(
    *,
    language: str,
    saved_search_name: str,
    title: str,
    url: str,
    source: str,
    summary: str | None,
    settings_url: str,
) -> EmailContent:
    """One article, one saved search, one mail: an alert fires the moment ingestion finds a match,
    so there is never more than a single item to report."""
    strings = _ALERT_STRINGS.get(language, _ALERT_STRINGS[FALLBACK_LANGUAGE])
    subject = strings.subject.format(name=saved_search_name)
    intro = strings.intro.format(name=saved_search_name)
    return EmailContent(
        subject=subject,
        text_body=_text_body(intro, strings, title, url, source, summary, settings_url),
        html_body=_html_body(intro, strings, title, url, source, summary, settings_url),
    )


def _text_body(
    intro: str,
    strings: _AlertStrings,
    title: str,
    url: str,
    source: str,
    summary: str | None,
    settings_url: str,
) -> str:
    lines = [f"{title} — {source}"]
    if summary:
        lines.append(summary)
    lines.append(url)
    return "\n\n".join(
        [intro, "\n".join(lines), f"{strings.settings_notice}\n{strings.settings_link_label}: {settings_url}"]
    )


def _html_body(
    intro: str,
    strings: _AlertStrings,
    title: str,
    url: str,
    source: str,
    summary: str | None,
    settings_url: str,
) -> str:
    safe_settings_url = escape(settings_url, quote=True)
    summary_html = f"<p>{escape(summary)}</p>" if summary else ""
    return (
        f"<p>{escape(intro)}</p>"
        "<ul><li>"
        f'<p><a href="{escape(url, quote=True)}">{escape(title)}</a></p>'
        f"<p>{escape(source)}</p>"
        f"{summary_html}"
        "</li></ul>"
        f"<p>{escape(strings.settings_notice)} "
        f'<a href="{safe_settings_url}">{escape(strings.settings_link_label)}</a></p>'
    )
