"""The text of every email SEWE sends, in English, French and Spanish.

Kept apart from the sender so the wording can change without touching the
delivery code. Plain text only for now: short, readable everywhere, and
nothing for a spam filter to dislike.
"""

_VERIFY = {
    "en": (
        "Your SEWE Finance code: {code}",
        "Your SEWE Finance verification code is {code}.\n\n"
        "It expires in 10 minutes. If you didn't sign up, ignore this email.",
    ),
    "fr": (
        "Votre code SEWE Finance : {code}",
        "Votre code de vérification SEWE Finance est {code}.\n\n"
        "Il expire dans 10 minutes. Si vous ne vous êtes pas inscrit, ignorez ce message.",
    ),
    "es": (
        "Tu código de SEWE Finance: {code}",
        "Tu código de verificación de SEWE Finance es {code}.\n\n"
        "Caduca en 10 minutos. Si no te registraste, ignora este correo.",
    ),
}


def verification_email(code: str, language: str) -> tuple[str, str]:
    subject, body = _VERIFY.get(language, _VERIFY["en"])
    return subject.format(code=code), body.format(code=code)
