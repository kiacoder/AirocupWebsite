import os as OS
import random as Random
import string as String
import uuid as UUID
from threading import Thread
import bcrypt as BCrypt
import jdatetime as JDateTime
from persiantools.digits import fa_to_en as FaToEN
from sqlalchemy import exc, func, select
from sqlalchemy.orm import subqueryload
import datetime as Datetime
import secrets as Secrets
import bleach as Bleach
from werkzeug.utils import secure_filename as SecureFileName, safe_join as SafeJoin
from flask import (
    Blueprint,
    abort as Abort,
    flash as Flash,
    redirect as ReDirect,
    render_template as RenderTemplate,
    request as Request,
    send_from_directory as SendFromDirectory,
    session,
    url_for as URLFor,
    jsonify as Jsonify,
)

import Config
import Database
import Constants
import Models
import Utils
import App

ClientBlueprint = Blueprint("Client", __name__)


@App.FlaskApp.route("/SignUp", methods=["GET", "POST"])
def SignUp():
    if Request.method == "POST":
        App.CSRF_Protector.protect()

        Phone = FaToEN(Request.form.get("PhoneNumber", "").strip())
        Email = FaToEN(Request.form.get("Email", "").strip().lower())
        Password = Request.form.get("Password", "")
        EducationLevel = Request.form.get("EducationLevel", "").strip()

        FormValues = {
            "PhoneNumber": Phone,
            "Email": Email,
            "EducationLevel": EducationLevel,
        }

        if EducationLevel not in Constants.AllowedEducation:
            Flash("مقطع تحصیلی انتخاب‌شده نامعتبر است.", "Error")
            return RenderTemplate(Constants.ClientHTMLNamesData["SignUp"], **FormValues)

        if Password != Request.form.get("ConfirmPassword", ""):
            Flash("رمز عبور و تکرار آن یکسان نیستند.", "Error")
            return RenderTemplate(Constants.ClientHTMLNamesData["SignUp"], **FormValues)

        IsValid, ErrorMessage = Utils.IsValidPassword(Password)
        if not IsValid:
            Flash(ErrorMessage, "Error")
            return RenderTemplate(Constants.ClientHTMLNamesData["SignUp"], **FormValues)

        if not Utils.IsValidIranianPhone(Phone) or not Utils.IsValidEmail(Email):
            Flash("ایمیل یا شماره موبایل نامعتبر است.", "Error")
            return RenderTemplate(Constants.ClientHTMLNamesData["SignUp"], **FormValues)

        with Database.GetDBSession() as DbSession:
            try:
                HashedPassword = BCrypt.hashpw(
                    Password.encode("utf-8"), BCrypt.gensalt()
                )
                VerificationCode = "".join(Random.choices(String.digits, k=6))
                NewClient = Models.Client(
                    PhoneNumber=Phone,
                    Email=Email,
                    Password=HashedPassword.decode("utf-8"),
                    RegistrationDate=Datetime.datetime.now(Datetime.timezone.utc),
                    EducationLevel=EducationLevel,
                    PhoneVerificationCode=VerificationCode,
                    VerificationCodeTimestamp=Datetime.datetime.now(
                        Datetime.timezone.utc
                    ),
                )
                DbSession.add(NewClient)
                DbSession.commit()

                Thread(
                    target=Utils.SendTemplatedSMSAsync,
                    args=(
                        App.FlaskApp,
                        NewClient.ClientID,
                        Config.MelliPayamak["TemplateID_Verification"],
                        VerificationCode,
                        Config.MelliPayamak,
                    ),
                ).start()

                return ReDirect(
                    URLFor("Verify", Action="phone_signup", ClientID=NewClient.ClientID)
                )

            except exc.IntegrityError:
                DbSession.rollback()
                Flash(
                    "کاربری با این ایمیل یا شماره تلفن قبلا ثبت نام کرده است.", "Error"
                )
                return RenderTemplate(
                    Constants.ClientHTMLNamesData["SignUp"], **FormValues
                )
            except Exception as Error:
                DbSession.rollback()
                App.FlaskApp.logger.error(f"SignUp unexpected error: {Error}")
                Flash("خطایی در هنگام ثبت نام رخ داد. لطفا دوباره تلاش کنید.", "Error")
                return RenderTemplate(
                    Constants.ClientHTMLNamesData["SignUp"], **FormValues
                )

    return RenderTemplate(Constants.ClientHTMLNamesData["SignUp"])


@App.FlaskApp.route("/ResolveIssues", methods=["GET"])
@App.ResolutionRequired
def ResolveDataIssues():
    with Database.GetDBSession() as db:
        Client = (
            db.query(Models.Client)
            .options(
                subqueryload(Models.Client.Teams).subqueryload(Models.Team.Members)
            )
            .filter(Models.Client.ClientID == session.get("ClientIDForResolution"))
            .first()
        )

        if not Client:
            session.clear()
            Flash("خطا: اطلاعات کاربری برای اصلاح یافت نشد.", "Error")
            return ReDirect(URLFor("Login"))

    return RenderTemplate(
        Constants.ClientHTMLNamesData["Null"],
        Client=Client,
        Problems=session.get("ResolutionProblems", {}),
        **Utils.GetFormContext(),
    )


@App.FlaskApp.route("/SubmitResolution", methods=["POST"])
@App.ResolutionRequired
def SubmitDataResolution():
    App.CSRF_Protector.protect()
    with Database.GetDBSession() as DbSession:
        try:
            RoleMap = {Role.value: Role for Role in Models.MemberRole}
            UpdatedMemberIDs = {
                int(k.split("_")[-1])
                for k in Request.form
                if k.startswith("member_name_")
            }

            for MemberID in UpdatedMemberIDs:
                Member = (
                    DbSession.query(Models.Member)
                    .join(Models.Team)
                    .filter(
                        Models.Member.MemberID == MemberID,
                        Models.Team.ClientID == session.get("ClientIDForResolution"),
                    )
                    .first()
                )

                if Member:
                    Member.Name = Bleach.clean(
                        Request.form.get(f"member_name_{MemberID}", "").strip()
                    )
                    Member.NationalID = FaToEN(
                        Request.form.get(f"member_nationalid_{MemberID}", "").strip()
                    )
                    RoleStr = Request.form.get(f"member_Role_{MemberID}", "").strip()
                    Member.Role = RoleMap.get(RoleStr, Models.MemberRole.Member)

                    ProvinceName = Request.form.get(
                        f"member_Province_{MemberID}", ""
                    ).strip()
                    CityName = Request.form.get(f"member_City_{MemberID}", "").strip()

                    CityID = (
                        DbSession.query(Models.City.CityID)
                        .join(Models.Province)
                        .filter(
                            Models.Province.Name == ProvinceName,
                            Models.City.Name == CityName,
                        )
                        .scalar()
                    )
                    Member.CityID = CityID

                    YearStr = Request.form.get(f"member_birthyear_{MemberID}")
                    MonthStr = Request.form.get(f"member_birthmonth_{MemberID}")
                    DayStr = Request.form.get(f"member_birthday_{MemberID}")

                    if YearStr and MonthStr and DayStr:
                        try:
                            Year, Month, Day = int(YearStr), int(MonthStr), int(DayStr)
                            JalaliDate = JDateTime.date(Year, Month, Day)
                            Member.BirthDate = JalaliDate.togregorian()
                        except (ValueError, TypeError):
                            Flash(
                                f"تاریخ تولد نامعتبر برای عضو '{Member.Name}' نادیده گرفته شد.",
                                "Warning",
                            )

            DbSession.commit()

            NeedsArchiving, NewProblems = Utils.CheckForDataCompletionIssues(
                DbSession, session.get("ClientIDForResolution")
            )

            if not NeedsArchiving:
                Client = (
                    DbSession.query(Models.Client)
                    .filter(
                        Models.Client.ClientID == session.get("ClientIDForResolution")
                    )
                    .first()
                )
                Client.Status = Models.EntityStatus.Active
                for Team in Client.Teams:
                    if Team.Status != Models.EntityStatus.Active:
                        Team.Status = Models.EntityStatus.Active
                    for Member in Team.Members:
                        if Member.Status != Models.EntityStatus.Active:
                            Member.Status = Models.EntityStatus.Active
                DbSession.commit()

                session.clear()
                session["ClientID"] = session.get("ClientIDForResolution")
                session.permanent = True
                Flash(
                    "اطلاعات شما با موفقیت تکمیل و حساب کاربری شما مجددا فعال شد!",
                    "Success",
                )
                return ReDirect(URLFor("Dashboard"))
            else:
                session["ResolutionProblems"] = NewProblems
                Flash(
                    "برخی از مشکلات همچنان باقی است. لطفا موارد مشخص شده را اصلاح نمایید.",
                    "Error",
                )
                return ReDirect(URLFor("ResolveDataIssues"))

        except Exception as Error:
            DbSession.rollback()
            App.FlaskApp.logger.error(
                f"Error during Data resolution for ClientID {session.get("ClientIDForResolution")}: {Error}"
            )
            Flash(
                "خطایی در هنگام ذخیره اطلاعات رخ داد. لطفا دوباره تلاش کنید.", "Error"
            )
            return ReDirect(URLFor("ResolveDataIssues"))


