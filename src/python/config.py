"Loads environment variables and applies type-safe parsing"

import os
from datetime import timedelta
from typing import Callable, Any
from dotenv import load_dotenv

load_dotenv()


def get_env(
    key: str,
    default: Any = None,
    cast: Callable[[str], Any] = str,
    strip_quotes: bool = True,
) -> Any:
    """Helper to safely fetch and cast environment variables."""
    val = os.getenv(key, default)
    if val is None:
        return default
    if strip_quotes and isinstance(val, str):
        val = val.strip('"').strip("'")
    try:
        return cast(val)
    except (ValueError, TypeError):
        return default


def get_bool(key: str, default: bool = False) -> bool:
    """Helper to parse booleans consistently."""
    val = os.getenv(key, str(default))
    val = val.strip('"').strip("'").lower()
    return val in ("true", "1", "t", "yes", "y")


def _normalize_samesite(value: Any) -> str | None:
    """Normalize SameSite strings to Flask-compatible values."""

    if value is None:
        return None

    normalized = str(value).strip().strip('"').strip("'").lower()

    if not normalized:
        return None

    if normalized == "none":
        return "None"

    if normalized == "lax":
        return "Lax"

    if normalized == "strict":
        return "Strict"

    # Fall back to Flask's default when an unsupported value is provided
    return "Lax"


admin_password_hash = get_env("admin_password_hash")
secret_key = get_env("secret_key")
if not admin_password_hash or not secret_key:
    raise ValueError(
        "error: admin_password_hash and secret_key must be set in the .env"
    )
debug = get_bool("flask_debug", False)
app_version = get_env("app_version", "1.0.0")
permanent_session_lifetime = timedelta(
    days=get_env("permanent_session_lifetime_days", 7, cast=int)
)

mail_configuration = {
    "Server": get_env("mail_server"),
    "Port": get_env("mail_port", 587, cast=int),
    "Username": get_env("mail_username"),
    "Password": get_env("mail_password"),
    "UseTLS": get_bool("mail_tls", True),
    "UseSSL": get_bool("mail_ssl", False),
}

melli_payamak = {
    "username": get_env("mellipayamak_username"),
    "password": get_env("mellipayamak_password"),
    "rest_url": get_env("mellipayamak_rest_url"),
    "template_id_verification": get_env(
        "mellipayamak_template_id_verification", 0, cast=int
    ),
    "template_id_password_reset": get_env(
        "mellipayamak_template_id_password_reset", 0, cast=int
    ),
}

payment_config = {
    "fee_per_person": get_env("payment_fee_per_person", 9_500_000, cast=int),
    "fee_team": get_env("payment_fee_team", 4_500_000, cast=int),
    "league_two_discount": get_env("payment_league_two_discount", 20, cast=int),
    "new_member_fee_per_league": get_env(
        "payment_new_member_fee_per_league", 9_500_000, cast=int
    ),
    "bank_name": get_env("payment_bank_name"),
    "owner_name": get_env("payment_owner_name"),
    "card_number": get_env("payment_card_number"),
    "iban": get_env("payment_iban"),
}

host = get_env("host", "0.0.0.0")
port = get_env("port", 5000, cast=int)
session_cookie_secure = get_bool("session_cookie_secure", False)
session_cookie_httponly = get_bool("session_cookie_httponly", True)
session_cookie_samesite = _normalize_samesite(
    get_env("session_cookie_samesite", "Lax"),
)

# Development ergonomics: running the debug server over HTTP should not lose
# session data simply because production cookies are still enabled in the .env.
if debug:
    session_cookie_secure = False
    if session_cookie_samesite == "None":
        session_cookie_samesite = "Lax"

# ``SameSite=None`` requires Secure cookies in modern browsers. If the
# configuration requests "None" but Secure is disabled (for example on a local
# HTTP setup), gracefully fall back to the safer ``Lax`` value so logins,
# flashes, and chat sessions continue to work instead of silently dropping the
# cookie.
if session_cookie_samesite == "None" and not session_cookie_secure:
    session_cookie_samesite = "Lax"
