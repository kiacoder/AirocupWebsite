"Utility functions for validation, file handling, SMS/email sending etc..."

import re
import smtplib
from email.mime.text import MIMEText
import datetime
from typing import Any, IO, Tuple, Optional
from sqlalchemy.orm import Session, subqueryload
from sqlalchemy.exc import SQLAlchemyError
import jdatetime  # type: ignore
import filetype  # type: ignore
from flask import Flask, session, current_app
from persiantools.digits import fa_to_en  # type: ignore
import requests  # type: ignore
import bleach  # type: ignore
from . import database
from . import models
from . import constants


def is_valid_name(name: str) -> bool:
    "Check if the name contains at least two words"
    return len(name.strip().split()) >= 2


def is_valid_email(email: str) -> bool:
    "Validate email format using regex"
    return (
        re.fullmatch(
            r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
            email,
        )
        is not None
    )


def is_valid_iranian_phone(phone: str) -> bool:
    "Validate Iranian phone number format"
    return phone.isdigit() and len(phone) == 11 and phone.startswith("09")


def is_file_allowed(file_stream: IO[bytes]) -> bool:
    "Check if the uploaded file is of an allowed type based on its content"
    try:
        kind = filetype.guess(file_stream)
        if kind is None:
            return False
        return (
            kind.extension in constants.AppConfig.allowed_extensions
            and kind.mime in constants.AppConfig.allowed_mime_types
        )
    except IOError:
        return False
    finally:
        file_stream.seek(0)


def calculate_age(
    birth_date: datetime.date, reference_date: Optional[datetime.date] = None
) -> int:
    """Return the age in completed years at the given reference date (today by default)."""

    if reference_date is None:
        reference_date = datetime.date.today()

    has_had_birthday = (reference_date.month, reference_date.day) >= (
        birth_date.month,
        birth_date.day,
    )
    return reference_date.year - birth_date.year - (0 if has_had_birthday else 1)


def validate_member_age(
    birth_date: datetime.date,
    role: Optional[models.MemberRole],
    education_level: Optional[str],
) -> Tuple[bool, Optional[str]]:
    """Validate a member's age against role-specific and education-level rules."""

    if role is None:
        return False, "نقش عضو مشخص نشده است."

    age = calculate_age(birth_date)

    if role == models.MemberRole.LEADER:
        if age < 18 or age > 70:
            return False, "سن سرپرست باید بین ۱۸ تا ۷۰ سال باشد."
        return True, None

    if role == models.MemberRole.COACH:
        if age < 16 or age > 70:
            return False, "سن مربی باید بین ۱۶ تا ۷۰ سال باشد."
        return True, None

    if role != models.MemberRole.MEMBER:
        return True, None

    if not education_level:
        return False, "مقطع تحصیلی تیم مشخص نشده است."

    level_config = constants.education_levels.get(education_level)
    if not level_config:
        return False, "مقطع تحصیلی انتخاب شده معتبر نیست."

    age_range = level_config.get("ages")
    if not age_range:
        return True, None

    min_age, max_age = age_range
    is_below_min = min_age is not None and age < min_age
    is_above_max = max_age is not None and age > max_age

    if is_below_min or is_above_max:
        if min_age is None and max_age is not None:
            allowed_text = f"تا {max_age} سال"
        elif min_age is not None and max_age is None:
            allowed_text = f"از {min_age} سال به بالا"
        else:
            allowed_text = f"بین {min_age} تا {max_age} سال"

        return (
            False,
            f"سن عضو ({age} سال) با بازه مجاز برای مقطع «{education_level}» ({allowed_text}) همخوانی ندارد.",
        )

    return True, None


def validate_persian_date(year: Any, month: Any, day: Any) -> Tuple[bool, str]:
    """Validate a Persian date given year, month, and day"""
    try:
        year_int, month_int, day_int = int(year), int(month), int(day)
        allowed_years = constants.Date.get_allowed_years()
        if year_int not in allowed_years:
            return (
                False,
                f"سال باید بین {allowed_years[0]} و {allowed_years[-1]} باشد",
            )

        jdatetime.date(year_int, month_int, day_int)

        return True, "تاریخ معتبر است"
    except ValueError:
        return False, "لطفاً تاریخ معتبر را انتخاب کنید (روز و ماه صحیح باشد)"
    except TypeError:
        return False, "لطفاً اعداد معتبر برای تاریخ وارد کنید"