@App.FlaskApp.route("/Login", methods=["GET", "POST"])
@App.limiter.limit("15 per minute")
def Login():
    NextURL = Request.args.get("next")
    if Request.method == "POST":
        App.CSRF_Protector.protect()
        IPAddress = Request.remote_addr
        Identifier = FaToEN(Request.form.get("Identifier", "").strip())
        Password = Request.form.get("Password", "").encode("utf-8")
        NextURLFromForm = Request.form.get("next")

        with Database.GetDBSession() as DbSession:
            ClientCheck = Database.GetClientBy(
                DbSession, "Email", Identifier
            ) or Database.GetClientBy(DbSession, "PhoneNumber", Identifier)

            if not ClientCheck or not BCrypt.checkpw(
                Password, ClientCheck.Password.encode("utf-8")
            ):
                Database.LogLoginAttempt(
                    DbSession, Identifier, IPAddress, IsSuccess=False
                )
                Flash("ایمیل/شماره تلفن یا رمز عبور نامعتبر است.", "Error")
                return ReDirect(URLFor("Login", next=NextURLFromForm or ""))

            if ClientCheck.Status != Models.EntityStatus.Active:
                Flash(
                    "حساب کاربری شما غیر فعال شده است. لطفا با مدیریت تماس بگیرید.",
                    "Error",
                )
                return ReDirect(URLFor("Login"))

            Database.LogLoginAttempt(DbSession, Identifier, IPAddress, IsSuccess=True)

            if not ClientCheck.IsPhoneVerified:
                NewCode = "".join(Random.choices(String.digits, k=6))
                ClientCheck.PhoneVerificationCode = NewCode
                ClientCheck.VerificationCodeTimestamp = Datetime.datetime.now(
                    Datetime.timezone.utc
                )
                DbSession.commit()
                Thread(
                    target=Utils.SendTemplatedSMSAsync,
                    args=(
                        App.FlaskApp,
                        ClientCheck.ClientID,
                        Config.MelliPayamak["TemplateID_Verification"],
                        NewCode,
                        Config.MelliPayamak,
                    ),
                ).start()
                Flash(
                    "حساب شما هنوز فعال نشده است. یک کد تایید جدید به شماره موبایل شما ارسال شد.",
                    "Warning",
                )
                return ReDirect(
                    URLFor(
                        "Verify", Action="phone_signup", ClientID=ClientCheck.ClientID
                    )
                )

            NeedsResolution, Problems = Utils.CheckForDataCompletionIssues(
                DbSession, ClientCheck.ClientID
            )
            if NeedsResolution:
                session.clear()
                session["ClientIDForResolution"] = ClientCheck.ClientID
                session["ResolutionProblems"] = Problems
                Flash(
                    "حساب کاربری شما دارای اطلاعات ناقص یا نامعتبر است. لطفا برای ادامه، اطلاعات خواسته‌شده را تکمیل و اصلاح نمایید.",
                    "Error",
                )
                return ReDirect(URLFor("ResolveDataIssues"))

            session.clear()
            session["ClientID"] = ClientCheck.ClientID
            session.permanent = True
            Flash("شما با موفقیت وارد شدید.", "Success")
            return ReDirect(NextURLFromForm or URLFor("Dashboard"))

    return RenderTemplate(
        Constants.ClientHTMLNamesData["Login"], next_url=NextURL or ""
    )


@App.FlaskApp.route("/MyHistory")
@App.LoginRequired
def MyHistory():
    with Database.GetDBSession() as db:

        return RenderTemplate(
            Constants.ClientHTMLNamesData["MyHistory"],
            Payments=[
                {
                    "PaymentID": p.PaymentID,
                    "TeamName": TeamName,
                    "Amount": p.Amount,
                    "UploadDate": p.UploadDate,
                    "Status": p.Status,
                    "ReceiptFilename": p.ReceiptFilename,
                    "ClientID": p.ClientID,
                }
                for p, TeamName in (
                    db.query(Database.Payment, Models.Team.TeamName)
                    .join(Models.Team, Database.Payment.TeamID == Database.Team.TeamID)
                    .filter(Database.Payment.ClientID == session["ClientID"])
                    .order_by(Database.Payment.UploadDate.desc())
                    .all()
                )
            ],
        )


@App.FlaskApp.route("/Team/<int:TeamID>/Update", methods=["GET", "POST"])
@App.LoginRequired
def UpdateTeam(TeamID):
    with Database.GetDBSession() as DbSession:
        Team = (
            DbSession.query(Models.Team)
            .filter(
                Models.Team.TeamID == TeamID,
                Models.Team.ClientID == session["ClientID"],
                Models.Team.Status == Models.EntityStatus.Active,
            )
            .first()
        )

        if not Team:
            Abort(404, "تیم مورد نظر پیدا نشد یا شما دسترسی به این تیم را ندارید")

        if Request.method == "POST":
            App.CSRF_Protector.protect()
            NewTeamName = Bleach.clean(Request.form.get("TeamName", "").strip())
            IsValid, ErrorMessage = Utils.IsValidTeamName(NewTeamName)
            if not IsValid:
                Flash(ErrorMessage, "Error")
            else:
                try:
                    ExistingTeam = (
                        DbSession.query(Models.Team)
                        .filter(
                            func.lower(Models.Team.TeamName) == func.lower(NewTeamName),
                            Models.Team.TeamID != TeamID,
                        )
                        .first()
                    )
                    if ExistingTeam:
                        Flash(
                            "تیمی با این نام از قبل وجود دارد. لطفا نام دیگری انتخاب کنید.",
                            "Error",
                        )
                    else:
                        Team.TeamName = NewTeamName
                        DbSession.commit()
                        Database.LogAction(
                            DbSession,
                            session["ClientID"],
                            f"User updated Team name for Team ID {TeamID} to '{NewTeamName}'.",
                        )
                        Flash("نام تیم با موفقیت به‌روزرسانی شد!", "Success")
                except exc.IntegrityError:
                    DbSession.rollback()
                    Flash(
                        "خطای پایگاه داده: تیمی با این نام از قبل وجود دارد.",
                        "Error",
                    )

            return ReDirect(URLFor("UpdateTeam", TeamID=TeamID))

        IsPaid = Database.CheckIfTeamIsPaid(DbSession, TeamID)
        Documents = []
        if IsPaid:
            Documents = (
                DbSession.query(Models.TeamDocument)
                .filter(Models.TeamDocument.TeamID == TeamID)
                .order_by(Models.TeamDocument.UploadDate.desc())
                .all()
            )

    return RenderTemplate(
        Constants.ClientHTMLNamesData["UpdateTeam"],
        Team=Team,
        IsPaid=IsPaid,
        Documents=Documents,
    )


