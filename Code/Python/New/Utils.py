import Constants
from sqlalchemy.orm import Session, subqueryload
import Models
import re as RE
import smtplib as SMTPLib
from typing import Any, IO, Tuple, Optional
import jdatetime as JDateTime
import filetype as FileType
from flask import Flask, session, current_app
from persiantools.digits import fa_to_en as FaToEN
import requests as Requests
from email.mime.text import MIMEText
import datetime as Datetime
import bleach as Bleach
from Database import get_db_session
import Database
import enum as Enum


def IsLeapYear(Year: int) -> bool:
    return (Year % 33) in [1, 5, 9, 13, 17, 22, 26, 30]


def IsValidName(Name: str) -> bool:
    return len(Name.strip().split()) >= 2


def IsValidEmail(Email: str) -> bool:
    return (
        RE.fullmatch(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", Email)
        is not None
    )


def IsValidIranianPhone(Phone: str) -> bool:
    return Phone.isdigit() and len(Phone) == 11 and Phone.startswith("09")


def IsFileAllowed(FileStream: IO[bytes]) -> bool:
    try:
        Kind = FileType.guess(FileStream)
        if Kind is None:
            return False
        return (
            Kind.extension in Constants.AppConfig.AllowedExtensions
            and Kind.mime in Constants.AppConfig.AllowedMimeTypes
        )
    except Exception:
        return False
    finally:
        FileStream.seek(0)


def ValidatePersianDate(Year: Any, Month: Any, Day: Any) -> Tuple[bool, str]:
    try:
        YearInt, MonthInt, DayInt = int(Year), int(Month), int(Day)
        AllowedYears = Constants.Date.GetAllowedYears()
        if YearInt not in AllowedYears:
            return (
                False,
                f"سال باید بین {AllowedYears[0]} و {AllowedYears[-1]} باشد",
            )
        if not (1 <= MonthInt <= 12):
            return False, "ماه باید بین ۱ تا ۱۲ باشد"
        MaxDays = Constants.Date.DaysInMonth.get(MonthInt, 30)
        if MonthInt == 12 and IsLeapYear(YearInt):
            MaxDays = 30
        if not (1 <= DayInt <= MaxDays):
            return False, f"روز برای ماه انتخاب شده باید بین ۱ تا {MaxDays} باشد"
        return True, "تاریخ معتبر است"
    except (ValueError, TypeError):
        return False, "لطفاً اعداد معتبر برای تاریخ وارد کنید"

def GetFormContext() -> dict:
    return {
        "Provinces": Constants.ProvincesData,
        "PersianMonths": Constants.Date.PersianMonths,
        "AllowedYears": Constants.Date.GetAllowedYears(),
        "DaysInMonth": Constants.Date.DaysInMonth,
    }


def SendTemplatedSMSAsync(
    App: Flask, ClientID: int, TemplateID: int, VerificationCode: str, SMSConfig: dict
):
    with App.app_context():
        try:
            with get_db_session() as db:
                Client = (
                    db.query(Models.Client)
                    .filter(Models.Client.ClientID == ClientID)
                    .first()
                )
                if not Client:
                    current_app.logger.error(
                        f"SMS Error: Client with ID {ClientID} not found."
                    )
                    return
                Recipient = Client.PhoneNumber

            Payload = {
                "username": SMSConfig.get("Username"),
                "password": SMSConfig.get("Password"),
                "to": Recipient,
                "bodyId": TemplateID,
                "text": VerificationCode,
            }
            Response = Requests.post(SMSConfig.get("RestURL"), json=Payload, timeout=10)
            Response.raise_for_status()
            ApiResponse = Response.json()

            if ApiResponse.get("RetStatus") == 1:
                current_app.logger.info(
                    f"SMS sent to {Recipient}. Response: {ApiResponse.get('Value')}"
                )
            else:
                current_app.logger.error(
                    f"SMS API failure for {Recipient}. Status: {ApiResponse.get('Value')}"
                )

        except Requests.exceptions.RequestException as Error:
            current_app.logger.error(
                f"SMS to ClientID {ClientID} failed due to a network error: {Error}"
            )
        except Exception as Error:
            current_app.logger.error(
                f"Unexpected error in SendTemplatedSMSAsync for ClientID {ClientID}: {Error}"
            )


def UpdateTeamStats(db: Session, TeamID: int):
    Members = (
        db.query(Models.Member.BirthDate, Models.Province.Name)
        .join(Models.City, Models.Member.CityID == Models.City.CityID)
        .join(Models.Province, Models.City.ProvinceID == Models.Province.ProvinceID)
        .filter(
            Models.Member.TeamID == TeamID,
            Models.Member.Status == Models.EntityStatus.Active,
            Models.Member.BirthDate.isnot(None),
        )
        .all()
    )
    TeamToUpdate = db.query(Models.Team).filter(Models.Team.TeamID == TeamID).first()
    if not TeamToUpdate:
        return

    if not Members:
        TeamToUpdate.AverageAge = 0
        TeamToUpdate.AverageProvinces = ""
    else:
        TotalAge = 0
        Provinces = set()
        Today = Datetime.date.today()
        for BirthDate, ProvinceName in Members:
            if ProvinceName:
                Provinces.add(ProvinceName)
            Age = (
                Today.year
                - BirthDate.year
                - ((Today.month, Today.day) < (BirthDate.month, BirthDate.day))
            )
            TotalAge += Age
        TeamToUpdate.AverageAge = round(TotalAge / len(Members)) if Members else 0
        TeamToUpdate.AverageProvinces = ", ".join(sorted(list(Provinces)))


def ContainsForbiddenWords(InputText: str) -> bool:
    if not InputText:
        return False
    LowercasedInput = InputText.lower()
    for Word in Constants.ForbiddenContent.WORDS:
        if RE.search(r"\b" + RE.escape(Word.lower()) + r"\b", LowercasedInput):
            return True
    return False


def IsValidTeamName(TeamName: str) -> Tuple[bool, str]:
    if not (3 <= len(TeamName) <= 30):
        return False, "نام تیم باید بین ۳ تا ۳۰ کاراکتر باشد."
    if not RE.fullmatch(r"^[A-Za-z\u0600-\u06FF0-9_ ]+$", TeamName):
        return False, "نام تیم فقط می‌تواند شامل حروف، اعداد، فاصله و خط زیر باشد."
    if ContainsForbiddenWords(TeamName):
        return False, "نام تیم حاوی کلمات غیرمجاز است."
    return True, ""


def IsValidNationalID(NationalID: str) -> bool:
    if not RE.fullmatch(r"^\d{10}$", NationalID) or len(set(NationalID)) == 1:
        return False
    Sum = sum(int(NationalID[i]) * (10 - i) for i in range(9))
    Remainder = Sum % 11
    return int(NationalID[9]) == (Remainder if Remainder < 2 else 11 - Remainder)


def SendAsyncEmail(
    App: Flask, ClientID: int, Subject: str, Body: str, MailConfig: dict
):
    with App.app_context():
        try:
            with get_db_session() as db:
                Client = (
                    db.query(Models.Client)
                    .filter(Models.Client.ClientID == ClientID)
                    .first()
                )
                if not Client:
                    current_app.logger.error(
                        f"Email Error: Client with ID {ClientID} not found."
                    )
                    return
                RecipientEmail = Client.Email

            Message = MIMEText(Body, "html", "utf-8")
            Message["Subject"] = Subject
            Message["From"] = MailConfig["Username"]
            Message["To"] = RecipientEmail

            with SMTPLib.SMTP(
                MailConfig["Server"], int(MailConfig["Port"]), timeout=15
            ) as Server:
                Server.starttls()
                Server.login(MailConfig["Username"], MailConfig["Password"])
                Server.sendmail(
                    MailConfig["Username"], [Message["To"]], Message.as_string()
                )
            current_app.logger.info(f"Email successfully sent to {RecipientEmail}")

        except SMTPLib.SMTPException as Error:
            current_app.logger.error(f"SMTP error for ClientID {ClientID}: {Error}")
        except Exception as Error:
            current_app.logger.error(
                f"Unexpected error in SendAsyncEmail for ClientID {ClientID}: {Error}"
            )


def IsValidPassword(Password: str) -> Tuple[bool, Optional[str]]:
    if len(Password) < 8:
        return False, "رمز عبور باید حداقل ۸ کاراکتر باشد."
    if not RE.search(r"[A-Z]", Password):
        return False, "رمز عبور باید حداقل شامل یک حرف بزرگ انگلیسی باشد."
    if not RE.search(r"[a-z]", Password):
        return False, "رمز عبور باید حداقل شامل یک حرف کوچک انگلیسی باشد."
    if not RE.search(r"[0-9]", Password):
        return False, "رمز عبور باید حداقل شامل یک عدد باشد."
    if not RE.search(r'[!@#$%^&*(),.?":{}|<>]', Password):
        return False, "رمز عبور باید حداقل شامل یک کاراکتر خاص باشد."
    return True, None


def CreateMemberFromFormData(
    db: Session, FormData: dict
) -> Tuple[Optional[dict], Optional[str]]:
    try:
        Name = Bleach.clean(FormData.get("Name", "").strip())
        NationalID = FaToEN(FormData.get("NationalID", "").strip())
        RoleValue = FormData.get("Role", "").strip()
        Province = FormData.get("Province", "").strip()
        CityName = FormData.get("City", "").strip()
        BirthYear = int(FormData.get("BirthYear", 0))
        BirthMonth = int(FormData.get("BirthMonth", 0))
        BirthDay = int(FormData.get("BirthDay", 0))
    except (ValueError, TypeError):
        return None, "تاریخ تولد باید به صورت عددی وارد شود."

    Errors = Database.ValidateNewMemberData(
        db,
        Name,
        NationalID,
        Province,
        CityName,
        BirthYear,
        BirthMonth,
        BirthDay,
        RoleValue,
    )
    if Errors:
        return None, " ".join(Errors)

    CityID = (
        db.query(Models.City.CityID)
        .join(Models.Province)
        .filter(Models.Province.Name == Province, Models.City.Name == CityName)
        .scalar()
    )

    Role = next((role for role in Models.MemberRole if role.value == RoleValue), None)
    GregorianDate = JDateTime.date(BirthYear, BirthMonth, BirthDay).togregorian()

    return {
        "Name": Name,
        "NationalID": NationalID,
        "Role": Role,
        "CityID": CityID,
        "BirthDate": GregorianDate,
    }, None


def _validate_member_for_resolution(Member: Models.Member, EducationLevel: str) -> dict:
    Problems = {"Missing": [], "Invalid": []}
    if not Member.Name:
        Problems["Missing"].append("Name")
    if not Member.NationalID:
        Problems["Missing"].append("NationalID")
    if not Member.Role:
        Problems["Missing"].append("Role")
    if not Member.CityID:
        Problems["Missing"].append("City")
    if not Member.BirthDate:
        Problems["Missing"].append("BirthDate")

    if Member.BirthDate:
        try:
            Today = Datetime.date.today()
            Age = (
                Today.year
                - Member.BirthDate.year
                - (
                    (Today.month, Today.day)
                    < (Member.BirthDate.month, Member.BirthDate.day)
                )
            )
            RoleValue = Member.Role.value

            if RoleValue == Models.MemberRole.Leader.value and not (18 <= Age <= 70):
                Problems["Invalid"].append(
                    f"سن سرپرست باید بین 18 تا 70 باشد (سن فعلی: {Age})"
                )
            elif RoleValue == Models.MemberRole.Coach.value and not (16 <= Age <= 70):
                Problems["Invalid"].append(
                    f"سن مربی باید بین 16 تا 70 باشد (سن فعلی: {Age})"
                )

            if EducationLevel in Constants.EducationAgeRanges:
                MinAge, MaxAge = Constants.EducationAgeRanges[EducationLevel]
                if not (MinAge <= Age <= MaxAge):
                    Problems["Invalid"].append(
                        f"سن عضو ({Age}) با مقطع تحصیلی ({EducationLevel}) مطابقت ندارد. محدوده مجاز: {MinAge}-{MaxAge} سال."
                    )
        except (ValueError, AttributeError):
            Problems["Invalid"].append("تاریخ تولد نامعتبر است")

    return Problems


def CheckForDataCompletionIssues(db: Session, ClientID: int) -> Tuple[bool, dict]:
    Client = db.query(Models.Client).filter(Models.Client.ClientID == ClientID).first()
    if not Client:
        return False, {}

    Teams = (
        db.query(Models.Team)
        .options(subqueryload(Models.Team.Members))
        .filter(
            Models.Team.ClientID == ClientID,
            Models.Team.Status == Models.EntityStatus.Active,
        )
        .all()
    )

    ProblematicMembers = {}
    NeedsResolution = False
    for Team in Teams:
        for Member in filter(
            lambda m: m.Status == Models.EntityStatus.Active, Team.Members
        ):
            Problems = _validate_member_for_resolution(Member, Client.EducationLevel)
            if Problems["Missing"] or Problems["Invalid"]:
                ProblematicMembers[Member.MemberID] = Problems
                NeedsResolution = True
    return NeedsResolution, ProblematicMembers


def InternalAddMember(db: Session, TeamID: int, FormData: dict) -> Tuple[bool, str]:
    NewMemberData, Error = CreateMemberFromFormData(db, FormData)
    if Error:
        return False, Error

    if NewMemberData["Role"] == Models.MemberRole.Leader and Database.HasExistingLeader(
        db, TeamID
    ):
        return False, "خطا: این تیم از قبل یک سرپرست دارد."

    HasConflict, ErrorMessage = Database.IsMemberLeagueConflict(
        db, NewMemberData["NationalID"], TeamID
    )
    if HasConflict:
        return False, ErrorMessage

    try:
        NewMember = Models.Member(**NewMemberData, TeamID=TeamID)
        db.add(NewMember)
        return True, NewMember.Name
    except Exception as Error:
        db.rollback()
        current_app.logger.error(
            f"Internal error adding member to Team {TeamID}: {Error}"
        )
        return False, "خطایی داخلی در هنگام افزودن عضو رخ داد."


def GetCurrentClient() -> Optional[Models.Client]:
    ClientID = session.get("ClientID")
    if not ClientID:
        return None
    try:
        with get_db_session() as db:
            return (
                db.query(Models.Client)
                .filter(
                    Models.Client.ClientID == ClientID,
                    Models.Client.Status == Models.EntityStatus.Active,
                )
                .first()
            )
    except Exception as Error:
        current_app.logger.error(f"Error fetching current Client: {Error}")
        return None
