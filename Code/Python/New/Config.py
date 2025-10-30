import jdatetime as JDateTime
import os as OS
from dotenv import load_dotenv
from datetime import timedelta as TimeDelta

load_dotenv()

# --- Core Application Settings ---
AdminPasswordHash = OS.getenv("ADMIN_PASSWORD_HASH")
SecretKey = OS.getenv("SECRET_KEY")
Debug = OS.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")

if not AdminPasswordHash or not SecretKey:
    raise ValueError(
        "Error: ADMIN_PASSWORD_HASH and SECRET_KEY must be set in the .env file."
    )

# --- Application Behavior ---
Version = OS.getenv("APP_VERSION", "1.0.0")
PermanentSessionLifeTime = TimeDelta(
    days=int(OS.getenv("PERMANENT_SESSION_LIFETIME_DAYS", 7))
)

# --- Service Configurations ---
MailConfiguration = {
    "Server": OS.getenv("MAIL_SERVER"),
    "Port": int(OS.getenv("MAIL_PORT", 587)),
    "Username": OS.getenv("MAIL_USERNAME"),
    "Password": OS.getenv("MAIL_PASSWORD"),
    "TLS": OS.getenv("MAIL_TLS", "True").lower() in ("true", "1", "t"),
    "SSL": OS.getenv("MAIL_SSL", "False").lower() in ("true", "1", "t"),
}

MelliPayamak = {
    "Username": OS.getenv("MELLIPAYAMAK_USERNAME"),
    "Password": OS.getenv("MELLIPAYAMAK_PASSWORD"),
    "RestURL": OS.getenv("MELLIPAYAMAK_REST_URL"),
    "TemplateID_Verification": int(OS.getenv("MELLIPAYAMAK_TEMPLATE_ID_VERIFICATION")),
    "TemplateID_PasswordReset": int(OS.getenv("MELLIPAYAMAK_TEMPLATE_ID_PASSWORD_RESET")),
}

PaymentConfig = {
    "FeePerPerson": int(OS.getenv("PAYMENT_FEE_PER_PERSON")),
    "FeeTeam": int(OS.getenv("PAYMENT_FEE_TEAM")),
    "LeagueTwoDiscount": int(OS.getenv("PAYMENT_LEAGUE_TWO_DISCOUNT")),
    "BankName": OS.getenv("PAYMENT_BANK_NAME"),
    "OwnerName": OS.getenv("PAYMENT_OWNER_NAME"),
    "CardNumber": OS.getenv("PAYMENT_CARD_NUMBER"),
    "IBAN": OS.getenv("PAYMENT_IBAN"),
}