@App.FlaskApp.route("/Team/<int:TeamID>/Delete", methods=["POST"])
@App.LoginRequired
def DeleteTeam(TeamID):
    App.CSRF_Protector.protect()
    with Database.GetDBSession() as DbSession:
        try:
            Team = (
                DbSession.query(Models.Team)
                .filter(
                    Models.Team.TeamID == TeamID,
                    Models.Team.ClientID == session["ClientID"],
                    Models.Team.Status == Models.EntityStatus.Active,
                )
                .first()
            )

            if not Team:
                Flash("تیم مورد نظر یافت نشد یا شما اجازه حذف آن را ندارید.", "Error")
                return ReDirect(URLFor("Dashboard"))

            if Database.HasTeamMadeAnyPayment(DbSession, TeamID):
                Flash(
                    "پس از ارسال رسید پرداخت، امکان آرشیو تیم توسط شما وجود ندارد.",
                    "Error",
                )
                return ReDirect(URLFor("Dashboard"))

            Team.Status = Models.EntityStatus.Inactive
            for Member in Team.Members:
                Member.Status = Models.EntityStatus.Withdrawn

            DbSession.commit()
            Flash(f"تیم «{Team.TeamName}» با موفقیت آرشیو شد.", "Success")

        except Exception as Error:
            DbSession.rollback()
            App.FlaskApp.logger.error(f"Error deleting Team {TeamID}: {Error}")
            Flash("خطایی در هنگام آرشیو تیم رخ داد.", "Error")

    return ReDirect(URLFor("Dashboard"))


@App.FlaskApp.route("/Team/<int:TeamID>/Members")
@App.LoginRequired
def ManageMembers(TeamID):
    with Database.GetDBSession() as DbSession:
        Team = (
            DbSession.query(Models.Team)
            .filter(
                Models.Team.TeamID == TeamID,
                Models.Team.ClientID == session["ClientID"],
                Models.Team.Status == Models.EntityStatus.Active,
            )
            .first()
        )

        if not Team:
            Abort(404, "تیم مورد نظر پیدا نشد یا شما دسترسی به این تیم را ندارید")

    return RenderTemplate(
        Constants.ClientHTMLNamesData["Members"],
        Team=Team,
        Members=(
            DbSession.query(Models.Member)
            .filter(
                Models.Member.TeamID == TeamID,
                Models.Member.Status == Models.EntityStatus.Active,
            )
            .all()
        ),
        IsPaid=Database.CheckIfTeamIsPaid(DbSession, TeamID),
        **Utils.GetFormContext(),
    )


@App.FlaskApp.route("/SupportChat")
@App.LoginRequired
def SupportChat():
    ClientUser = Utils.GetCurrentClient()
    if not ClientUser:
        Flash("خطا در بارگیری اطلاعات کاربری. لطفا دوباره وارد شوید.", "Error")
        return ReDirect(URLFor("Login"))
    return RenderTemplate(
        Constants.ClientHTMLNamesData["SupportChat"],
        User=ClientUser,
    )


@App.FlaskApp.route("/Team/<int:TeamID>/DeleteMember/<int:MemberID>", methods=["POST"])
@App.LoginRequired
def DeleteMember(TeamID, MemberID):
    App.CSRF_Protector.protect()
    try:
        with Database.GetDBSession() as DbSession:
            Team = (
                DbSession.query(Models.Team)
                .filter(
                    Models.Team.TeamID == TeamID,
                    Models.Team.ClientID == session["ClientID"],
                    Models.Team.Status == Models.EntityStatus.Active,
                )
                .first()
            )

            if not Team:
                Abort(404)

            if Database.HasTeamMadeAnyPayment(DbSession, TeamID):
                Flash("پس از ارسال رسید پرداخت، امکان حذف عضو وجود ندارد.", "Error")
                return ReDirect(URLFor("ManageMembers", TeamID=TeamID))

            MemberToDelete = (
                DbSession.query(Models.Member)
                .filter(
                    Models.Member.MemberID == MemberID,
                    Models.Member.TeamID == TeamID,
                    Models.Member.Status == Models.EntityStatus.Active,
                )
                .first()
            )

            if MemberToDelete:
                MemberName = MemberToDelete.Name
                MemberToDelete.Status = Models.EntityStatus.Withdrawn

                Database.LogAction(
                    DbSession,
                    session["ClientID"],
                    f"User marked member '{MemberName}' as withdrawn from Team ID {TeamID}.",
                )

                DbSession.commit()
                Utils.UpdateTeamStats(DbSession, TeamID)

                Flash("عضو با موفقیت به عنوان منصرف شده علامت‌گذاری شد.", "Success")
            else:
                Flash("عضو مورد نظر یافت نشد.", "Error")

    except Exception as Error:
        App.FlaskApp.logger.error(
            f"Error archiving member {MemberID} from Team {TeamID}: {Error}"
        )
        Flash("خطایی در هنگام حذف عضو رخ داد.", "Error")

    return ReDirect(URLFor("ManageMembers", TeamID=TeamID))


@App.FlaskApp.route("/GetMyChatHistory")
@App.LoginRequired
def GetMyChatHistory():
    if not session.get("ClientID"):
        return Jsonify({"Messages": []})
    with Database.GetDBSession() as db:
        return Jsonify(
            {
                "Messages": [
                    {
                        "MessageText": Message.MessageText,
                        "Timestamp": Message.Timestamp.isoformat(),
                        "Sender": Message.Sender,
                    }
                    for Message in Database.GetChatHistoryByClientID(
                        db, session.get("ClientID")
                    )
                ]
            }
        )


@App.FlaskApp.route("/Team/<int:TeamID>/UploadDocument", methods=["POST"])
@App.LoginRequired
def UploadDocument(TeamID):
    App.CSRF_Protector.protect()

    with Database.GetDBSession() as db:
        Team = (
            db.query(Models.Team)
            .filter(
                Models.Team.TeamID == TeamID,
                Models.Team.Status == Models.EntityStatus.Active,
            )
            .first()
        )

        if not Team:
            Abort(404)

        if Team.ClientID != session.get("ClientID") and not session.get(
            "AdminLoggedIn"
        ):
            Abort(403)

        if not Database.CheckIfTeamIsPaid(db, TeamID):
            Flash("شما اجازه بارگذاری مستندات برای این تیم را ندارید.", "Error")
            return ReDirect(URLFor("UpdateTeam", TeamID=TeamID))

        if "File" not in Request.files:
            Flash("فایلی برای بارگذاری انتخاب نشده است.", "Error")
            return ReDirect(URLFor("UpdateTeam", TeamID=TeamID))

        File = Request.files["File"]
        if not File or not File.filename:
            Flash("نام فایل نامعتبر است.", "Error")
            return ReDirect(URLFor("UpdateTeam", TeamID=TeamID))

        if Request.content_length > Constants.AppConfig.MaxDocumentSize:
            Flash(
                f"حجم فایل سند نباید بیشتر از {Constants.AppConfig.MaxDocumentSize / 1024 / 1024:.1f} مگابایت باشد.",
                "Error",
            )
            return ReDirect(URLFor("UpdateTeam", TeamID=TeamID))

        File.stream.seek(0)
        if not Utils.IsFileAllowed(File.stream):
            Flash("نوع فایل مجاز نیست یا فایل خراب است.", "Error")
            return ReDirect(URLFor("UpdateTeam", TeamID=TeamID))
        File.stream.seek(0)

        OriginalFilename = SecureFileName(File.filename)
        Extension = (
            OriginalFilename.rsplit(".", 1)[1].lower()
            if "." in OriginalFilename
            else ""
        )
        SecureName = f"{UUID.uuid4()}.{Extension}"

        NewDocument = Models.TeamDocument(
            TeamID=TeamID,
            ClientID=session["ClientID"],
            FileName=SecureName,
            FileType=Extension,
            UploadDate=Datetime.datetime.now(Datetime.timezone.utc),
        )

        try:
            DocumentFolder = OS.path.join(
                App.FlaskApp.config["UPLOAD_FOLDER_DOCUMENTS"], str(TeamID)
            )
            OS.makedirs(DocumentFolder, exist_ok=True)
            File.save(OS.path.join(DocumentFolder, SecureName))
            db.add(NewDocument)
            db.commit()
            Flash("مستندات با موفقیت بارگذاری شد.", "Success")
        except Exception as Error:
            db.rollback()
            App.FlaskApp.logger.error(f"Document save failed: {Error}")
            Flash("خطایی در هنگام ذخیره فایل مستندات رخ داد.", "Error")

    return ReDirect(URLFor("UpdateTeam", TeamID=TeamID))