_PERSIAN_NORMALIZATION_TABLE = str.maketrans({"ي": "ی", "ك": "ک"})


def normalize_persian_text(value: Optional[str]) -> str:
    """Normalize Persian text for consistent comparisons.

    This helper removes leading/trailing whitespace, replaces Arabic Ya/Kaf
    variants with their Persian counterparts, and collapses internal
    whitespace. The function returns an empty string when the provided value is
    falsy or not a string, allowing callers to safely chain the result in
    dictionary lookups without additional guards.
    """

    if not isinstance(value, str):
        return ""

    normalized = value.translate(_PERSIAN_NORMALIZATION_TABLE).strip()
    normalized = normalized.replace("\u200c", " ")
    return " ".join(normalized.split())


def get_form_context() -> dict:
    "Provide context data for forms (excluding hardcoded days_in_month)"
    return {
        "Provinces": constants.provinces_data,
        "PersianMonths": constants.Date.persian_months,
        "AllowedYears": constants.Date.get_allowed_years(),
    }


def send_templated_sms_async(
    app: Flask,
    client_id: int,
    template_id: int,
    verification_code: str,
    sms_config: dict,
):
    "Send a templated SMS asynchronously"
    with app.app_context():
        try:
            rest_url = sms_config.get("rest_url")
            if not isinstance(rest_url, str):
                current_app.logger.error(
                    "SMS configuration is missing or invalid for 'rest_url'."
                )
                return

            with database.get_db_session() as db:
                client = (
                    db.query(models.Client)
                    .filter(models.Client.client_id == client_id)
                    .first()
                )
                if not client:
                    current_app.logger.error(
                        f"SMS error: Client with ID {client_id} not found."
                    )
                    return
                recipient = client.phone_number

            payload = {
                "username": sms_config.get("username"),
                "password": sms_config.get("password"),
                "to": recipient,
                "bodyId": template_id,
                "text": verification_code,
            }
            response = requests.post(rest_url, data=payload, timeout=10)
            response.raise_for_status()
            api_response = response.json()

            if api_response.get("RetStatus") == 1:
                current_app.logger.info(
                    f"SMS sent to {recipient}. "
                    f"Response: {api_response.get('Value')}"
                )
            else:
                current_app.logger.error(
                    f"SMS API failure for {recipient}. "
                    f"Status: {api_response.get('Value')}"
                )

        except requests.exceptions.RequestException as error:
            current_app.logger.error(
                f"SMS to client_id {client_id} failed due to a "
                f"network error: {error}"
            )
        except (SQLAlchemyError, KeyError) as error:
            current_app.logger.error(
                "Unexpected error in send_templated_sms_async for "
                f"client_id {client_id}: {error}"
            )


def update_team_stats(db: Session, team_id: int):
    "Update average age and provinces of members in a team"
    members = (
        db.query(models.Member.birth_date, models.Province.name)
        .join(models.City, models.Member.city_id == models.City.city_id)
        .join(
            models.Province,
            models.City.province_id == models.Province.province_id,
        )
        .filter(
            models.Member.team_id == team_id,
            models.Member.status == models.EntityStatus.ACTIVE,
            models.Member.birth_date.isnot(None),
        )
        .all()
    )

    if not members:
        average_age = 0
        average_provinces = ""
    else:
        total_age = 0
        provinces = set()
        today_gregorian = datetime.date.today()
        for birth_date, province_name in members:
            if province_name:
                provinces.add(province_name)
            has_birthday_passed = (today_gregorian.month, today_gregorian.day) < (
                birth_date.month,
                birth_date.day,
            )
            age = today_gregorian.year - birth_date.year - has_birthday_passed
            total_age += age
        average_age = round(total_age / len(members))
        average_provinces = ", ".join(sorted(list(provinces)))

    db.query(models.Team).filter(models.Team.team_id == team_id).update(
        {"average_age": average_age, "average_provinces": average_provinces}
    )


def contains_forbidden_words(input_text: str) -> bool:
    "Check if the input text contains forbidden words"
    if not input_text:
        return False
    lowercased_input = input_text.lower()
    for word in constants.ForbiddenContent.custom_words:
        if re.search(r"\b" + re.escape(word.lower()) + r"\b", lowercased_input):
            return True
    return False


