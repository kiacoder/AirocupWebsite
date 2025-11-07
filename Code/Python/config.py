"""
Configuration module for the web application.
Loads environment variables and applies type-safe parsing.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv
from typing import Callable, Any

load_dotenv()


def get_env(key: str, default: Any = None, cast: Callable[[str], Any] = str, strip_quotes: bool = True) -> Any:
    """Helper to safely fetch and cast environment variables."""
    val = os.getenv(key, default)
    if val is None:
        return default
    if strip_quotes and isinstance(val, str):
        val = val.strip('"').strip("'")
    try:
        return cast(val)
    except Exception:
        return default


def get_bool(key: str, default=False):
    """Helper to parse booleans consistently."""
    val = os.getenv(key, str(default))
    val = val.strip('"').strip("'").lower()
    return val in ("true", "1", "t", "yes", "y")


# Critical values
admin_password_hash = get_env("admin_password_hash")
secret_key = get_env("secret_key")

if not admin_password_hash or not secret_key:
    raise ValueError("error: admin_password_hash and secret_key must be set in the .env")

# General app settings
debug = get_bool("flask_debug", False)
app_version = get_env("app_version", "1.0.0")
permanent_session_lifetime = timedelta(
    days=get_env("permanent_session_lifetime_days", 7, cast=int)
)

# Mail configuration
mail_configuration = {
    "Server": get_env("mail_server"),
    "Port": get_env("mail_port", 587, cast=int),
    "Username": get_env("mail_username"),
    "Password": get_env("mail_password"),
    "UseTLS": get_bool("mail_tls", True),
    "UseSSL": get_bool("mail_ssl", False),
}

# MelliPayamak SMS Panel
melli_payamak = {
    "username": get_env("mellipayamak_username"),
    "password": get_env("mellipayamak_password"),
    "rest_url": get_env("mellipayamak_rest_url"),
    "template_id_verification": get_env("mellipayamak_template_id_verification", 0, cast=int),
    "template_id_password_reset": get_env("mellipayamak_template_id_password_reset", 0, cast=int),
}

# Payment configuration
payment_config = {
    "fee_per_person": get_env("payment_fee_per_person", 0, cast=int),
    "fee_team": get_env("payment_fee_team", 0, cast=int),
    "league_two_discount": get_env("payment_league_two_discount", 0, cast=int),
    "bank_name": get_env("payment_bank_name"),
    "owner_name": get_env("payment_owner_name"),
    "card_number": get_env("payment_card_number"),
    "iban": get_env("payment_iban"),
}

# Host
host = get_env("host", "0.0.0.0")