@App.FlaskApp.route("/UploadDocuments/<int:TeamID>/<filename>")
@App.LoginRequired
def GetDocument(TeamID, filename):
    with Database.GetDBSession() as db:
        Team = (
            db.query(Models.Team.ClientID).filter(Models.Team.TeamID == TeamID).first()
        )

        if not Team or (
            Team.ClientID != session.get("ClientID")
            and not session.get("AdminLoggedIn")
        ):
            Abort(403)

    Filepath = SafeJoin(
        OS.path.join(Constants.Path.UploadsDir, "Documents", str(TeamID)), filename
    )
    if Filepath is None or not OS.path.exists(Filepath):
        Abort(404)

    return SendFromDirectory(
        OS.path.join(Constants.Path.UploadsDir, "Documents", str(TeamID)),
        filename,
        as_attachment=True,
    )


@App.FlaskApp.route("/Team/<int:TeamID>/AddMember", methods=["POST"])
@App.LoginRequired
def AddMember(TeamID):
    App.CSRF_Protector.protect()
    try:
        with Database.GetDBSession() as DbSession:
            Team = (
                DbSession.query(Models.Team)
                .filter(
                    Models.Team.TeamID == TeamID,
                    Models.Team.ClientID == session["ClientID"],
                    Models.Team.Status == Models.EntityStatus.Active,
                )
                .first()
            )

            if not Team:
                Abort(404)

            CurrentMemberCount = (
                DbSession.query(func.count(Models.Member.MemberID))
                .filter(
                    Models.Member.TeamID == TeamID,
                    Models.Member.Status == Models.EntityStatus.Active,
                )
                .scalar()
            )

            if CurrentMemberCount >= Constants.AppConfig.MaxMembersPerTeam:
                Flash("خطا: شما به حداکثر تعداد اعضای تیم رسیده‌اید.", "Error")
                return ReDirect(URLFor("ManageMembers", TeamID=TeamID))

            Success, Message = Utils.InternalAddMember(DbSession, TeamID, Request.form)

            if Success:
                MemberName = Message
                Database.LogAction(
                    DbSession,
                    session["ClientID"],
                    f"Added new member '{MemberName}' to Team ID {TeamID}.",
                )

                if Database.CheckIfTeamIsPaid(DbSession, TeamID):
                    Team.UnpaidMembersCount += 1
                    Flash(
                        "عضو جدید با موفقیت اضافه شد. لطفاً برای فعال‌سازی، هزینه عضو جدید را پرداخت نمایید.",
                        "Warning",
                    )
                else:
                    Flash("عضو با موفقیت اضافه شد!", "Success")

                DbSession.commit()
                Utils.UpdateTeamStats(DbSession, TeamID)
            else:
                Flash(Message, "Error")

    except Exception as Error:
        App.FlaskApp.logger.error(f"Error adding member to Team {TeamID}: {Error}")
        Flash("خطایی در هنگام افزودن عضو رخ داد.", "Error")

    return ReDirect(URLFor("ManageMembers", TeamID=TeamID))


@App.FlaskApp.route(
    "/Team/<int:TeamID>/EditMember/<int:MemberID>", methods=["GET", "POST"]
)
@App.LoginRequired
def EditMember(TeamID, MemberID):
    TemplateName = Constants.ClientHTMLNamesData["EditMember"]

    with Database.GetDBSession() as DbSession:
        Team = (
            DbSession.query(Models.Team)
            .filter(
                Models.Team.TeamID == TeamID,
                Models.Team.ClientID == session["ClientID"],
                Models.Team.Status == Models.EntityStatus.Active,
            )
            .first()
        )

        if not Team:
            Abort(404, "تیم مورد نظر پیدا نشد یا شما دسترسی به این تیم را ندارید")

        Member = (
            DbSession.query(Models.Member)
            .filter(
                Models.Member.MemberID == MemberID,
                Models.Member.TeamID == TeamID,
                Models.Member.Status == Models.EntityStatus.Active,
            )
            .first()
        )

        if not Member:
            Flash("عضو مورد نظر یافت نشد.", "Error")
            return ReDirect(URLFor("ManageMembers", TeamID=TeamID))

        if Request.method == "POST":
            App.CSRF_Protector.protect()

            NewName = Bleach.clean(Request.form.get("Name", "").strip())
            NewRoleValue = Request.form.get("Role", "").strip()
            NewNationalID = FaToEN(Request.form.get("NationalID", "").strip())
            NewCityName = Request.form.get("City", "").strip()
            NewProvinceName = Request.form.get("Province", "").strip()

            RoleMap = {Role.value: Role for Role in Models.MemberRole}
            NewRole = RoleMap.get(NewRoleValue)

            if (
                not NewName
                or not NewNationalID
                or not NewCityName
                or not NewProvinceName
            ):
                Flash("نام، کد ملی، استان و شهر الزامی هستند.", "Error")
                return RenderTemplate(
                    TemplateName,
                    Team=Team,
                    Member=Member,
                    FormData=Request.form,
                    **Utils.GetFormContext(),
                )

            if NewRole == Models.MemberRole.Leader:
                if Database.HasExistingLeader(
                    DbSession, TeamID, MemberIDToExclude=MemberID
                ):
                    Flash("خطا: این تیم از قبل یک سرپرست دارد.", "Error")
                    return ReDirect(
                        URLFor("EditMember", TeamID=TeamID, MemberID=MemberID)
                    )

            try:
                NewCityID = (
                    DbSession.query(Models.City.CityID)
                    .join(Models.Province)
                    .filter(
                        Models.Province.Name == NewProvinceName,
                        Models.City.Name == NewCityName,
                    )
                    .scalar()
                )

                if not NewCityID:
                    Flash("استان یا شهر انتخاب شده معتبر نیست.", "Error")
                else:
                    Member.Name = NewName
                    Member.Role = NewRole
                    Member.NationalID = NewNationalID
                    Member.CityID = NewCityID
                    DbSession.commit()

                    Utils.UpdateTeamStats(DbSession, TeamID)
                    Database.LogAction(
                        DbSession,
                        session["ClientID"],
                        f"Edited member '{NewName}' (ID: {MemberID}) in Team ID {TeamID}.",
                    )

                    Flash("اطلاعات عضو با موفقیت به‌روزرسانی شد.", "Success")
                    return ReDirect(URLFor("ManageMembers", TeamID=TeamID))

            except Exception as Error:
                DbSession.rollback()
                App.FlaskApp.logger.error(f"Error updating member {MemberID}: {Error}")
                Flash("خطایی در هنگام به‌روزرسانی اطلاعات عضو رخ داد.", "Error")

            return RenderTemplate(
                TemplateName,
                Team=Team,
                Member=Member,
                FormData=Request.form,
                **Utils.GetFormContext(),
            )

    return RenderTemplate(
        TemplateName, Team=Team, Member=Member, **Utils.GetFormContext()
    )


