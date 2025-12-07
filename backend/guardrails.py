# =========================
# ✅ GUARDRail SYSTEM (NO REGEX)
# =========================

SENSITIVE_KEYWORDS = {
    "child abuse",
    "sexual abuse",
    "rape",
    "molest",
    "porn",
    "nude",
    "suicide",
    "self harm",
    "kill",
    "murder",
    "terror",
    "bomb",
    "drugs",
    "weapon",
    "gun",
    "sex",
    "violence",
}


def violates_guardrails(message: str) -> bool:
    """
    Returns True if the message contains any blocked keyword.
    No regex used. Pure keyword scanning.
    """
    msg = message.lower()

    for keyword in SENSITIVE_KEYWORDS:
        if keyword in msg:
            return True

    return False


def guardrail_response() -> str:
    return (
        "⚠️ I’m designed only for **travel assistance**, including:\n"
        "- Trip planning\n"
        "- Live weather\n"
        "- Routes & transport\n"
        "- Festivals & tourism safety\n\n"
        "I can’t help with sensitive, harmful, or unsafe topics.\n\n"
        "If you or someone is in danger, please contact **local emergency services** or a "
        "**trusted professional immediately**.\n\n"
        "You can ask me about destinations, itineraries, routes, or current travel conditions anytime."
    )
