"Configuration module for the web application. loads environment variables"

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH")
secret_key = os.getenv("SECRET_KEY")
debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
if not admin_password_hash or not secret_key:
    raise ValueError(
        "Error: ADMIN_PASSWORD_HASH and SECRET_KEY must be set in the .env"
    )
version = os.getenv("APP_VERSION", "1.0.0")
permanent_session_life_time = timedelta(
    days=int(os.getenv("PERMANENT_SESSION_LIFETIME_DAYS", "7"))
)
mail_configuration = {
    "server": os.getenv("MAIL_SERVER"),
    "port": int(os.getenv("MAIL_PORT", "587")),
    "username": os.getenv("MAIL_USERNAME"),
    "password": os.getenv("MAIL_PASSWORD"),
    "tls": os.getenv("MAIL_TLS", "True").lower() in ("true", "1", "t"),
    "ssl": os.getenv("MAIL_SSL", "False").lower() in ("true", "1", "t"),
}
melli_payamak = {
    "username": os.getenv("MELLIPAYAMAK_USERNAME"),
    "password": os.getenv("MELLIPAYAMAK_PASSWORD"),
    "rest_url": os.getenv("MELLIPAYAMAK_REST_URL"),
    "template_id_verification": int(
        os.getenv("MELLIPAYAMAK_TEMPLATE_ID_VERIFICATION", "0")
    ),
    "template_id_password_reset": int(
        os.getenv("MELLIPAYAMAK_TEMPLATE_ID_PASSWORD_RESET", "0")
    ),
}

payment_config = {
    "fee_per_person": int(os.getenv("PAYMENT_FEE_PER_PERSON", "0")),
    "fee_team": int(os.getenv("PAYMENT_FEE_TEAM", "0")),
    "league_two_discount": int(os.getenv("PAYMENT_LEAGUE_TWO_DISCOUNT", "0")),
    "bank_name": os.getenv("PAYMENT_BANK_NAME"),
    "owner_name": os.getenv("PAYMENT_OWNER_NAME"),
    "card_number": os.getenv("PAYMENT_CARD_NUMBER"),
    "iban": os.getenv("PAYMENT_IBAN"),
}