@App.FlaskApp.route("/ReceiptUploads/<int:ClientID>/<filename>")
@App.LoginRequired
def GetReceipt(ClientID, filename):
    if ClientID != session.get("ClientID") and not session.get("AdminLoggedIn"):
        Abort(403)
    return SendFromDirectory(
        OS.path.join(App.FlaskApp.config["UPLOAD_FOLDER_RECEIPTS"], str(ClientID)),
        filename,
    )


@App.FlaskApp.route("/CreateTeam", methods=["GET", "POST"])
@App.LoginRequired
def CreateTeam():
    with Database.GetDBSession() as DbSession:
        TeamsCount = (
            DbSession.query(Models.Team)
            .filter(
                Models.Team.ClientID == session["ClientID"],
                Models.Team.Status == Models.EntityStatus.Active,
            )
            .count()
        )
        if TeamsCount >= Constants.AppConfig.MaxTeamPerClient:
            Flash(f"شما به حداکثر تعداد تیم مجاز رسیده‌اید.", "Error")
            return ReDirect(URLFor("Dashboard"))

        if Request.method == "POST":
            App.CSRF_Protector.protect()
            TeamName = Bleach.clean(Request.form.get("TeamName", "").strip())
            FormContext = Utils.GetFormContext()

            IsValid, ErrorMessage = Utils.IsValidTeamName(TeamName)
            if not IsValid:
                Flash(ErrorMessage, "Error")
                return RenderTemplate(
                    Constants.ClientHTMLNamesData["CreateTeam"],
                    FormData=Request.form,
                    **FormContext,
                )

            FirstMemberData, Error = Utils.CreateMemberFromFormData(
                DbSession, Request.form
            )
            if Error:
                Flash(Error, "Error")
                return RenderTemplate(
                    Constants.ClientHTMLNamesData["CreateTeam"],
                    FormData=Request.form,
                    **FormContext,
                )

            try:
                RegDate = Datetime.datetime.now(Datetime.timezone.utc)
                NewTeam = Models.Team(
                    ClientID=session["ClientID"],
                    TeamName=TeamName,
                    TeamRegistrationDate=RegDate,
                )
                DbSession.add(NewTeam)
                DbSession.flush()

                NewMember = Models.Member(TeamID=NewTeam.TeamID, **FirstMemberData)
                DbSession.add(NewMember)
                DbSession.commit()

                Utils.UpdateTeamStats(DbSession, NewTeam.TeamID)

                Flash(f"تیم «{TeamName}» با موفقیت ساخته شد!", "Success")
                return ReDirect(URLFor("Dashboard"))
            except exc.IntegrityError:
                DbSession.rollback()
                Flash(
                    "تیمی با این نام از قبل وجود دارد. لطفا نام دیگری انتخاب کنید.",
                    "Error",
                )
                return RenderTemplate(
                    Constants.ClientHTMLNamesData["CreateTeam"],
                    FormData=Request.form,
                    **FormContext,
                )

    FormContext = Utils.GetFormContext()
    return RenderTemplate(Constants.ClientHTMLNamesData["CreateTeam"], **FormContext)


@App.FlaskApp.route("/Team/<int:TeamID>/SelectLeague", methods=["GET", "POST"])
@App.LoginRequired
def SelectLeague(TeamID):
    with Database.GetDBSession() as DbSession:
        Team = (
            DbSession.query(Models.Team)
            .filter(
                Models.Team.TeamID == TeamID,
                Models.Team.ClientID == session["ClientID"],
                Models.Team.Status == Models.EntityStatus.Active,
            )
            .first()
        )

        if not Team:
            Abort(404, "تیم پیدا نشد")

        if Database.HasTeamMadeAnyPayment(DbSession, TeamID):
            Flash(
                "از آنجایی که برای این تیم رسید پرداخت ارسال شده است، امکان تغییر لیگ‌ها وجود ندارد.",
                "Warning",
            )
            return ReDirect(URLFor("Dashboard"))

        if Request.method == "POST":
            App.CSRF_Protector.protect()
            LeagueOneID = Request.form.get("LeagueOne")
            LeagueTwoID = Request.form.get("LeagueTwo")

            if not LeagueOneID:
                Flash("لطفاً لیگ اول (اجباری) را انتخاب کنید.", "Error")
                return ReDirect(URLFor("SelectLeague", TeamID=TeamID))

            if LeagueTwoID and LeagueOneID == LeagueTwoID:
                Flash("شما نمی‌توانید یک لیگ را دو بار انتخاب کنید.", "Error")
                return ReDirect(URLFor("SelectLeague", TeamID=TeamID))

            Team.LeagueOneID = int(LeagueOneID) if LeagueOneID else None
            Team.LeagueTwoID = int(LeagueTwoID) if LeagueTwoID else None

            DbSession.commit()
            Flash("لیگ‌های تیم با موفقیت به‌روزرسانی شد.", "Success")
            return ReDirect(URLFor("Dashboard"))

    return RenderTemplate(
        Constants.ClientHTMLNamesData["SelectLeague"],
        Team=Team,
        Leagues=Constants.LeaguesListData,
    )


