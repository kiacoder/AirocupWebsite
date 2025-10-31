"""DataBase Related Code, For Adding Editing And Deleting Members, Teams and Clients"""

import datetime
import os
from contextlib import contextmanager
from typing import Any, Iterator, List, Optional, Tuple

import bcrypt
import constants
import models
import utils
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker

db_engine = create_engine(
    f"sqlite:///{constants.Path.DataBase}", connect_args={"check_same_thread": False}
)
db_session_local = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


@contextmanager
def get_db_session() -> Iterator[Session]:
    db = db_session_local()
    try:
        yield db
    finally:
        db.close()


def CreateDatabase():
    os.makedirs(os.path.dirname(constants.Path.DataBase), exist_ok=True)
    models.DeclarativeBase.metadata.create_all(bind=db_engine)


def has_existing_leader(
    db: Session, team_id: int, member_id_to_exclude: Optional[int] = None
) -> bool:
    query = db.query(models.Member).filter(
        models.Member.TeamID == team_id, models.Member.Role == models.MemberRole.Leader
    )
    if member_id_to_exclude:
        query = query.filter(models.Member.MemberID != member_id_to_exclude)
    return query.first() is not None


def get_all_active_clients(db: Session) -> list[models.Client]:
    return (
        db.query(models.Client)
        .filter(models.Client.Status == models.EntityStatus.ACTIVE)
        .order_by(models.Client.Email.asc())
        .all()
    )


def get_team_by_id(db: Session, team_id: int) -> Optional[models.Team]:
    return db.query(models.Team).filter(models.Team.TeamID == team_id).first()


def ValidateClientUpdate(
    db: Session,
    client_id: int,
    form_data: Any,
    is_valid_password,
    is_valid_email,
    is_valid_iranian_phone,
    fa_to_en,
) -> Tuple[Optional[dict], list[str]]:
    clean_data = {}
    errors = []

    client_to_update = (
        db.query(models.Client).filter(models.Client.client_id == client_id).first()
    )
    if not client_to_update:
        return None, ["اطلاعات کاربر مورد نظر یافت نشد."]

    new_email = form_data.get("Email", "").strip()
    if new_email and new_email != client_to_update.Email:
        if not is_valid_email(new_email):
            errors.append("فرمت ایمیل وارد شده معتبر نیست.")
        else:
            existing_client = (
                db.query(models.Client)
                .filter(
                    func.lower(models.Client.Email) == func.lower(new_email),
                    models.Client.client_id != client_id,
                )
                .first()
            )
            if existing_client:
                errors.append("این ایمیل قبلاً توسط کاربر دیگری ثبت شده است.")
            else:
                clean_data["Email"] = new_email

    new_phone_number = fa_to_en(form_data.get("PhoneNumber", "").strip())
    if new_phone_number and new_phone_number != client_to_update.PhoneNumber:
        if not is_valid_iranian_phone(new_phone_number):
            errors.append("شماره تلفن وارد شده معتبر نیست.")
        else:
            existing_client = (
                db.query(models.Client)
                .filter(
                    models.Client.PhoneNumber == new_phone_number,
                    models.Client.client_id != client_id,
                )
                .first()
            )
            if existing_client:
                errors.append("این شماره تلفن قبلاً توسط کاربر دیگری ثبت شده است.")
            else:
                clean_data["PhoneNumber"] = new_phone_number

    new_password = form_data.get("Password")
    if new_password:
        is_valid, error_message = is_valid_password(new_password)
        if not is_valid:
            errors.append(error_message)
        else:
            clean_data["Password"] = new_password

    if errors:
        return None, errors
    return clean_data, []


