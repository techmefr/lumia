from dataclasses import dataclass
from html import escape

# Transactional mail is the one place a reader sees the product without the translated interface
# around it, so an untranslated locale has to land on a real language rather than on a key.
FALLBACK_LANGUAGE = "en"


@dataclass(frozen=True)
class EmailContent:
    subject: str
    text_body: str
    html_body: str


@dataclass(frozen=True)
class _MagicLinkStrings:
    subject: str
    intro: str
    call_to_action: str
    ignore_notice: str


_MAGIC_LINK_STRINGS: dict[str, _MagicLinkStrings] = {
    "en": _MagicLinkStrings(
        subject="Your Lumia sign-in link",
        intro="Use the link below to sign in to Lumia.",
        call_to_action="Sign in to Lumia",
        ignore_notice="If you did not ask to sign in, you can ignore this message.",
    ),
    "fr": _MagicLinkStrings(
        subject="Votre lien de connexion Lumia",
        intro="Cliquez sur le lien ci-dessous pour vous connecter à Lumia.",
        call_to_action="Se connecter à Lumia",
        ignore_notice="Si vous n'avez pas demandé à vous connecter, ignorez ce message.",
    ),
    "es": _MagicLinkStrings(
        subject="Tu enlace de acceso a Lumia",
        intro="Usa el siguiente enlace para acceder a Lumia.",
        call_to_action="Acceder a Lumia",
        ignore_notice="Si no has solicitado acceder, puedes ignorar este mensaje.",
    ),
    "de": _MagicLinkStrings(
        subject="Ihr Lumia-Anmeldelink",
        intro="Melden Sie sich über den folgenden Link bei Lumia an.",
        call_to_action="Bei Lumia anmelden",
        ignore_notice=(
            "Wenn Sie keine Anmeldung angefordert haben, können Sie diese Nachricht ignorieren."
        ),
    ),
    "it": _MagicLinkStrings(
        subject="Il tuo link di accesso a Lumia",
        intro="Usa il link qui sotto per accedere a Lumia.",
        call_to_action="Accedi a Lumia",
        ignore_notice="Se non hai richiesto l'accesso, puoi ignorare questo messaggio.",
    ),
    "pt": _MagicLinkStrings(
        subject="O seu link de acesso ao Lumia",
        intro="Utilize o link abaixo para entrar no Lumia.",
        call_to_action="Entrar no Lumia",
        ignore_notice="Se não pediu para entrar, pode ignorar esta mensagem.",
    ),
}


_PASSWORD_RESET_STRINGS: dict[str, _MagicLinkStrings] = {
    "en": _MagicLinkStrings(
        subject="Reset your Lumia password",
        intro="Use the link below to choose a new Lumia password.",
        call_to_action="Choose a new password",
        ignore_notice=(
            "If you did not ask to change your password, you can ignore this message: "
            "it stays unchanged."
        ),
    ),
    "fr": _MagicLinkStrings(
        subject="Réinitialiser votre mot de passe Lumia",
        intro="Cliquez sur le lien ci-dessous pour choisir un nouveau mot de passe Lumia.",
        call_to_action="Choisir un nouveau mot de passe",
        ignore_notice=(
            "Si vous n'avez pas demandé à changer de mot de passe, ignorez ce message : "
            "le vôtre reste inchangé."
        ),
    ),
    "es": _MagicLinkStrings(
        subject="Restablece tu contraseña de Lumia",
        intro="Usa el siguiente enlace para elegir una nueva contraseña de Lumia.",
        call_to_action="Elegir una nueva contraseña",
        ignore_notice=(
            "Si no has solicitado cambiar tu contraseña, puedes ignorar este mensaje: "
            "la tuya no cambia."
        ),
    ),
    "de": _MagicLinkStrings(
        subject="Ihr Lumia-Passwort zurücksetzen",
        intro="Wählen Sie über den folgenden Link ein neues Lumia-Passwort.",
        call_to_action="Neues Passwort wählen",
        ignore_notice=(
            "Wenn Sie keine Passwortänderung angefordert haben, können Sie diese Nachricht "
            "ignorieren: Ihr Passwort bleibt unverändert."
        ),
    ),
    "it": _MagicLinkStrings(
        subject="Reimposta la tua password Lumia",
        intro="Usa il link qui sotto per scegliere una nuova password Lumia.",
        call_to_action="Scegli una nuova password",
        ignore_notice=(
            "Se non hai richiesto di cambiare la password, puoi ignorare questo messaggio: "
            "la tua resta invariata."
        ),
    ),
    "pt": _MagicLinkStrings(
        subject="Redefinir a sua palavra-passe do Lumia",
        intro="Utilize o link abaixo para escolher uma nova palavra-passe do Lumia.",
        call_to_action="Escolher uma nova palavra-passe",
        ignore_notice=(
            "Se não pediu para alterar a sua palavra-passe, pode ignorar esta mensagem: "
            "a sua permanece inalterada."
        ),
    ),
}


def render_magic_link_email(
    *, language: str, magic_link_url: str, password_reset: bool = False
) -> EmailContent:
    catalogue = _PASSWORD_RESET_STRINGS if password_reset else _MAGIC_LINK_STRINGS
    strings = catalogue.get(language, catalogue[FALLBACK_LANGUAGE])
    safe_url = escape(magic_link_url, quote=True)
    return EmailContent(
        subject=strings.subject,
        # The raw url stays on its own line: mail clients that show only the text part have to
        # leave the reader something selectable.
        text_body=f"{strings.intro}\n\n{magic_link_url}\n\n{strings.ignore_notice}",
        html_body=(
            f"<p>{escape(strings.intro)}</p>"
            f'<p><a href="{safe_url}">{escape(strings.call_to_action)}</a></p>'
            f"<p>{safe_url}</p>"
            f"<p>{escape(strings.ignore_notice)}</p>"
        ),
    )