@App.FlaskApp.route("/Verify", methods=["GET", "POST"])
def Verify():
    if Request.method == "POST":
        App.CSRF_Protector.protect()
        Action = Request.form.get("Action")

        if Action == "phone_signup":
            ClientID = Request.form.get("ClientID")
            with Database.GetDBSession() as DbSession:
                Client = (
                    DbSession.query(Models.Client)
                    .filter(Models.Client.ClientID == ClientID)
                    .first()
                )
                if Client and Client.PhoneVerificationCode == Request.form.get("Code"):
                    if (
                        Datetime.datetime.now(Datetime.timezone.utc)
                        - Client.VerificationCodeTimestamp
                    ).total_seconds() > 900:
                        Flash(
                            "کد تایید منقضی شده است. لطفا دوباره درخواست دهید.", "Error"
                        )
                        return ReDirect(
                            URLFor("Verify", Action="phone_signup", ClientID=ClientID)
                        )

                    Client.IsPhoneVerified = 1
                    Client.PhoneVerificationCode = None
                    DbSession.commit()
                    Flash(
                        "شماره موبایل شما با موفقیت تایید شد! اکنون می‌توانید وارد شوید.",
                        "Success",
                    )
                    return ReDirect(URLFor("Login"))
                else:
                    Flash("کد وارد شده صحیح نمی باشد.", "Error")
                    return ReDirect(
                        URLFor("Verify", Action="phone_signup", ClientID=ClientID)
                    )

        elif Action == "password_reset":
            Identifier = Request.form.get("Identifier")
            IdentifierType = Request.form.get("IdentifierType")
            with Database.GetDBSession() as db:
                ResetRecord = (
                    db.query(Models.PasswordReset)
                    .filter(
                        Models.PasswordReset.Identifier == Identifier,
                        Models.PasswordReset.IdentifierType == IdentifierType,
                        Models.PasswordReset.Code == Request.form.get("Code"),
                    )
                    .first()
                )
                if ResetRecord:
                    if (
                        Datetime.datetime.now(Datetime.timezone.utc)
                        - ResetRecord.Timestamp
                    ).total_seconds() > 900:
                        db.delete(ResetRecord)
                        db.commit()
                        Flash("کد منقضی شده است. لطفا دوباره درخواست دهید.", "Error")
                        return ReDirect(URLFor("ForgotPassword"))

                    NewToken = Secrets.token_urlsafe(32)
                    ResetRecord.Code = NewToken
                    ResetRecord.Timestamp = Datetime.datetime.now(Datetime.timezone.utc)
                    db.commit()
                    return ReDirect(URLFor("ResetPassword", Token=NewToken))
                else:
                    Flash("کد وارد شده صحیح نمی باشد.", "Error")
                    return ReDirect(
                        URLFor(
                            "Verify",
                            Action="password_reset",
                            Identifier=Identifier,
                            IdentifierType=IdentifierType,
                        )
                    )

        Flash("عملیات نامعتبر است.", "Error")
        return ReDirect(URLFor("Login"))

    Action = Request.args.get("Action")
    Context = {"Action": Action, "Cooldown": 0}

    if Action == "phone_signup":
        ClientID = Request.args.get("ClientID")
        if not ClientID:
            Flash("شناسه کاربر نامعتبر است.", "Error")
            return ReDirect(URLFor("Login"))
        with Database.GetDBSession() as DbSession:
            Client = (
                DbSession.query(Models.Client)
                .filter(Models.Client.ClientID == ClientID)
                .first()
            )
            if Client and Client.VerificationCodeTimestamp:
                SecondsPassed = (
                    Datetime.datetime.now(Datetime.timezone.utc)
                    - Client.VerificationCodeTimestamp
                ).total_seconds()
                if SecondsPassed < 180:
                    Context["Cooldown"] = 180 - int(SecondsPassed)
        Context["ClientID"] = ClientID

    elif Action == "password_reset":
        Identifier = Request.args.get("Identifier")
        IdentifierType = Request.args.get("IdentifierType")
        if not Identifier or not IdentifierType:
            Flash("اطلاعات مورد نیاز برای تایید کد موجود نیست.", "Error")
            return ReDirect(URLFor("ForgotPassword"))
        with Database.GetDBSession() as db:
            ResetRecord = (
                db.query(Models.PasswordReset)
                .filter(Models.PasswordReset.Identifier == Identifier)
                .first()
            )
            if not ResetRecord:
                Flash("درخواست بازیابی یافت نشد یا منقضی شده است.", "Error")
                return ReDirect(URLFor("ForgotPassword"))
            if ResetRecord.Timestamp:
                SecondsPassed = (
                    Datetime.datetime.now(Datetime.timezone.utc) - ResetRecord.Timestamp
                ).total_seconds()
                if SecondsPassed < 180:
                    Context["Cooldown"] = 180 - int(SecondsPassed)
        Context["Identifier"] = Identifier
        Context["IdentifierType"] = IdentifierType

    else:
        Flash("صفحه مورد نظر یافت نشد.", "Error")
        return ReDirect(URLFor("Login"))

    return RenderTemplate(Constants.ClientHTMLNamesData["Verify"], **Context)


@App.FlaskApp.route("/ResendCode", methods=["POST"])
@App.limiter.limit("5 per 15 minutes")
def ResendCode():
    RequestData = Request.get_json() or {}
    Action = RequestData.get("Action")

    if not Action:
        return Jsonify({"Success": False, "Message": "عملیات نامعتبر است."}), 400

    if Action == "phone_signup":
        if not RequestData.get("ClientID"):
            return (
                Jsonify({"Success": False, "Message": "شناسه کاربر نامعتبر است."}),
                400,
            )

        with Database.GetDBSession() as DbSession:
            Client = (
                DbSession.query(Models.Client)
                .filter(Models.Client.ClientID == RequestData.get("ClientID"))
                .first()
            )
            if not Client:
                return Jsonify({"Success": False, "Message": "کاربر یافت نشد."}), 404

            if (
                Client.VerificationCodeTimestamp
                and (
                    Datetime.datetime.now(Datetime.timezone.utc)
                    - Client.VerificationCodeTimestamp
                ).total_seconds()
                < 180
            ):
                return (
                    Jsonify({"Success": False, "Message": "لطفا ۳ دقیقه صبر کنید."}),
                    429,
                )

            NewCode = "".join(Random.choices(String.digits, k=6))
            Client.PhoneVerificationCode = NewCode
            Client.VerificationCodeTimestamp = Datetime.datetime.now(
                Datetime.timezone.utc
            )
            DbSession.commit()

            Thread(
                target=Utils.SendTemplatedSMSAsync,
                args=(
                    App.FlaskApp,
                    RequestData.get("ClientID"),
                    Config.MelliPayamak["TemplateID_Verification"],
                    NewCode,
                    Config.MelliPayamak,
                ),
            ).start()

    elif Action == "password_reset":
        Identifier = RequestData.get("Identifier")
        IdentifierType = RequestData.get("IdentifierType")
        if not Identifier or not IdentifierType:
            return Jsonify({"Success": False, "Message": "اطلاعات ناقص است."}), 400

        with Database.GetDBSession() as DbSession:
            ResetRecord = (
                DbSession.query(Models.PasswordReset)
                .filter(Models.PasswordReset.Identifier == Identifier)
                .first()
            )
            if (
                ResetRecord
                and ResetRecord.Timestamp
                and (
                    Datetime.datetime.now(Datetime.timezone.utc) - ResetRecord.Timestamp
                ).total_seconds()
                < 180
            ):
                return (
                    Jsonify({"Success": False, "Message": "لطفا ۳ دقیقه صبر کنید."}),
                    429,
                )

            Client = Database.GetClientBy(DbSession, IdentifierType, Identifier)
            if not Client:
                return Jsonify({"Success": False, "Message": "کاربر یافت نشد."}), 404

            NewCode = "".join(Random.choices(String.digits, k=6))
            if ResetRecord:
                ResetRecord.Code = NewCode
                ResetRecord.Timestamp = Datetime.datetime.now(Datetime.timezone.utc)
            else:
                NewResetRecord = Models.PasswordReset(
                    Identifier=Identifier,
                    IdentifierType=IdentifierType,
                    Code=NewCode,
                    Timestamp=Datetime.datetime.now(Datetime.timezone.utc),
                )
                DbSession.add(NewResetRecord)
            DbSession.commit()

            if IdentifierType == "Email":
                Subject = "کد بازیابی رمز عبور آیروکاپ"
                Body = f"کد بازیابی رمز عبور شما: {NewCode}"
                Thread(
                    target=Utils.SendAsyncEmail,
                    args=(
                        App.FlaskApp,
                        Client.ClientID,
                        Subject,
                        Body,
                        Config.MailConfiguration,
                    ),
                ).start()
            elif IdentifierType == "PhoneNumber":
                Thread(
                    target=Utils.SendTemplatedSMSAsync,
                    args=(
                        App.FlaskApp,
                        Client.ClientID,
                        Config.MelliPayamak["TemplateID_PasswordReset"],
                        NewCode,
                        Config.MelliPayamak,
                    ),
                ).start()

    else:
        return Jsonify({"Success": False, "Message": "عملیات ناشناخته است."}), 400

    return Jsonify({"Success": True, "Message": "کد جدید ارسال شد."})


