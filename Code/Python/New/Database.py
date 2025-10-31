import os
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Iterator, Any, Optional, Tuple
import datetime
import bcrypt
import Utils
from typing import List
import Constants
import Models

DBEngine = create_engine(
    f"sqlite:///{Constants.Path.DataBase}", connect_args={"check_same_thread": False}
)
DBSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=DBEngine)


@contextmanager
def get_db_session() -> Iterator[Session]:
    db = DBSessionLocal()
    try:
        yield db
    finally:
        db.close()


def CreateDatabase():
    os.makedirs(os.path.dirname(Constants.Path.DataBase), exist_ok=True)
    Models.DeclarativeBase.metadata.create_all(bind=DBEngine)


def HasExistingLeader(
    db: Session, TeamID: int, MemberIDToExclude: Optional[int] = None
) -> bool:
    Query = db.query(Models.Member).filter(
        Models.Member.TeamID == TeamID, Models.Member.Role == Models.MemberRole.Leader
    )
    if MemberIDToExclude:
        Query = Query.filter(Models.Member.MemberID != MemberIDToExclude)
    return Query.first() is not None


def GetAllActiveClients(db: Session) -> list[Models.Client]:
    return (
        db.query(Models.Client)
        .filter(Models.Client.Status == Models.EntityStatus.Active)
        .order_by(Models.Client.Email.asc())
        .all()
    )


def GetTeamByID(db: Session, TeamID: int) -> Optional[Models.Team]:
    return db.query(Models.Team).filter(Models.Team.TeamID == TeamID).first()


def ValidateClientUpdate(
    db: Session,
    ClientID: int,
    FormData: Any,
    IsValidPassword,
    IsValidEmail,
    IsValidIranianPhone,
    FaToEN,
) -> Tuple[Optional[dict], list[str]]:
    CleanData = {}
    Errors = []

    ClientToUpdate = (
        db.query(Models.Client).filter(Models.Client.ClientID == ClientID).first()
    )
    if not ClientToUpdate:
        return None, ["اطلاعات کاربر مورد نظر یافت نشد."]

    NewEmail = FormData.get("Email", "").strip()
    if NewEmail and NewEmail != ClientToUpdate.Email:
        if not IsValidEmail(NewEmail):
            Errors.append("فرمت ایمیل وارد شده معتبر نیست.")
        else:
            ExistingClient = (
                db.query(Models.Client)
                .filter(
                    func.lower(Models.Client.Email) == func.lower(NewEmail),
                    Models.Client.ClientID != ClientID,
                )
                .first()
            )
            if ExistingClient:
                Errors.append("این ایمیل قبلاً توسط کاربر دیگری ثبت شده است.")
            else:
                CleanData["Email"] = NewEmail

    NewPhoneNumber = FaToEN(FormData.get("PhoneNumber", "").strip())
    if NewPhoneNumber and NewPhoneNumber != ClientToUpdate.PhoneNumber:
        if not IsValidIranianPhone(NewPhoneNumber):
            Errors.append("شماره تلفن وارد شده معتبر نیست.")
        else:
            ExistingClient = (
                db.query(Models.Client)
                .filter(
                    Models.Client.PhoneNumber == NewPhoneNumber,
                    Models.Client.ClientID != ClientID,
                )
                .first()
            )
            if ExistingClient:
                Errors.append("این شماره تلفن قبلاً توسط کاربر دیگری ثبت شده است.")
            else:
                CleanData["PhoneNumber"] = NewPhoneNumber

    NewPassword = FormData.get("Password")
    if NewPassword:
        IsValid, ErrorMessage = IsValidPassword(NewPassword)
        if not IsValid:
            Errors.append(ErrorMessage)
        else:
            CleanData["Password"] = NewPassword

    if Errors:
        return None, Errors
    return CleanData, []


