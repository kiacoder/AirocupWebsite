"""DataBase Code For adding Editing and Deleting Members, Teams and Clients"""

import datetime
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, List, Optional, Tuple
import bcrypt
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.util import typing as sa_typing
from . import constants
from . import models
from . import utils


if hasattr(sa_typing, "make_union_type"):
    _sa_make_union_type = sa_typing.make_union_type

    def _patched_make_union_type(*types):
        if len(types) == 1 and isinstance(types[0], tuple):
            types = types[0]
        try:
            return _sa_make_union_type(*types)
        except TypeError:
            iterator = iter(types)
            try:
                union_type = next(iterator)
            except StopIteration as stop_error:
                raise stop_error
            for typ in iterator:
                union_type = union_type | typ
            return union_type

    sa_typing.make_union_type = _patched_make_union_type

_normalized_sqlite_path = Path(constants.Path.database).as_posix()

db_engine = create_engine(
    f"sqlite:///{_normalized_sqlite_path}",
    connect_args={"check_same_thread": False},
)


def create_database():
    "Create the database and its tables if they do not exist"
    os.makedirs(os.path.dirname(constants.Path.database), exist_ok=True)
    models.Base.metadata.create_all(bind=db_engine)


def ensure_schema_upgrades():
    """apply lightweight schema adjustments that older databases may lack."""

    def _has_column(connection, table: str, column: str) -> bool:
        return any(
            row[1] == column
            for row in connection.execute(text(f"PRAGMA table_info({table});"))
        )

    def _add_column(connection, table: str, ddl: str):
        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl};"))

    def _ensure_index(connection, name: str, table: str, columns: str):
        existing = [
            row[1] for row in connection.execute(text(f"PRAGMA index_list('{table}');"))
        ]
        if name not in existing:
            connection.execute(
                text(f"CREATE INDEX IF NOT EXISTS {name} ON {table}({columns});")
            )

    with db_engine.connect() as connection:
        if not _has_column(connection, "teams", "education_level"):
            _add_column(connection, "teams", "education_level VARCHAR(50)")

        if not _has_column(connection, "teams", "average_age"):
            _add_column(connection, "teams", "average_age INTEGER DEFAULT 0")

        if not _has_column(connection, "teams", "average_provinces"):
            _add_column(connection, "teams", "average_provinces VARCHAR(255)")

        if not _has_column(connection, "teams", "unpaid_members_count"):
            _add_column(connection, "teams", "unpaid_members_count INTEGER DEFAULT 0")

        if not _has_column(connection, "teams", "status"):
            _add_column(connection, "teams", "status VARCHAR(50) DEFAULT 'active'")
        if not _has_column(connection, "members", "status"):
            _add_column(connection, "members", "status VARCHAR(50) DEFAULT 'active'")
        if not _has_column(connection, "clients", "status"):
            _add_column(connection, "clients", "status VARCHAR(50) DEFAULT 'active'")
        if not _has_column(connection, "clients", "is_phone_verified"):
            _add_column(connection, "clients", "is_phone_verified BOOLEAN DEFAULT 0")
        if not _has_column(connection, "clients", "phone_verification_code"):
            _add_column(connection, "clients", "phone_verification_code VARCHAR(10)")
        if not _has_column(connection, "clients", "verification_code_timestamp"):
            _add_column(connection, "clients", "verification_code_timestamp DATETIME")
        if not _has_column(connection, "payments", "tracking_number"):
            _add_column(connection, "payments", "tracking_number VARCHAR(64)")
        if not _has_column(connection, "payments", "payer_name"):
            _add_column(connection, "payments", "payer_name VARCHAR(100)")
        if not _has_column(connection, "payments", "payer_phone"):
            _add_column(connection, "payments", "payer_phone VARCHAR(20)")
        if not _has_column(connection, "payments", "paid_at"):
            _add_column(connection, "payments", "paid_at DATETIME")
        connection.execute(
            text("UPDATE teams SET status='active' WHERE status IS NULL;")
        )
        connection.execute(
            text("UPDATE members SET status='active' WHERE status IS NULL;")
        )
        connection.execute(
            text("UPDATE clients SET status='active' WHERE status IS NULL;")
        )
        connection.execute(
            text("UPDATE payments SET status='pending' WHERE status IS NULL;")
        )
        _ensure_index(
            connection, "clients_status_email_idx", "clients", "status, email"
        )
        _ensure_index(
            connection, "clients_phone_status_idx", "clients", "phone_number, status"
        )
        _ensure_index(
            connection, "teams_client_status_idx", "teams", "client_id, status"
        )
        _ensure_index(
            connection,
            "teams_status_registration_idx",
            "teams",
            "status, team_registration_date",
        )
        _ensure_index(
            connection, "payments_status_upload_idx", "payments", "status, upload_date"
        )
        _ensure_index(
            connection, "payments_team_status_idx", "payments", "team_id, status"
        )
        _ensure_index(
            connection, "members_team_status_idx", "members", "team_id, status"
        )