@App.FlaskApp.route("/ForgotPassword", methods=["GET", "POST"])
@App.limiter.limit("5 per 15 minutes")
def ForgotPassword():
    if Request.method == "POST":
        App.CSRF_Protector.protect()
        Identifier = FaToEN(Request.form.get("Identifier", "").strip())
        IdentifierType = (
            "Email"
            if Utils.IsValidEmail(Identifier)
            else "PhoneNumber" if Utils.IsValidIranianPhone(Identifier) else None
        )

        SuccessMessage = "اگر کاربری با این مشخصات در سیستم وجود داشته باشد، کد بازیابی برایتان ارسال خواهد شد."

        if not IdentifierType:
            Flash("لطفا یک ایمیل یا شماره موبایل معتبر وارد کنید.", "Error")
            return ReDirect(URLFor("ForgotPassword"))

        with Database.GetDBSession() as DbSession:
            ClientCheck = Database.GetClientBy(DbSession, IdentifierType, Identifier)

            if ClientCheck:
                ResetCode = "".join(Random.choices(String.digits, k=6))
                Timestamp = Datetime.datetime.now(Datetime.timezone.utc)

                ResetRecord = (
                    DbSession.query(Models.PasswordReset)
                    .filter(Models.PasswordReset.Identifier == Identifier)
                    .first()
                )
                if ResetRecord:
                    ResetRecord.Code = ResetCode
                    ResetRecord.Timestamp = Timestamp
                else:
                    NewResetRecord = Models.PasswordReset(
                        Identifier=Identifier,
                        IdentifierType=IdentifierType,
                        Code=ResetCode,
                        Timestamp=Timestamp,
                    )
                    DbSession.add(NewResetRecord)
                DbSession.commit()

                if IdentifierType == "Email":
                    Subject = "بازیابی رمز عبور آیروکاپ"
                    Body = f"کد بازیابی رمز عبور شما در آیروکاپ: {ResetCode}"
                    Thread(
                        target=Utils.SendAsyncEmail,
                        args=(
                            App.FlaskApp,
                            ClientCheck.ClientID,
                            Subject,
                            Body,
                            Config.MailConfiguration,
                        ),
                    ).start()

                elif IdentifierType == "PhoneNumber":
                    Thread(
                        target=Utils.SendTemplatedSMSAsync,
                        args=(
                            App.FlaskApp,
                            ClientCheck.ClientID,
                            Config.MelliPayamak["TemplateID_PasswordReset"],
                            ResetCode,
                            Config.MelliPayamak,
                        ),
                    ).start()

            Flash(SuccessMessage, "Info")
            return ReDirect(
                URLFor(
                    "Verify",
                    Action="password_reset",
                    Identifier=Identifier,
                    IdentifierType=IdentifierType,
                )
            )

    return RenderTemplate(Constants.ClientHTMLNamesData["ForgotPassword"])


@App.FlaskApp.route("/ResendPasswordCode", methods=["POST"])
@App.limiter.limit("5 per 15 minutes")
def ResendPasswordCode():
    RequestData = Request.get_json() or {}
    Identifier = RequestData.get("Identifier")
    IdentifierType = RequestData.get("IdentifierType")

    if not Identifier or not IdentifierType:
        return Jsonify({"Success": False, "Message": "اطلاعات ناقص است."}), 400

    with Database.GetDBSession() as DbSession:
        ResetRecord = (
            DbSession.query(Models.PasswordReset)
            .filter(Models.PasswordReset.Identifier == Identifier)
            .first()
        )

        if ResetRecord and ResetRecord.Timestamp:
            if (
                Datetime.datetime.now(Datetime.timezone.utc) - ResetRecord.Timestamp
            ).total_seconds() < 180:
                return (
                    Jsonify({"Success": False, "Message": "لطفا ۳ دقیقه صبر کنید."}),
                    429,
                )

        Client = Database.GetClientBy(DbSession, IdentifierType, Identifier)
        if not Client:
            return Jsonify({"Success": False, "Message": "کاربر یافت نشد."}), 404

        NewCode = "".join(Random.choices(String.digits, k=6))

        if ResetRecord:
            ResetRecord.Code = NewCode
            ResetRecord.Timestamp = Datetime.datetime.now(Datetime.timezone.utc)
        else:
            NewResetRecord = Models.PasswordReset(
                Identifier=Identifier,
                IdentifierType=IdentifierType,
                Code=NewCode,
                Timestamp=Datetime.datetime.now(Datetime.timezone.utc),
            )
            DbSession.add(NewResetRecord)

        DbSession.commit()

        if IdentifierType == "Email":
            Subject = "بازیابی رمز عبور آیروکاپ"
            Body = f"کد بازیابی رمز عبور شما در آیروکاپ: {NewCode}"
            Thread(
                target=Utils.SendAsyncEmail,
                args=(
                    App.FlaskApp,
                    Client.ClientID,
                    Subject,
                    Body,
                    Config.MailConfiguration,
                ),
            ).start()
        elif IdentifierType == "PhoneNumber":
            Thread(
                target=Utils.SendTemplatedSMSAsync,
                args=(
                    App.FlaskApp,
                    Client.ClientID,
                    Config.MelliPayamak["TemplateID_PasswordReset"],
                    NewCode,
                    Config.MelliPayamak,
                ),
            ).start()

    return Jsonify({"Success": True, "Message": "کد جدید ارسال شد."})


@App.FlaskApp.route("/ResendVerificationCode", methods=["POST"])
@App.limiter.limit("5 per 15 minutes")
def ResendVerificationCode():
    RequestData = Request.get_json() or {}
    ClientID = RequestData.get("ClientID")

    if not ClientID:
        return Jsonify({"Success": False, "Message": "خطای کلاینت."}), 400

    with Database.GetDBSession() as DbSession:
        Client = (
            DbSession.query(Models.Client)
            .filter(Models.Client.ClientID == ClientID)
            .first()
        )
        if not Client:
            return Jsonify({"Success": False, "Message": "کاربر یافت نشد."}), 404
        if Client.VerificationCodeTimestamp:
            if (
                Datetime.datetime.now(Datetime.timezone.utc)
                - Client.VerificationCodeTimestamp
            ).total_seconds() < 180:
                return (
                    Jsonify({"Success": False, "Message": "لطفا ۳ دقیقه صبر کنید."}),
                    429,
                )

        NewCode = "".join(Random.choices(String.digits, k=6))
        Client.PhoneVerificationCode = NewCode
        Client.VerificationCodeTimestamp = Datetime.datetime.now(Datetime.timezone.utc)
        DbSession.commit()

    Thread(
        target=Utils.SendTemplatedSMSAsync,
        args=(
            App.FlaskApp,
            ClientID,
            Config.MelliPayamak["TemplateID_Verification"],
            NewCode,
            Config.MelliPayamak,
        ),
    ).start()

    return Jsonify({"Success": True, "Message": "کد جدید ارسال شد."})


@App.FlaskApp.route("/ResetPassword", methods=["GET", "POST"])
def ResetPassword():
    Token = Request.args.get("Token")
    if not Token:
        Flash("توکن بازیابی نامعتبر است یا وجود ندارد.", "Error")
        return ReDirect(URLFor("ForgotPassword"))

    if Request.method == "POST":
        App.CSRF_Protector.protect()

        NewPassword = Request.form.get("NewPassword")
        IsValid, ErrorMessage = Utils.IsValidPassword(NewPassword)
        if not IsValid:
            Flash(ErrorMessage, "Error")
            return ReDirect(URLFor("ResetPassword", Token=Token))

        with Database.GetDBSession() as DbSession:
            ValidRecord = (
                DbSession.query(Models.PasswordReset)
                .filter(Models.PasswordReset.Code == Token)
                .first()
            )

            if not ValidRecord:
                Flash("توکن بازیابی نامعتبر است یا قبلا استفاده شده است.", "Error")
                return ReDirect(URLFor("ForgotPassword"))

            if (
                Datetime.datetime.now(Datetime.timezone.utc) - ValidRecord.Timestamp
            ).total_seconds() > 900:
                DbSession.delete(ValidRecord)
                DbSession.commit()
                Flash("توکن بازیابی منقضی شده است. لطفا دوباره درخواست دهید.", "Error")
                return ReDirect(URLFor("ForgotPassword"))

            ClientToUpdate = Database.GetClientBy(
                DbSession, ValidRecord.IdentifierType, ValidRecord.Identifier
            )
            if ClientToUpdate:
                HashedPassword = BCrypt.hashpw(
                    NewPassword.encode("utf-8"), BCrypt.gensalt()
                )
                ClientToUpdate.Password = HashedPassword.decode("utf-8")
                DbSession.delete(ValidRecord)
                DbSession.commit()

                Flash("رمز عبور شما با موفقیت تغییر یافت.", "Success")
                return ReDirect(URLFor("Login"))
            else:
                DbSession.delete(ValidRecord)
                DbSession.commit()
                Flash("کاربر مرتبط با این توکن یافت نشد.", "Error")
                return ReDirect(URLFor("ForgotPassword"))

    return RenderTemplate(Constants.ClientHTMLNamesData["ResetPassword"], Token=Token)