def UpdateClientDetails(db: Session, ClientID: int, CleanData: dict):
    Client = db.query(Models.Client).filter(Models.Client.ClientID == ClientID).first()
    if not Client:
        return

    if "PhoneNumber" in CleanData:
        Client.PhoneNumber = CleanData["PhoneNumber"]
    if "Email" in CleanData:
        Client.Email = CleanData["Email"]
    if "Password" in CleanData:
        Client.Password = bcrypt.hashpw(
            CleanData["Password"].encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    db.commit()


def GetClientBy(db: Session, Identifier: str, value: Any) -> Optional[Models.Client]:
    if Identifier == "ClientID":
        return db.query(Models.Client).filter(Models.Client.ClientID == value).first()
    elif Identifier == "Email":
        return (
            db.query(Models.Client)
            .filter(func.lower(Models.Client.Email) == func.lower(value))
            .first()
        )
    elif Identifier == "PhoneNumber":
        return (
            db.query(Models.Client).filter(Models.Client.PhoneNumber == value).first()
        )
    raise ValueError(f"Invalid Identifier for searching Clients: {Identifier}")


def GetAllArticles(db: Session):
    return db.query(Models.News).order_by(Models.News.PublishDate.desc()).all()


def GetArticleByID(db: Session, ArticleID: int):
    return db.query(Models.News).filter(Models.News.NewsID == ArticleID).first()


def LogLoginAttempt(db: Session, Identifier: str, IPAddress: str, IsSuccess: bool):
    db.add(
        Models.LoginAttempt(
            Identifier=Identifier,
            IPAddress=IPAddress,
            Timestamp=datetime.datetime.now(datetime.timezone.utc),
            IsSuccess=IsSuccess,
        )
    )


def PopulateGeographyData():
    with get_db_session() as db:
        if db.query(Models.Province).first():
            return
        print("Populating Provinces and Cities tables...")
        for ProvinceName, Cities in Constants.ProvincesData.items():
            NewProvince = Models.Province(Name=ProvinceName)
            db.add(NewProvince)
            db.flush()
            for CityName in Cities:
                db.add(Models.City(Name=CityName, ProvinceID=NewProvince.ProvinceID))
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
    if not Utils.IsValidName(Name):
        Errors.append("نام و نام خانوادگی معتبر نیست. لطفاً نام کامل را وارد کنید.")

    if not Utils.IsValidNationalID(NationalID):
        Errors.append("کد ملی وارد شده معتبر نیست.")
    elif (
        db.query(Models.Member.MemberID)
        .filter(Models.Member.NationalID == NationalID)
        .first()
    ):
        Errors.append("این کد ملی قبلاً برای عضو دیگری در سیستم ثبت شده است.")

    if not (
        db.query(Models.City.CityID)
        .join(Models.Province)
        .filter(Models.Province.Name == Province, Models.City.Name == City)
        .first()
    ):
        Errors.append("استان یا شهر انتخاب شده معتبر نیست.")

    IsValidDate, DateError = Utils.ValidatePersianDate(BirthYear, BirthMonth, BirthDay)
    if not IsValidDate:
        Errors.append(DateError)

    if RoleValue not in {role.value for role in Models.MemberRole}:
        Errors.append("نقش انتخاب شده (سرپرست، مربی، عضو) معتبر نیست.")

    return Errors


def LogAction(
    db: Session, ClientID: int, ActionDescription: str, IsAdminAction: bool = False
):
    db.add(
        Models.HistoryLog(
            ClientID=ClientID,
            Action=ActionDescription,
            AdminInvolved=IsAdminAction,
            Timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
    )


def SaveChatMessage(db: Session, ClientID: int, MessageText: str, Sender: str):
    db.add(
        Models.ChatMessage(
            ClientID=ClientID,
            MessageText=MessageText,
            Sender=Sender,
            Timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
    )


def GetChatHistoryByClientID(db: Session, ClientID: int) -> list[Models.ChatMessage]:
    return (
        db.query(Models.ChatMessage)
        .filter(Models.ChatMessage.ClientID == ClientID)
        .order_by(Models.ChatMessage.Timestamp.asc())
        .all()
    )


def HasTeamMadeAnyPayment(db: Session, TeamID: int) -> bool:
    return (
        db.query(Models.Payment).filter(Models.Payment.TeamID == TeamID).first()
        is not None
    )


def CheckIfTeamIsPaid(db: Session, TeamID: int) -> bool:
    return (
        db.query(Models.Payment)
        .filter(
            Models.Payment.TeamID == TeamID,
            Models.Payment.Status == Models.PaymentStatus.Approved,
        )
        .first()
    ) is not None


def IsMemberLeagueConflict(
    db: Session, NationalID: str, TargetTeamID: int
) -> Tuple[bool, str]:
    TargetTeam = (
        db.query(Models.Team.LeagueOneID, Models.Team.LeagueTwoID)
        .filter(
            Models.Team.TeamID == TargetTeamID,
            Models.Team.Status == Models.EntityStatus.Active,
        )
        .first()
    )
    if not TargetTeam or (not TargetTeam.LeagueOneID and not TargetTeam.LeagueTwoID):
        return False, ""

    TargetLeagueIDs = {TargetTeam.LeagueOneID, TargetTeam.LeagueTwoID} - {None}
    if not TargetLeagueIDs:
        return False, ""

    ConflictingTeam = (
        db.query(Models.Team)
        .join(Models.Member)
        .filter(
            Models.Member.NationalID == NationalID,
            Models.Team.TeamID != TargetTeamID,
            Models.Member.Status == Models.EntityStatus.Active,
            Models.Team.Status == Models.EntityStatus.Active,
            Models.Member.Role.notin_(
                [Models.MemberRole.Leader, Models.MemberRole.Coach]
            ),
            (
                Models.Team.LeagueOneID.in_(TargetLeagueIDs)
                | Models.Team.LeagueTwoID.in_(TargetLeagueIDs)
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
            db.query(Models.League.Name)
            .filter(Models.League.LeagueID.in_(SharedLeagueIDs))
            .all()
        )
        Names = ", ".join([Name for (Name,) in SharedLeagueNames])

        return (
            True,
            f"این عضو در تیم «{ConflictingTeam.TeamName}» که در لیگ(های) «{Names}» حضور دارد، ثبت شده است.",
        )
    return False, ""