def is_valid_team_name(team_name: str) -> Tuple[bool, str]:
    "Validate team name against length, character set, and forbidden words"
    if not (3 <= len(team_name) <= 30):
        return False, "نام تیم باید بین ۳ تا ۳۰ کاراکتر باشد."
    if not re.fullmatch(r"^[A-Za-z\u0600-\u06FF0-9_ ]+$", team_name):
        return (
            False,
            "نام تیم فقط می‌تواند شامل حروف، اعداد، فاصله و خط زیر باشد.",
        )
    if contains_forbidden_words(team_name):
        return False, "نام تیم حاوی کلمات غیرمجاز است."
    return True, ""


def is_valid_national_id(national_id: str) -> bool:
    "Validate Iranian national ID"
    if not re.fullmatch(r"^\d{10}$", national_id) or len(set(national_id)) == 1:
        return False
    s = sum(int(national_id[i]) * (10 - i) for i in range(9))
    r = s % 11
    return int(national_id[9]) == (r if r < 2 else 11 - r)


def send_async_email(
    app: Flask, client_id: int, subject: str, body: str, mail_config: dict
):
    "Send an email asynchronously to a client"
    with app.app_context():
        try:
            with database.get_db_session() as db:
                client = (
                    db.query(models.Client)
                    .filter(models.Client.client_id == client_id)
                    .first()
                )
                if not client:
                    current_app.logger.error(
                        f"email error: Client with ID {client_id} not found."
                    )
                    return
                recipient_email = client.email

            message = MIMEText(body, "html", "utf-8")
            message["Subject"] = subject
            message["From"] = mail_config["Username"]
            message["To"] = str(recipient_email)
            use_ssl = mail_config.get("UseSSL", False)
            server_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP

            with server_class(
                mail_config["Server"], mail_config["Port"], timeout=15
            ) as server:
                if not use_ssl:
                    server.starttls()

                server.login(mail_config["Username"], mail_config["Password"])
                server.sendmail(
                    mail_config["Username"],
                    [message["To"]],
                    message.as_string(),
                )
            current_app.logger.info(f"email successfully sent " f"to {recipient_email}")

        except smtplib.SMTPException as error:
            current_app.logger.error(
                f"SMTP error for client_id {client_id}: " f"{error}"
            )
        except (KeyError, TypeError) as error:
            current_app.logger.error(
                f"Unexpected error in send_async_email for client_id "
                f"{client_id}: {error}"
            )


def is_valid_password(password: str) -> Tuple[bool, Optional[str]]:
    "Validate password complexity requirements"
    if len(password) < 8:
        return False, "رمز عبور باید حداقل ۸ کاراکتر باشد."
    if not re.search(r"[A-Z]", password):
        return False, "رمز عبور باید حداقل شامل یک حرف بزرگ انگلیسی باشد."
    if not re.search(r"[a-z]", password):
        return False, "رمز عبور باید حداقل شامل یک حرف کوچک انگلیسی باشد."
    if not re.search(r"[0-9]", password):
        return False, "رمز عبور باید حداقل شامل یک عدد باشد."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "رمز عبور باید حداقل شامل یک کاراکتر خاص باشد."
    return True, None


def create_member_from_form_data(
    db: Session,
    form_data: dict,
    *,
    team_id: Optional[int] = None,
    member_id: Optional[int] = None,
) -> Tuple[Optional[dict], Optional[str]]:
    """Create a member dictionary from form data after validation.

    ``team_id`` and ``member_id`` are optional and let the validator ignore the
    current record when editing as well as block duplicates within the same
    team without preventing members from joining different teams/leagues.
    """
    try:
        name = bleach.clean(form_data.get("name", "").strip())
        national_id = fa_to_en(form_data.get("national_id", "").strip())
        role_value = form_data.get("role", "").strip()
        province = form_data.get("province", "").strip()
        city_name = form_data.get("city", "").strip()
        birth_year = int(form_data.get("birth_year", 0))
        birth_month = int(form_data.get("birth_month", 0))
        birth_day = int(form_data.get("birth_day", 0))
    except (ValueError, TypeError):
        return None, "تاریخ تولد باید به صورت عددی وارد شود."

    errors = database.validate_new_member_data(
        db,
        name,
        national_id,
        province,
        city_name,
        birth_year,
        birth_month,
        birth_day,
        role_value,
        team_id=team_id,
        member_id_to_exclude=member_id,
    )
    if errors:
        return None, " ".join(errors)

    city_id = (
        db.query(models.City.city_id)
        .join(models.Province)
        .filter(models.Province.name == province, models.City.name == city_name)
        .scalar()
    )

    role = next((r for r in models.MemberRole if r.value == role_value), None)
    persian_date = jdatetime.date(birth_year, birth_month, birth_day)
    gregorian_date = persian_date.togregorian()

    return {
        "name": name,
        "national_id": national_id,
        "role": role,
        "city_id": city_id,
        "birth_date": gregorian_date,
    }, None