@App.FlaskApp.route("/Team/<int:TeamID>/Payment", methods=["GET", "POST"])
@App.LoginRequired
def Payment(TeamID):
    with Database.GetDBSession() as DbSession:
        Team = (
            DbSession.query(Models.Team)
            .filter(
                Models.Team.TeamID == TeamID,
                Models.Team.ClientID == session["ClientID"],
                Models.Team.Status == Models.EntityStatus.Active,
            )
            .first()
        )

        if not Team:
            Abort(404, "تیم پیدا نشد")

        if Request.method == "POST":
            App.CSRF_Protector.protect()
            ReceiptFile = Request.files.get("receipt")
            if not ReceiptFile or ReceiptFile.filename == "":
                Flash("لطفا فایل رسید پرداخت را انتخاب کنید.", "Error")
                return ReDirect(Request.url)

            if Request.content_length > Constants.AppConfig.MaxImageSize:
                Flash(
                    f"حجم فایل رسید نباید بیشتر از {Constants.AppConfig.MaxImageSize / 1024 / 1024:.1f} مگابایت باشد.",
                    "Error",
                )
                return ReDirect(Request.url)

            ReceiptFile.stream.seek(0)
            if not Utils.IsFileAllowed(ReceiptFile.stream):
                Flash("نوع فایل مجاز نیست یا فایل خراب است.", "Error")
                return ReDirect(Request.url)
            ReceiptFile.stream.seek(0)

            Filename = SecureFileName(ReceiptFile.filename)
            Extension = Filename.rsplit(".", 1)[1].lower() if "." in Filename else ""
            SecureName = f"{UUID.uuid4()}.{Extension}"

            TotalCost = 0
            MembersToPayFor = 0
            if Database.CheckIfTeamIsPaid(DbSession, TeamID):
                MembersToPayFor = Team.UnpaidMembersCount
                if MembersToPayFor == 0:
                    Flash("عضو جدیدی برای پرداخت وجود ندارد.", "Info")
                    return ReDirect(URLFor("Dashboard"))
                TotalCost = MembersToPayFor * Config.PaymentConfig["FeePerPerson"]
            else:
                MemberCount = (
                    DbSession.query(Models.Member)
                    .filter(
                        Models.Member.TeamID == TeamID,
                        Models.Member.Status == Models.EntityStatus.Active,
                    )
                    .count()
                )
                MembersToPayFor = MemberCount
                MembersFee = MemberCount * Config.PaymentConfig["FeePerPerson"]
                TotalCost = Config.PaymentConfig["FeeTeam"] + MembersFee

                if Team.LeagueTwoID:
                    DiscountPercent = Config.PaymentConfig["LeagueTwoDiscount"] / 100
                    DiscountedMembersFee = MembersFee * (1 - DiscountPercent)
                    TotalCost = (
                        Config.PaymentConfig["FeeTeam"]
                        + MembersFee
                        + DiscountedMembersFee
                    )

            NewPayment = Models.Payment(
                TeamID=TeamID,
                ClientID=session["ClientID"],
                Amount=TotalCost,
                MembersPaidFor=MembersToPayFor,
                ReceiptFilename=SecureName,
                UploadDate=Datetime.datetime.now(Datetime.timezone.utc),
                Status=Models.PaymentStatus.Pending,
            )
            DbSession.add(NewPayment)

            try:
                UserReceiptsFolder = OS.path.join(
                    App.FlaskApp.config["UPLOAD_FOLDER_RECEIPTS"],
                    str(session["ClientID"]),
                )
                OS.makedirs(UserReceiptsFolder, exist_ok=True)
                ReceiptFile.save(OS.path.join(UserReceiptsFolder, SecureName))
            except Exception as Error:
                DbSession.rollback()
                App.FlaskApp.logger.error(f"File save failed for payment: {Error}")
                Flash(
                    "خطایی در هنگام ذخیره فایل رسید رخ داد. لطفا دوباره تلاش کنید.",
                    "Error",
                )
                return ReDirect(Request.url)
            else:
                DbSession.commit()
                Flash(
                    "متشکریم! رسید شما با موفقیت بارگذاری و برای بررسی ارسال شد.",
                    "Success",
                )
                return ReDirect(URLFor("Dashboard"))

        if Database.CheckIfTeamIsPaid(DbSession, TeamID):
            UnpaidMembersCount = Team.UnpaidMembersCount
            if UnpaidMembersCount == 0:
                Flash("در حال حاضر عضو جدیدی برای پرداخت وجود ندارد.", "Info")
                return ReDirect(URLFor("Dashboard"))
            TotalFee = UnpaidMembersCount * Config.PaymentConfig["FeePerPerson"]
            Context = {
                "IsNewMemberPayment": True,
                "MembersToPayFor": UnpaidMembersCount,
                "TotalFee": TotalFee,
            }
        else:
            NumMembers = (
                DbSession.query(Models.Member)
                .filter(
                    Models.Member.TeamID == TeamID,
                    Models.Member.Status == Models.EntityStatus.Active,
                )
                .count()
            )

            MembersFee = NumMembers * Config.PaymentConfig["FeePerPerson"]
            LeagueOneCost = MembersFee + Config.PaymentConfig["FeeTeam"]
            TotalFee = LeagueOneCost
            LeagueTwoCost, DiscountAmount = 0, 0

            if Team.LeagueTwoID:
                DiscountAmount = MembersFee * (
                    Config.PaymentConfig["LeagueTwoDiscount"] / 100
                )
                LeagueTwoCost = MembersFee - DiscountAmount
                TotalFee += LeagueTwoCost

            Context = {
                "IsNewMemberPayment": False,
                "NumMembers": NumMembers,
                "TotalFee": TotalFee,
                "LeagueOneCost": LeagueOneCost,
                "LeagueTwoCost": LeagueTwoCost,
                "DiscountAmount": DiscountAmount,
            }

    return RenderTemplate(
        Constants.ClientHTMLNamesData["Payment"], Team=Team, **Context
    )


@App.FlaskApp.route("/Dashboard")
@App.LoginRequired
def Dashboard():
    with Database.GetDBSession() as DbSession:
        Teams = (
            DbSession.query(Models.Team)
            .options(subqueryload(Models.Team.Members))
            .filter(
                Models.Team.ClientID == session.get("ClientID"),
                Models.Team.Status == Models.EntityStatus.Active,
            )
            .order_by(Models.Team.TeamRegistrationDate.desc())
            .all()
        )

        TeamIDs = [Team.TeamID for Team in Teams]
        PaymentStatuses = {}

        if TeamIDs:
            Subquery = (
                select(
                    Models.Payment.TeamID,
                    Models.Payment.Status,
                    func.row_number()
                    .over(
                        partition_by=Models.Payment.TeamID,
                        order_by=Models.Payment.UploadDate.desc(),
                    )
                    .label("row_number"),
                )
                .where(Models.Payment.TeamID.in_(TeamIDs))
                .subquery()
            )

            LatestPayments = (
                DbSession.query(Subquery).filter(Subquery.c.row_number == 1).all()
            )
            PaymentStatuses = {Row.TeamID: Row.Status for Row in LatestPayments}

        for Team in Teams:
            Team.LastPaymentStatus = PaymentStatuses.get(Team.TeamID)

    return RenderTemplate(
        Constants.ClientHTMLNamesData["Dashboard"],
        Teams=Teams,
        PaymentInfo=Constants.PaymentConfig,
    )