@contextmanager
def get_db_session() -> Iterator[Session]:
    "Get a database session"
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    db = session_local()
    try:
        yield db
    finally:
        db.close()


def has_existing_leader(
    db: Session, team_id: int, member_id_to_exclude: Optional[int] = None
) -> bool:
    "Check if team already has leader, optionally excluding specific member id"
    query = db.query(models.Member).filter(
        models.Member.team_id == team_id, models.Member.role == models.MemberRole.LEADER
    )
    if member_id_to_exclude:
        query = query.filter(models.Member.member_id != member_id_to_exclude)
    return query.first() is not None


def get_all_active_clients(db: Session) -> list[models.Client]:
    "Retrieve all active clients ordered by email address"
    return (
        db.query(models.Client)
        .filter(models.Client.status == models.EntityStatus.ACTIVE)
        .order_by(models.Client.email.asc())
        .all()
    )


def get_team_by_id(db: Session, team_id: int) -> Optional[models.Team]:
    "Retrieve a team by its id"
    return db.query(models.Team).filter(models.Team.team_id == team_id).first()


def validate_client_update(
    db: Session,
    client_id: int,
    form_data: Any,
    is_valid_password,
    is_valid_email,
    is_valid_iranian_phone,
    fa_to_en,
) -> Tuple[Optional[dict], list[str]]:
    "Validate client update data and return cleaned data or errors"
    clean_data = {}
    errors = []

    client_to_update = (
        db.query(models.Client).filter(models.Client.client_id == client_id).first()
    )
    if not client_to_update:
        return None, ["اطلاعات کاربر مورد نظر یافت نشد."]

    new_email = form_data.get("email", "").strip()
    if new_email and new_email != client_to_update.email:
        if not is_valid_email(new_email):
            errors.append("فرمت ایمیل وارد شده معتبر نیست.")
        else:
            existing_client = (
                db.query(models.Client)
                .filter(
                    func.lower(models.Client.email) == func.lower(new_email),
                    models.Client.client_id != client_id,
                )
                .first()
            )
            if existing_client:
                errors.append("این ایمیل قبلاً توسط کاربر دیگری ثبت شده است.")
            else:
                clean_data["email"] = new_email

    new_phone_number = fa_to_en(form_data.get("phone_number", "").strip())
    if new_phone_number and new_phone_number != client_to_update.phone_number:
        if not is_valid_iranian_phone(new_phone_number):
            errors.append("شماره تلفن وارد شده معتبر نیست.")
        else:
            existing_client = (
                db.query(models.Client)
                .filter(
                    models.Client.phone_number == new_phone_number,
                    models.Client.client_id != client_id,
                )
                .first()
            )
            if existing_client:
                errors.append("این شماره تلفن قبلاً توسط کاربر دیگری ثبت شده است.")
            else:
                clean_data["phone_number"] = new_phone_number

    new_password = form_data.get("password")
    if new_password:
        is_valid, error_message = is_valid_password(new_password)
        if not is_valid:
            errors.append(error_message)
        else:
            clean_data["password"] = new_password

    if errors:
        return None, errors
    return clean_data, []