def validate_member_for_resolution(
    member: models.Member, education_level: Optional[str]
) -> dict:
    "Validate a member's data for missing or invalid fields"
    problems: dict[str, list[str]] = {"missing": [], "invalid": []}
    if member.name is None:
        problems["missing"].append("name")
    if member.national_id is None:
        problems["missing"].append("national_id")
    if member.role is None:
        problems["missing"].append("role")
    if member.city_id is None:
        problems["missing"].append("city")
    if member.birth_date is None:
        problems["missing"].append("birth_date")

    if member.birth_date is not None:
        try:
            is_valid_age, age_error = validate_member_age(
                member.birth_date,
                member.role,
                education_level,
            )
            if not is_valid_age and age_error:
                problems["invalid"].append(age_error)
        except (ValueError, AttributeError):
            problems["invalid"].append("تاریخ تولد نامعتبر است")

    return problems


def check_for_data_completion_issues(db: Session, client_id: int) -> Tuple[bool, dict]:
    "Check all teams and members for data completion issues"
    client = (
        db.query(models.Client).filter(models.Client.client_id == client_id).first()
    )
    if not client:
        return False, {}

    teams = (
        db.query(models.Team)
        .options(subqueryload(models.Team.members))
        .filter(
            models.Team.client_id == client_id,
            models.Team.status == models.EntityStatus.ACTIVE,
        )
        .all()
    )

    problematic_members = {}
    needs_resolution = False
    for team in teams:
        education_level = getattr(team, "education_level", None)

        for member in filter(
            lambda m: m.status == models.EntityStatus.ACTIVE, team.members
        ):
            problems = validate_member_for_resolution(member, education_level)
            if problems["missing"] or problems["invalid"]:
                problematic_members[member.member_id] = problems
                needs_resolution = True

    return needs_resolution, problematic_members


def internal_add_member(
    db: Session, team_id: int, form_data: dict
) -> Tuple[Optional[models.Member], Optional[str]]:
    "Add a new member to a team after validating the data"
    new_member_data, error = create_member_from_form_data(
        db, form_data, team_id=team_id
    )
    if error:
        return None, error
    if not new_member_data:
        return None, "خطایی ناشناخته در هنگام پردازش اطلاعات عضو رخ داد."

    if new_member_data[
        "role"
    ] == models.MemberRole.LEADER and database.has_existing_leader(db, team_id):
        return None, "خطا: این تیم از قبل یک سرپرست دارد."

    team = db.query(models.Team).filter(models.Team.team_id == team_id).first()
    education_level = getattr(team, "education_level", None) if team else None
    if new_member_data["role"] == models.MemberRole.MEMBER and not education_level:
        return None, "ابتدا مقطع تحصیلی تیم را مشخص کنید."

    is_age_valid, age_error = validate_member_age(
        new_member_data["birth_date"],
        new_member_data["role"],
        education_level,
    )
    if not is_age_valid:
        return None, age_error or "سن عضو با قوانین مقطع انتخاب شده همخوانی ندارد."

    has_conflict, error_message = database.is_member_league_conflict(
        db, new_member_data["national_id"], team_id
    )
    if has_conflict:
        return None, error_message

    try:
        new_member = models.Member(**new_member_data, team_id=team_id)
        db.add(new_member)
        return new_member, None
    except SQLAlchemyError as error:
        db.rollback()
        current_app.logger.error(
            f"Internal error adding member to Team {team_id}: {error}"
        )
        return None, "خطایی داخلی در هنگام افزودن عضو رخ داد."


def get_current_client(allow_inactive: bool = False) -> Optional[models.Client]:
    """Retrieve the currently logged-in Client based on session data."""
    client_id = session.get("client_id")
    if not client_id:
        return None
    try:
        with database.get_db_session() as db:
            query = db.query(models.Client).filter(
                models.Client.client_id == client_id
            )
            if not allow_inactive:
                query = query.filter(
                    models.Client.status == models.EntityStatus.ACTIVE
                )
            return query.first()
    except SQLAlchemyError as error:
        current_app.logger.error(f"error fetching current Client: {error}")
        return None