def UpdateClientDetails(db: Session, client_id: int, CleanData: dict):
    client = db.query(models.Client).filter(models.Client.client_id == client_id).first()
    if not client:
        return

    if "PhoneNumber" in CleanData:
        client.PhoneNumber = CleanData["PhoneNumber"]
    if "Email" in CleanData:
        client.Email = CleanData["Email"]
    if "Password" in CleanData:
        client.Password = bcrypt.hashpw(
            CleanData["Password"].encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    db.commit()


def GetClientBy(db: Session, Identifier: str, value: Any) -> Optional[models.Client]:
    if Identifier == "client_id":
        return db.query(models.Client).filter(models.Client.client_id == value).first()
    elif Identifier == "Email":
        return (
            db.query(models.Client)
            .filter(func.lower(models.Client.Email) == func.lower(value))
            .first()
        )
    elif Identifier == "PhoneNumber":
        return (
            db.query(models.Client).filter(models.Client.PhoneNumber == value).first()
        )
    raise ValueError(f"Invalid Identifier for searching Clients: {Identifier}")


def GetAllArticles(db: Session):
    return db.query(models.News).order_by(models.News.PublishDate.desc()).all()


def GetArticleByID(db: Session, ArticleID: int):
    return db.query(models.News).filter(models.News.NewsID == ArticleID).first()


def LogLoginAttempt(db: Session, Identifier: str, IPAddress: str, IsSuccess: bool):
    db.add(
        models.LoginAttempt(
            Identifier=Identifier,
            IPAddress=IPAddress,
            Timestamp=datetime.datetime.now(datetime.timezone.utc),
            IsSuccess=IsSuccess,
        )
    )


def PopulateGeographyData():
    with get_db_session() as db:
        if db.query(models.Province).first():
            return
        print("Populating Provinces and Cities tables...")
        for ProvinceName, Cities in constants.ProvincesData.items():
            NewProvince = models.Province(Name=ProvinceName)
            db.add(NewProvince)
            db.flush()
            for CityName in Cities:
                db.add(models.City(Name=CityName, ProvinceID=NewProvince.ProvinceID))
        db.commit()
        print("Geography data populated successfully.")


def ValidateNewMemberData(
    db: Session,
    Name: str,
    NationalID: str,
    Province: str,
    City: str,
    BirthYear: int,
    BirthMonth: int,
    BirthDay: int,
    RoleValue: str,
) -> List[str]:
    Errors = []
    if not utils.IsValidName(Name):
        Errors.append("نام و نام خانوادگی معتبر نیست. لطفاً نام کامل را وارد کنید.")

    if not utils.IsValidNationalID(NationalID):
        Errors.append("کد ملی وارد شده معتبر نیست.")
    elif (
        db.query(models.Member.MemberID)
        .filter(models.Member.NationalID == NationalID)
        .first()
    ):
        Errors.append("این کد ملی قبلاً برای عضو دیگری در سیستم ثبت شده است.")

    if not (
        db.query(models.City.CityID)
        .join(models.Province)
        .filter(models.Province.Name == Province, models.City.Name == City)
        .first()
    ):
        Errors.append("استان یا شهر انتخاب شده معتبر نیست.")

    IsValidDate, DateError = utils.ValidatePersianDate(BirthYear, BirthMonth, BirthDay)
    if not IsValidDate:
        Errors.append(DateError)

    if RoleValue not in {role.value for role in models.MemberRole}:
        Errors.append("نقش انتخاب شده (سرپرست، مربی، عضو) معتبر نیست.")

    return Errors


def LogAction(
    db: Session, client_id: int, ActionDescription: str, IsAdminAction: bool = False
):
    db.add(
        models.HistoryLog(
            client_id=client_id,
            Action=ActionDescription,
            AdminInvolved=IsAdminAction,
            Timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
    )


def SaveChatMessage(db: Session, client_id: int, MessageText: str, Sender: str):
    db.add(
        models.ChatMessage(
            client_id=client_id,
            MessageText=MessageText,
            Sender=Sender,
            Timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
    )


def GetChatHistoryByClientID(db: Session, client_id: int) -> list[models.ChatMessage]:
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.client_id == client_id)
        .order_by(models.ChatMessage.Timestamp.asc())
        .all()
    )


def HasTeamMadeAnyPayment(db: Session, TeamID: int) -> bool:
    return (
        db.query(models.Payment).filter(models.Payment.TeamID == TeamID).first()
        is not None
    )


def CheckIfTeamIsPaid(db: Session, TeamID: int) -> bool:
    return (
        db.query(models.Payment)
        .filter(
            models.Payment.TeamID == TeamID,
            models.Payment.Status == models.PaymentStatus.APPROVED,
        )
        .first()
    ) is not None


def IsMemberLeagueConflict(
    db: Session, NationalID: str, TargetTeamID: int
) -> Tuple[bool, str]:
    TargetTeam = (
        db.query(models.Team.LeagueOneID, models.Team.LeagueTwoID)
        .filter(
            models.Team.TeamID == TargetTeamID,
            models.Team.Status == models.EntityStatus.ACTIVE,
        )
        .first()
    )
    if not TargetTeam or (not TargetTeam.LeagueOneID and not TargetTeam.LeagueTwoID):
        return False, ""

    TargetLeagueIDs = {TargetTeam.LeagueOneID, TargetTeam.LeagueTwoID} - {None}
    if not TargetLeagueIDs:
        return False, ""

    ConflictingTeam = (
        db.query(models.Team)
        .join(models.Member)
        .filter(
            models.Member.NationalID == NationalID,
            models.Team.TeamID != TargetTeamID,
            models.Member.Status == models.EntityStatus.ACTIVE,
            models.Team.Status == models.EntityStatus.ACTIVE,
            models.Member.Role.notin_(
                [models.MemberRole.Leader, models.MemberRole.Coach]
            ),
            (
                models.Team.LeagueOneID.in_(TargetLeagueIDs)
                | models.Team.LeagueTwoID.in_(TargetLeagueIDs)
            ),
        )
        .first()
    )

    if ConflictingTeam:
        ConflictingTeamLeagueIDs = {
            ConflictingTeam.LeagueOneID,
            ConflictingTeam.LeagueTwoID,
        }
        SharedLeagueIDs = TargetLeagueIDs.intersection(ConflictingTeamLeagueIDs)

        SharedLeagueNames = (
            db.query(models.League.Name)
            .filter(models.League.LeagueID.in_(SharedLeagueIDs))
            .all()
        )
        Names = ", ".join([Name for (Name,) in SharedLeagueNames])

        return (
            True,
            f"این عضو در تیم «{ConflictingTeam.TeamName}» که در لیگ(های) «{Names}» حضور دارد، ثبت شده است.",
        )
    return False, ""