def update_client_details(db: Session, client_id: int, clean_data: dict):
    "Update client details in the database"
    client_to_update = (
        db.query(models.Client).filter(models.Client.client_id == client_id).first()
    )
    if not client_to_update:
        return

    if "phone_number" in clean_data:
        client_to_update.phone_number = clean_data["phone_number"]
    if "email" in clean_data:
        client_to_update.email = clean_data["email"]
    if "password" in clean_data:
        client_to_update.password = bcrypt.hashpw(
            clean_data["password"].encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")
    db.commit()


def get_client_by(db: Session, identifier: str, value: Any) -> Optional[models.Client]:
    "Retrieve a client by specified identifier"
    if identifier == "client_id":
        return db.query(models.Client).filter(models.Client.client_id == value).first()
    elif identifier == "email":
        return (
            db.query(models.Client)
            .filter(func.lower(models.Client.email) == func.lower(value))
            .first()
        )
    elif identifier == "phone_number":
        return (
            db.query(models.Client).filter(models.Client.phone_number == value).first()
        )
    raise ValueError(f"Invalid Identifier for searching Clients: {identifier}")


def get_all_articles(db: Session):
    "Retrieve all news articles ordered by publish date descending"
    return db.query(models.News).order_by(models.News.publish_date.desc()).all()


def get_article_by_id(db: Session, article_id: int):
    "Retrieve a news article by its ID"
    return db.query(models.News).filter(models.News.news_id == article_id).first()


def log_login_attempt(db: Session, identifier: str, ip_address: str, is_success: bool):
    "Log a login attempt to the database"
    db.add(
        models.LoginAttempt(
            identifier=identifier,
            ip_address=ip_address,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            is_success=is_success,
        )
    )


def populate_leagues(db: Session):
    "Populate Leagues table from constants if it is empty"
    if db.query(models.League).first():
        return
    print("Populating Leagues table...")

    leagues_data = getattr(constants, "leagues_list", [])
    if not leagues_data:
        print("warning: constants.leagues_list is empty. No leagues to populate.")
        return

    for league_dict in leagues_data:
        if not isinstance(league_dict, dict):
            continue

        new_league = models.League(
            league_id=league_dict.get("id"),
            name=league_dict.get("name"),
            icon=league_dict.get("icon"),
            description=league_dict.get("description"),
        )
        db.add(new_league)

    db.commit()
    print("Leagues data populated successfully.")


def populate_geography_data(db: Session):
    "Populate provinces and Cities tables from constants if they are empty"
    if db.query(models.Province).first():
        return
    print("Populating provinces and Cities tables...")
    for province_name, cities in constants.provinces_data.items():
        new_province = models.Province(name=province_name)
        db.add(new_province)
        db.flush()
        for city_name in cities:
            db.add(models.City(name=city_name, province_id=new_province.province_id))
    db.commit()
    print("Geography data populated successfully.")


def validate_new_member_data(
    db: Session,
    name: str,
    national_id: str,
    province: str,
    city: str,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    role_value: str,
    *,
    team_id: Optional[int] = None,
    member_id_to_exclude: Optional[int] = None,
) -> List[str]:
    "Validate new member data and return a list of error messages if any"
    errors = []

    if not utils.is_valid_name(name):
        errors.append("نام و نام خانوادگی معتبر نیست. لطفاً نام کامل را وارد کنید.")

    if not utils.is_valid_national_id(national_id):
        errors.append("کد ملی وارد شده معتبر نیست.")

    elif team_id:
        duplicate_query = (
            db.query(models.Member.member_id)
            .filter(
                models.Member.team_id == team_id,
                models.Member.national_id == national_id,
                models.Member.status == models.EntityStatus.ACTIVE,
            )
        )
        if member_id_to_exclude:
            duplicate_query = duplicate_query.filter(
                models.Member.member_id != member_id_to_exclude
            )
        if duplicate_query.first():
            errors.append("این کد ملی قبلاً برای این تیم ثبت شده است.")

    if not (
        db.query(models.City.city_id)
        .join(models.Province)
        .filter(models.Province.name == province, models.City.name == city)
        .first()
    ):
        errors.append("استان یا شهر انتخاب شده معتبر نیست.")

    is_valid_date, date_error = utils.validate_persian_date(
        birth_year, birth_month, birth_day
    )
    if not is_valid_date:
        errors.append(date_error)

    if role_value not in {role.value for role in models.MemberRole}:
        errors.append("نقش انتخاب شده (سرپرست، مربی، عضو) معتبر نیست.")

    return errors


def log_action(
    db: Session, client_id: int, action_description: str, is_admin_action: bool = False
):
    "Log an action to the database"
    db.add(
        models.HistoryLog(
            client_id=client_id,
            action=action_description,
            admin_involved=is_admin_action,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
    )


def save_chat_message(
    db: Session, client_id: int, message_text: str, sender: str
) -> models.ChatMessage:
    "Save a chat message to the database and return it."
    message = models.ChatMessage(
        client_id=client_id,
        message_text=message_text,
        sender=sender,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_chat_history_by_client_id(
    db: Session, client_id: int
) -> list[models.ChatMessage]:
    "Retrieve chat history for a specific client"
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.client_id == client_id)
        .order_by(models.ChatMessage.timestamp.asc())
        .all()
    )


def has_team_made_any_payment(db: Session, team_id: int) -> bool:
    "Check if the team has made any payments"
    return (
        db.query(models.Payment).filter(models.Payment.team_id == team_id).first()
        is not None
    )


def check_if_team_is_paid(db: Session, team_id: int) -> bool:
    "Check if the team has any approved payments"
    return (
        db.query(models.Payment)
        .filter(
            models.Payment.team_id == team_id,
            models.Payment.status == models.PaymentStatus.APPROVED,
        )
        .first()
    ) is not None


def is_member_league_conflict(
    db: Session,
    national_id: str,
    target_team_id: int,
    member_id_to_exclude: Optional[int] = None,
) -> Tuple[bool, str]:
    "Check if adding a member to the target team would create league conflict"
    target_team = (
        db.query(models.Team.league_one_id, models.Team.league_two_id)
        .filter(
            models.Team.team_id == target_team_id,
            models.Team.status == models.EntityStatus.ACTIVE,
        )
        .first()
    )
    if not target_team or (
        not target_team.league_one_id and not target_team.league_two_id
    ):
        return False, ""

    target_league_ids = {target_team.league_one_id, target_team.league_two_id} - {None}
    if not target_league_ids:
        return False, ""

    query = (
        db.query(models.Team)
        .join(models.Member)
        .filter(
            models.Member.national_id == national_id,
            models.Team.team_id != target_team_id,
            models.Member.status == models.EntityStatus.ACTIVE,
            models.Team.status == models.EntityStatus.ACTIVE,
            models.Member.role.notin_(
                [models.MemberRole.LEADER, models.MemberRole.COACH]
            ),
            (
                models.Team.league_one_id.in_(target_league_ids)
                | models.Team.league_two_id.in_(target_league_ids)
            ),
        )
    )
    if member_id_to_exclude:
        query = query.filter(models.Member.member_id != member_id_to_exclude)

    conflicting_team = query.first()

    if conflicting_team:
        conflicting_team_league_ids = {
            conflicting_team.league_one_id,
            conflicting_team.league_two_id,
        }
        shared_league_ids = target_league_ids.intersection(conflicting_team_league_ids)

        shared_league_names = (
            db.query(models.League.name)
            .filter(models.League.league_id.in_(shared_league_ids))
            .all()
        )
        names = ", ".join([name for (name,) in shared_league_names])

        return (
            True,
            f"این عضو در تیم «{conflicting_team.team_name}» که در لیگ(های) «{names}» حضور دارد، ثبت شده است.",
        )
    return False, ""
