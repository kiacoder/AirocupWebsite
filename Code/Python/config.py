"Configuration module for the web application. loads environment variables"

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

admin_password_hash = os.getenv("admin_password_hash")
secret_key = os.getenv("secret_key")
flask_debug = os.getenv("flask_debug", "False").lower() in ("true", "1", "t")
if not admin_password_hash or not secret_key:
    raise ValueError(
        "error: admin_password_hash and secret_key must be set in the .env"
    )
app_version = os.getenv("app_version", "1.0.0")
permanent_session_lifetime = timedelta(
    days=int(os.getenv("permanent_session_lifetime_days", "7"))
)
# Mail Server Configuration
mail_server = os.getenv("mail_server")
mail_port = int(os.getenv("mail_port", "587"))
mail_username = os.getenv("mail_username")
mail_password = os.getenv("mail_password")
mail_tls = os.getenv("mail_tls", "True").lower() in ("true", "1", "t")
mail_ssl = os.getenv("mail_ssl", "False").lower() in ("true", "1", "t")

# MelliPayamak SMS Panel Configuration
mellipayamak_username = os.getenv("mellipayamak_username")
mellipayamak_password = os.getenv("mellipayamak_password")
mellipayamak_rest_url = os.getenv("mellipayamak_rest_url")
mellipayamak_template_id_verification = int(
    os.getenv("mellipayamak_template_id_verification", "0")
)
mellipayamak_template_id_password_reset = int(
    os.getenv("mellipayamak_template_id_password_reset", "0")
)

# Payment Configuration
payment_fee_per_person = int(os.getenv("payment_fee_per_person", "0"))
payment_fee_team = int(os.getenv("payment_fee_team", "0"))
payment_league_two_discount = int(os.getenv("payment_league_two_discount", "0"))
payment_bank_name = os.getenv("payment_bank_name")
payment_owner_name = os.getenv("payment_owner_name")
payment_card_number = os.getenv("payment_card_number")
payment_iban = os.getenv("payment_iban")

# Host Configuration
host = os.getenv("host", "0.0.0.0")