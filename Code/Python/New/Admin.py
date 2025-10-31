import os as OS
import math as Math
import uuid as UUID
import bcrypt as BCrypt
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
from sqlalchemy import exc, select, func
from sqlalchemy.orm import joinedload
import datetime as Datetime
import bleach as Bleach
from werkzeug.utils import secure_filename as SecureFileName
import Config
import Database
import Constants
import Models
import Utils
from persiantools.digits import fa_to_en as FaToEN
import App

AdminBlueprint = Blueprint(
    "Admin", __name__, url_prefix="/Admin", template_folder="Admin"
)


@App.FlaskApp.route("/UploadsGallery/<filename>")
def UploadedGalleryImage(filename):
    return SendFromDirectory(Constants.Path.GalleryDir, filename)


def GetAdminPersonas():
    return [Member["Name"] for Member in Constants.CommitteeMembersData] + [
        "Website Dev",
        "Admin",
    ]


@App.FlaskApp.route("/AdminLogin", methods=["GET", "POST"])
def AdminLogin():
    if Request.method == "POST":
        App.CSRF_Protector.protect()
        if BCrypt.checkpw(
            Request.form["Password"].encode("utf-8"),
            Config.AdminPasswordHash.encode("utf-8"),
        ):
            session["AdminLoggedIn"] = True
            Flash("ورود به پنل مدیریت با موفقیت انجام شد.", "Success")
            return ReDirect(URLFor("AdminDashboard"))
        else:
            Flash("رمز عبور ادمین نامعتبر است.", "Error")

    return RenderTemplate(Constants.AdminHTMLNamesData["AdminLogin"])


@App.FlaskApp.route("/Admin/GetChatHistory/<int:ClientID>")
@App.AdminRequired
def GetChatHistory(ClientID):
    with Database.get_db_session() as db:
        return Jsonify(
            {
                "Messages": [
                    {
                        "MessageText": Message.MessageText,
                        "Timestamp": Message.Timestamp.isoformat(),
                        "Sender": Message.Sender,
                    }
                    for Message in Database.GetChatHistoryByClientID(db, ClientID)
                ]
            }
        )


@App.FlaskApp.route("/API/GetChatClients")
@App.AdminRequired
def ApiGetChatClients():
    with Database.get_db_session() as db:
        ClientList = [
            {"ID": c.ClientID, "Email": c.Email}
            for c in Database.GetAllActiveClients(db)
        ]
    return Jsonify(ClientList)


@App.FlaskApp.route("/Admin/Chat/<int:ClientID>")
@App.AdminRequired
def AdminChat(ClientID):
    with Database.get_db_session() as DbSession:
        Client = Database.GetClientBy(DbSession, "ClientID", ClientID)
    if not Client or Client.Status != Models.EntityStatus.Active:
        Flash("کاربر مورد نظر یافت نشد یا غیرفعال است.", "Error")
        return ReDirect(URLFor("AdminSelectChat"))
    return RenderTemplate(
        Constants.AdminHTMLNamesData["AdminChat"],
        Client=Client,
        Personas=GetAdminPersonas(),
    )


@App.FlaskApp.route("/Admin/AddTeam/<int:ClientID>", methods=["POST"])
@App.AdminRequired
def AdminAddTeam(ClientID):
    TeamName = Bleach.clean(Request.form.get("TeamName", "").strip())

    if not TeamName:
        Flash("نام تیم نمی‌تواند خالی باشد.", "Error")
        return ReDirect(URLFor("AdminManageClient", ClientID=ClientID))

    with Database.get_db_session() as DbSession:
        try:
            NewTeam = Models.Team(
                ClientID=ClientID,
                TeamName=TeamName,
                TeamRegistrationDate=Datetime.datetime.now(Datetime.timezone.utc),
            )
            DbSession.add(NewTeam)
            DbSession.commit()
            Flash(f"تیم «{TeamName}» با موفقیت برای این کاربر ساخته شد.", "Success")
        except exc.IntegrityError:
            DbSession.rollback()
            Flash(
                "تیمی با این نام از قبل در سیستم وجود دارد. لطفا نام دیگری انتخاب کنید.",
                "Error",
            )

    return ReDirect(URLFor("AdminManageClient", ClientID=ClientID))


@App.FlaskApp.route("/Admin/Chat/Select")
@App.AdminRequired
def AdminSelectChat():
    with Database.get_db_session() as DbSession:
        ClientsQuery = (
            DbSession.query(
                Models.Client.ClientID,
                Models.Client.Email,
                func.count(Models.ChatMessage.MessageID).label("UnreadCount"),
                func.max(Models.ChatMessage.Timestamp).label("LastMessageTimestamp"),
            )
            .join(
                Models.ChatMessage,
                Models.Client.ClientID == Models.ChatMessage.ClientID,
            )
            .filter(Models.ChatMessage.Sender.notin_(GetAdminPersonas()))
            .group_by(Models.Client.ClientID)
            .order_by(func.max(Models.ChatMessage.Timestamp).desc())
        )

    return RenderTemplate(
        Constants.AdminHTMLNamesData["AdminChatList"], Clients=ClientsQuery.all()
    )


@App.FlaskApp.route("/Admin/UpdatePaymentStatus/<int:TeamID>", methods=["POST"])
@App.AdminActionRequired
def AdminUpdatePaymentStatus(TeamID):
    try:
        NewStatus = Models.PaymentStatus(Request.form.get("NewStatus"))
    except ValueError:
        Flash("وضعیت ارسالی نامعتبر است.", "Error")
        return ReDirect(URLFor("AdminManageTeams"))

    with Database.get_db_session() as DbSession:
        LatestPayment = (
            DbSession.query(Models.Payment)
            .filter(Models.Payment.TeamID == TeamID)
            .order_by(Models.Payment.UploadDate.desc())
            .first()
        )

        if not LatestPayment:
            Flash("هیچ پرداختی برای این تیم یافت نشد.", "Error")
            return ReDirect(URLFor("AdminManageTeams"))

        try:
            LatestPayment.Status = NewStatus
            DbSession.commit()
            Flash(
                f"وضعیت آخرین پرداخت تیم به '{NewStatus.value}' تغییر یافت.", "Success"
            )

        except Exception as Error:
            DbSession.rollback()
            App.FlaskApp.logger.error(
                f"Error updating payment status for Team {TeamID}: {Error}"
            )
            Flash("خطایی در هنگام به‌روزرسانی وضعیت پرداخت رخ داد.", "Error")

    return ReDirect(URLFor("AdminManageTeams"))


@App.FlaskApp.route("/Admin/DeleteTeam/<int:TeamID>", methods=["POST"])
@App.AdminActionRequired
def AdminDeleteTeam(TeamID):
    with Database.get_db_session() as DbSession:
        try:
            Team = (
                DbSession.query(Models.Team)
                .filter(Models.Team.TeamID == TeamID)
                .first()
            )
            if not Team:
                Abort(404)

            Team.Status = Models.EntityStatus.Inactive
            for Member in Team.Members:
                Member.Status = Models.EntityStatus.Withdrawn  # Status is white

            Database.LogAction(
                DbSession,
                Team.ClientID,
                f"Admin archived Team '{Team.TeamName}' (ID: {TeamID}) as withdrawn.",
                IsAdminAction=True,
            )

            DbSession.commit()
            Flash(
                f"تیم «{Team.TeamName}» با موفقیت به عنوان منصرف شده آرشیو شد.",
                "Success",
            )

        except Exception as Error:
            DbSession.rollback()
            App.FlaskApp.logger.error(
                f"Error in AdminDeleteTeam for Team {TeamID}: {Error}"
            )
            Flash("خطایی در هنگام آرشیو تیم رخ داد.", "Error")

    return ReDirect(URLFor("AdminManageClient", ClientID=Team.ClientID))


@App.FlaskApp.route(
    "/Admin/Team/<int:TeamID>/DeleteMember/<int:MemberID>", methods=["POST"]
)
@App.AdminActionRequired
def AdminDeleteMember(TeamID, MemberID):
    with Database.get_db_session() as DbSession:
        Member = (
            DbSession.query(Models.Member)
            .options(joinedload(Models.Member.Team))
            .filter(Models.Member.MemberID == MemberID, Models.Member.TeamID == TeamID)
            .first()
        )

        if not Member:
            Flash("عضو مورد نظر یافت نشد.", "Error")
            return ReDirect(URLFor("AdminEditTeam", TeamID=TeamID))

        Member.Status = Models.EntityStatus.Withdrawn

        Database.LogAction(
            DbSession,
            Member.Team.ClientID,  # ClientID is white
            f"Admin marked member '{Member.Name}' as resigned from Team ID {TeamID}.",
            IsAdminAction=True,
        )

        DbSession.commit()
        Utils.UpdateTeamStats(DbSession, TeamID)

        Flash("عضو با موفقیت به عنوان منصرف شده علامت‌گذاری و آرشیو شد.", "Success")

    return ReDirect(URLFor("AdminEditTeam", TeamID=TeamID))


@App.FlaskApp.route("/Admin/ManageNews", methods=["GET", "POST"])
@App.AdminRequired
def AdminManageNews():
    with Database.get_db_session() as DbSession:
        if Request.method == "POST":
            TemplatePath = Request.form.get("TemplatePath", "").strip()
            TitleString = Bleach.clean(Request.form.get("Title", "").strip())
            ContentString = Bleach.clean(Request.form.get("Content", "").strip())
            ImageFile = Request.files.get("Image")

            if not TitleString or not ContentString:
                Flash("عنوان و محتوای خبر نمی‌توانند خالی باشند.", "Error")
                return ReDirect(URLFor("AdminManageNews"))

            ExistingNews = (
                DbSession.query(Models.News)
                .filter(
                    func.lower(Models.News.Title) == func.lower(TitleString)
                )  # both lowers are white
                .first()
            )
            if ExistingNews:
                Flash("خبری با این عنوان از قبل وجود دارد.", "Error")
                return ReDirect(URLFor("AdminManageNews"))

            NewArticle = Models.News(
                Title=TitleString,
                Content=ContentString,
                PublishDate=Datetime.datetime.now(Datetime.timezone.utc),
                TemplatePath=TemplatePath,
            )

            if ImageFile and ImageFile.filename:
                ImageFile.stream.seek(0)
                if not Utils.IsFileAllowed(ImageFile.stream):
                    Flash("خطا: فرمت فایل تصویر مجاز نیست.", "Error")
                    return ReDirect(URLFor("AdminManageNews"))
                ImageFile.stream.seek(0)

                OriginalFileName = SecureFileName(ImageFile.filename)
                Extension = OriginalFileName.rsplit(".", 1)[-1].lower()
                NewArticle.ImagePath = f"{UUID.uuid4()}.{Extension}"

                try:
                    ImageFile.save(
                        OS.path.join(
                            App.FlaskApp.config["UPLOAD_FOLDER_NEWS"],
                            f"{UUID.uuid4()}.{Extension}",
                        )
                    )
                except Exception as Error:
                    App.FlaskApp.logger.error(f"News image save failed: {Error}")
                    Flash("خطا در ذخیره تصویر خبر.", "Error")
                    return ReDirect(URLFor("AdminManageNews"))

            try:
                DbSession.add(NewArticle)
                DbSession.commit()
                Flash("خبر جدید با موفقیت اضافه شد.", "Success")
            except exc.IntegrityError:
                DbSession.rollback()
                Flash("خبری با این عنوان از قبل وجود دارد.", "Error")
            except Exception as Error:
                DbSession.rollback()
                App.FlaskApp.logger.error(f"Error creating news: {Error}")
                Flash("خطایی در ایجاد خبر رخ داد.", "Error")

            return ReDirect(URLFor("AdminManageNews"))

        ArticlesList = Database.GetAllArticles(DbSession)
    return RenderTemplate(
        Constants.AdminHTMLNamesData["AdminManageNews"], Articles=ArticlesList
    )


@App.FlaskApp.route("/Admin/EditNews/<int:ArticleID>", methods=["GET", "POST"])
@App.AdminRequired
def AdminEditNews(ArticleID):
    with Database.get_db_session() as DbSession:
        Article = Database.GetArticleByID(DbSession, ArticleID)
        if not Article:
            Abort(404)

        if Request.method == "POST":
            try:
                Article.TemplatePath = Request.form.get("TemplatePath", "").strip()
                NewTitle = Bleach.clean(Request.form.get("Title", "").strip())
                Article.Content = Bleach.clean(Request.form.get("Content", "").strip())

                if NewTitle != Article.Title:
                    ExistingNews = (
                        DbSession.query(Models.News)
                        .filter(
                            func.lower(Models.News.Title)
                            == func.lower(NewTitle),  # both lowers is white
                            Models.News.NewsID != ArticleID,
                        )
                        .first()
                    )
                    if ExistingNews:
                        Flash("خبری با این عنوان از قبل وجود دارد.", "Error")
                        return ReDirect(URLFor("AdminEditNews", ArticleID=ArticleID))
                    Article.Title = NewTitle

                ImageFile = Request.files.get("Image")
                if ImageFile and ImageFile.filename:
                    ImageFile.stream.seek(0)
                    if not Utils.IsFileAllowed(ImageFile.stream):
                        Flash("خطا: فرمت فایل تصویر مجاز نیست.", "Error")
                        return ReDirect(URLFor("AdminEditNews", ArticleID=ArticleID))
                    ImageFile.stream.seek(0)

                    OriginalFileName = SecureFileName(ImageFile.filename)
                    Extension = OriginalFileName.rsplit(".", 1)[-1].lower()
                    SecureName = f"{UUID.uuid4()}.{Extension}"
                    NewImagePath = OS.path.join(
                        App.FlaskApp.config["UPLOAD_FOLDER_NEWS"], SecureName
                    )

                    OldImagePath = None
                    if Article.ImagePath:
                        OldImagePath = OS.path.join(
                            App.FlaskApp.config["UPLOAD_FOLDER_NEWS"],
                            Article.ImagePath,
                        )

                    ImageFile.save(NewImagePath)

                    if OldImagePath and OS.path.exists(OldImagePath):
                        OS.remove(OldImagePath)

                    Article.ImagePath = SecureName

                DbSession.commit()
                Flash("خبر با موفقیت ویرایش شد.", "Success")
                return ReDirect(URLFor("AdminManageNews"))

            except Exception as Error:
                DbSession.rollback()
                App.FlaskApp.logger.error(f"Error editing news {ArticleID}: {Error}")
                Flash("خطایی در ویرایش خبر رخ داد.", "Error")
                return ReDirect(URLFor("AdminEditNews", ArticleID=ArticleID))

    return RenderTemplate(
        Constants.AdminHTMLNamesData["AdminEditNews"], Article=Article
    )


@App.FlaskApp.route("/Admin/ManageClient/<int:ClientID>")
@App.AdminRequired
def AdminManageClient(ClientID):
    with Database.get_db_session() as DbSession:
        Client = (
            DbSession.query(Models.Client)
            .filter(Models.Client.ClientID == ClientID)
            .first()
        )
        if not Client:
            Abort(404, "کاربر مورد نظر یافت نشد.")

        LatestPaymentSubquery = (
            select(Models.Payment.Status)
            .where(Models.Payment.TeamID == Models.Team.TeamID)
            .order_by(Models.Payment.UploadDate.desc())
            .limit(1)
            .scalar_subquery()
            .label("LastPaymentStatus")
        )

        TeamsQuery = (
            DbSession.query(
                Models.Team,
                func.count(Models.Member.MemberID).label("TotalMembers"),
                LatestPaymentSubquery,
            )
            .outerjoin(
                Models.Member,
                (Models.Member.TeamID == Models.Team.TeamID)
                & (Models.Member.Status == Models.EntityStatus.Active),
            )
            .filter(
                Models.Team.ClientID == ClientID,
                Models.Team.Status == Models.EntityStatus.Active,
            )
            .group_by(Models.Team.TeamID)
            .order_by(Models.Team.TeamRegistrationDate.desc())
            .all()
        )

        TeamsWithStatus = []
        for Team, MemberCount, LastPaymentStatus in TeamsQuery:
            Team.TotalMembers = MemberCount  # TotalMembers is white
            Team.LastPaymentStatus = LastPaymentStatus  # LastPaymentStatus is white
            TeamsWithStatus.append(Team)

    return RenderTemplate(
        Constants.AdminHTMLNamesData["AdminManageClient"],
        Client=Client,
        Teams=TeamsWithStatus,
    )


@App.FlaskApp.route("/Admin/ManageTeams")
@App.AdminRequired
def AdminManageTeams():
    with Database.get_db_session() as DbSession:
        Subquery = (
            select(Models.Payment.Status)
            .where(Models.Payment.TeamID == Models.Team.TeamID)
            .order_by(Models.Payment.UploadDate.desc())
            .limit(1)
            .scalar_subquery()
        )

        AllTeams = (
            DbSession.query(
                Models.Team.TeamID,
                Models.Team.TeamName,
                Models.Client.Email.label("ClientEmail"),
                func.count(Models.Member.MemberID).label("MemberCount"),
                Subquery.label("LastPaymentStatus"),
            )
            .join(Models.Client, Models.Team.ClientID == Models.Client.ClientID)
            .outerjoin(
                Models.Member,
                (Models.Team.TeamID == Models.Member.TeamID)
                & (Models.Member.Status == Models.EntityStatus.Active),
            )
            .filter(Models.Team.Status == Models.EntityStatus.Active)
            .group_by(Models.Team.TeamID)
            .order_by(Models.Team.TeamRegistrationDate.desc())
            .all()
        )

    return RenderTemplate(
        Constants.AdminHTMLNamesData["AdminManageTeams"], Teams=AllTeams
    )


@App.FlaskApp.route("/Admin/Team/<int:TeamID>/AddMember", methods=["GET", "POST"])
@App.AdminRequired
def AdminAddMember(TeamID):
    with Database.get_db_session() as DbSession:
        Team = Database.GetTeamByID(DbSession, TeamID)
        if not Team:
            Abort(404)

        if Request.method == "POST":
            App.CSRF_Protector.protect()
            try:
                Success, Message = Utils.InternalAddMember(
                    DbSession, TeamID, Request.form
                )
                if Success:
                    if Database.CheckIfTeamIsPaid(DbSession, TeamID):
                        Team.UnpaidMembersCount += 1
                        Flash(
                            "عضو جدید با موفقیت اضافه شد. (توجه: تیم پرداخت‌شده است، هزینه عضو جدید باید محاسبه شود).",
                            "Warning",
                        )
                    else:
                        Flash("عضو جدید با موفقیت توسط ادمین اضافه شد.", "Success")

                    DbSession.commit()
                    Utils.UpdateTeamStats(DbSession, TeamID)
                    return ReDirect(URLFor("AdminEditTeam", TeamID=TeamID))
                else:
                    Flash(Message, "Error")
            except Exception as Error:
                DbSession.rollback()
                App.FlaskApp.logger.error(
                    f"Error in AdminAddMember for Team {TeamID}: {Error}"
                )
                Flash("خطایی در هنگام افزودن عضو رخ داد.", "Error")

    FormContext = Utils.GetFormContext()
    return RenderTemplate(
        Constants.AdminHTMLNamesData["AdminAddMember"], Team=Team, **FormContext
    )


@App.FlaskApp.route("/Admin/EditTeam/<int:TeamID>", methods=["GET", "POST"])
@App.AdminRequired
def AdminEditTeam(TeamID):
    with Database.get_db_session() as DbSession:
        Team = DbSession.query(Models.Team).filter(Models.Team.TeamID == TeamID).first()
        if not Team:
            Abort(404)

        if Request.method == "POST":
            try:
                NewTeamName = Bleach.clean(Request.form.get("TeamName", "").strip())
                LeagueOneID = Request.form.get("LeagueOneID")
                LeagueTwoID = Request.form.get("LeagueTwoID")

                IsValid, ErrorMessage = Utils.IsValidTeamName(NewTeamName)
                if not IsValid:
                    Flash(ErrorMessage, "Error")
                else:
                    ExistingTeam = (
                        DbSession.query(Models.Team)
                        .filter(
                            func.lower(Models.Team.TeamName) == func.lower(NewTeamName),
                            Models.Team.TeamID != TeamID,
                        )
                        .first()
                    )
                    if ExistingTeam:
                        Flash("تیمی با این نام از قبل وجود دارد.", "Error")
                    else:
                        Team.TeamName = NewTeamName
                        Team.LeagueOneID = int(LeagueOneID) if LeagueOneID else None
                        Team.LeagueTwoID = int(LeagueTwoID) if LeagueTwoID else None
                        DbSession.commit()
                        Utils.UpdateTeamStats(DbSession, TeamID)
                        Flash("جزئیات تیم با موفقیت ذخیره شد", "Success")

            except Exception as Error:
                DbSession.rollback()
                App.FlaskApp.logger.error(
                    f"Error in AdminEditTeam for Team {TeamID}: {Error}"
                )
                Flash("خطایی در هنگام ویرایش تیم رخ داد.", "Error")

            return ReDirect(URLFor("AdminEditTeam", TeamID=TeamID))

        Members = (
            DbSession.query(Models.Member).filter(Models.Member.TeamID == TeamID).all()
        )
        FormContext = Utils.GetFormContext()

    return RenderTemplate(
        Constants.AdminHTMLNamesData["AdminEditTeam"],
        Team=Team,
        Members=Members,
        **FormContext,
    )


@App.FlaskApp.route(
    "/Admin/Team/<int:TeamID>/EditMember/<int:MemberID>", methods=["POST"]
)
@App.AdminRequired
def AdminEditMember(TeamID, MemberID):
    with Database.get_db_session() as DbSession:
        UpdatedMemberData, Error = Utils.CreateMemberFromFormData(
            DbSession, Request.form
        )
        if Error:
            Flash(Error, "Error")
        else:
            if UpdatedMemberData["Role"] == Models.MemberRole.Leader:
                if Database.HasExistingLeader(
                    DbSession, TeamID, MemberIDToExclude=MemberID
                ):
                    Flash("خطا: این تیم از قبل یک سرپرست دارد.", "Error")
                    return ReDirect(URLFor("AdminEditTeam", TeamID=TeamID))

            MemberToUpdate = (
                DbSession.query(Models.Member)
                .filter(Models.Member.MemberID == MemberID)
                .first()
            )
            if MemberToUpdate:
                MemberToUpdate.Name = UpdatedMemberData["Name"]
                MemberToUpdate.BirthDate = UpdatedMemberData["BirthDate"]
                MemberToUpdate.NationalID = UpdatedMemberData["NationalID"]
                MemberToUpdate.Role = UpdatedMemberData["Role"]
                MemberToUpdate.CityID = UpdatedMemberData["CityID"]

                DbSession.commit()
                Utils.UpdateTeamStats(DbSession, TeamID)
                Flash("اطلاعات عضو با موفقیت ویرایش شد.", "Success")
            else:
                Flash("عضو مورد نظر برای ویرایش یافت نشد.", "Error")

    return ReDirect(URLFor("AdminEditTeam", TeamID=TeamID))


@App.FlaskApp.route("/Admin/ManageClients")
@App.AdminRequired
def AdminClientsList():
    with Database.get_db_session() as DbSession:

        return RenderTemplate(
            Constants.AdminHTMLNamesData["AdminClientsList"],
            Clients=(
                DbSession.query(Models.Client)
                .filter(Models.Client.Status == Models.EntityStatus.Active)
                .order_by(Models.Client.RegistrationDate.desc())
                .limit(10)
                .offset((Request.args.get("page", 1, type=int) - 1) * 10)
                .all()
            ),
            CurrentPage=Request.args.get("page", 1, type=int),
            TotalPagesCount=Math.ceil(
                (
                    DbSession.query(func.count(Models.Client.ClientID))
                    .filter(Models.Client.Status == Models.EntityStatus.Active)
                    .scalar()
                )
                / 10
            ),
        )


@App.FlaskApp.route("/Admin/AddClient", methods=["POST"])
@App.AdminRequired
def AdminAddClient():
    Email = Request.form.get("Email", "").strip().lower()
    Phone = Request.form.get("PhoneNumber", "").strip()
    Password = Request.form.get("Password", "")

    if not all(
        [
            Utils.IsValidEmail(Request.form.get("Email", "").strip().lower()),
            Utils.IsValidIranianPhone(Phone),
            Password,
        ]
    ):
        Flash("لطفا تمام فیلدها را با مقادیر معتبر پر کنید.", "Error")
        return ReDirect(URLFor("AdminClientsList"))

    with Database.get_db_session() as DbSession:
        try:
            if (
                DbSession.query(Models.Client)
                .filter(
                    (Models.Client.Email == Email)
                    | (Models.Client.PhoneNumber == Phone)
                )
                .first()
            ):
                Flash("کاربری با این ایمیل یا شماره تلفن از قبل وجود دارد.", "Error")
                return ReDirect(URLFor("AdminClientsList"))

            DbSession.add(
                Models.Client(
                    PhoneNumber=Phone,
                    Email=Email,
                    Password=BCrypt.hashpw(
                        Password.encode("utf-8"), BCrypt.gensalt()
                    ).decode("utf-8"),
                    RegistrationDate=Datetime.datetime.now(Datetime.timezone.utc),
                    IsPhoneVerified=1,
                )
            )
            DbSession.commit()
            Flash("کاربر جدید با موفقیت اضافه شد.", "Success")

        except exc.IntegrityError:
            DbSession.rollback()
            Flash("کاربری با این ایمیل یا شماره تلفن از قبل وجود دارد.", "Error")
        except Exception as Error:
            DbSession.rollback()
            App.FlaskApp.logger.error(f"Error adding Client: {Error}")
            Flash("خطایی در ایجاد کاربر رخ داد.", "Error")

    return ReDirect(URLFor("AdminClientsList"))


@App.FlaskApp.route("/Admin/EditClient/<int:ClientID>", methods=["POST"])
@App.AdminRequired
def AdminEditClient(ClientID):
    with Database.get_db_session() as DbSession:
        try:
            CleanData, Errors = Database.ValidateClientUpdate(
                DbSession,
                ClientID,
                Request.form,
                Utils.IsValidPassword,
                Utils.IsValidEmail,
                Utils.IsValidIranianPhone,
                FaToEN,
            )

            if Errors:
                for Error in Errors:
                    Flash(Error, "Error")
            else:
                if CleanData:
                    Database.UpdateClientDetails(DbSession, ClientID, CleanData)
                    Flash("اطلاعات کاربر با موفقیت ویرایش شد.", "Success")
                else:
                    Flash("هیچ تغییری برای ذخیره وجود نداشت.", "Info")

        except Exception as Error:
            DbSession.rollback()
            App.FlaskApp.logger.error(f"Error editing Client {ClientID}: {Error}")
            Flash("خطایی در هنگام ویرایش اطلاعات کاربر رخ داد.", "Error")

    return ReDirect(URLFor("AdminManageClient", ClientID=ClientID))


@App.FlaskApp.route("/Admin/DeleteClient/<int:ClientID>", methods=["POST"])
@App.AdminRequired
def AdminDeleteClient(ClientID):
    with Database.get_db_session() as DbSession:
        Client = (
            DbSession.query(Models.Client)
            .filter(Models.Client.ClientID == ClientID)
            .first()
        )
        if Client:
            Client.Status = Models.EntityStatus.Inactive

            for Team in (
                DbSession.query(Models.Team)
                .filter(
                    Models.Team.ClientID == ClientID,
                    Models.Team.Status == Models.EntityStatus.Active,
                )
                .all()
            ):
                Team.Status = Models.EntityStatus.Inactive

            DbSession.commit()
            Flash("کاربر و تمام تیم‌های مرتبط با او با موفقیت غیرفعال شدند.", "Success")
        else:
            Flash("کاربر یافت نشد.", "Error")
    return ReDirect(URLFor("AdminClientsList"))


@App.FlaskApp.route("/AdminDashboard")
@App.AdminRequired
def AdminDashboard():
    with Database.get_db_session() as DbSession:
        TotalClients = (
            DbSession.query(func.count(Models.Client.ClientID))
            .filter(Models.Client.Status == Models.EntityStatus.Active)
            .scalar()
        )
        TotalTeams = (
            DbSession.query(func.count(Models.Team.TeamID))
            .filter(Models.Team.Status == Models.EntityStatus.Active)
            .scalar()
        )
        ApprovedTeams = (
            DbSession.query(func.count(func.distinct(Models.Payment.TeamID)))
            .filter(Models.Payment.Status == Models.PaymentStatus.Approved)
            .scalar()
        )
        TotalMembers = (
            DbSession.query(func.count(Models.Member.MemberID))
            .filter(Models.Member.Status == Models.EntityStatus.Active)
            .scalar()
        )
        TotalLeaders = (
            DbSession.query(func.count(Models.Member.MemberID))
            .filter(
                Models.Member.Status == Models.EntityStatus.Active,
                Models.Member.Role == Models.MemberRole.Leader,
            )
            .scalar()
        )
        TotalCoaches = (
            DbSession.query(func.count(Models.Member.MemberID))
            .filter(
                Models.Member.Status == Models.EntityStatus.Active,
                Models.Member.Role == Models.MemberRole.Coach,
            )
            .scalar()
        )

        Stats = {
            "TotalClients": TotalClients,
            "TotalTeams": TotalTeams,
            "ApprovedTeams": ApprovedTeams,
            "TotalMembers": TotalMembers,
            "TotalLeaders": TotalLeaders,
            "TotalCoaches": TotalCoaches,
        }

        PendingPayments = (
            DbSession.query(Models.Payment, Models.Team.TeamName, Models.Client.Email)
            .join(Models.Team, Models.Payment.TeamID == Models.Team.TeamID)
            .join(Models.Client, Models.Payment.ClientID == Models.Client.ClientID)
            .filter(Models.Payment.Status == Models.PaymentStatus.Pending)
            .order_by(Models.Payment.UploadDate.asc())
            .all()
        )

    return RenderTemplate(
        Constants.AdminHTMLNamesData["AdminDashboard"],
        Stats=Stats,
        PendingPayments=PendingPayments,
    )


@App.FlaskApp.route("/Admin/ManagePayment/<int:PaymentID>/<Action>", methods=["POST"])
@App.AdminRequired
def AdminManagePayment(PaymentID, Action):
    if Action not in ["approve", "reject"]:
        Abort(400)

    with Database.get_db_session() as DbSession:
        try:
            Payment = (
                DbSession.query(Models.Payment)
                .filter(
                    Models.Payment.PaymentID == PaymentID,
                    Models.Payment.Status == Models.PaymentStatus.Pending,
                )
                .first()
            )

            if not Payment:
                Flash("این پرداخت قبلاً پردازش شده یا یافت نشد.", "Warning")
                return ReDirect(URLFor("AdminDashboard"))

            if Action == "approve":
                Payment.Status = Models.PaymentStatus.Approved
                DbSession.query(Models.Member).filter(
                    Models.Member.TeamID == Payment.TeamID,
                    Models.Member.Status != Models.EntityStatus.Active,
                ).update(
                    {"Status": Models.EntityStatus.Active}, synchronize_session=False
                )

                MembersJustPaidFor = Payment.MembersPaidFor
                DbSession.query(Models.Team).filter(
                    Models.Team.TeamID == Payment.TeamID
                ).update(
                    {
                        "UnpaidMembersCount": Models.Team.UnpaidMembersCount
                        - MembersJustPaidFor
                    },
                    synchronize_session=False,
                )

                Database.LogAction(
                    DbSession,
                    Payment.ClientID,
                    f"Admin Approved Payment ID {PaymentID} for Team ID {Payment.TeamID}.",
                    IsAdminAction=True,
                )
                Flash("پرداخت با موفقیت تایید شد و اعضای تیم فعال شدند.", "Success")

            elif Action == "reject":
                Payment.Status = Models.PaymentStatus.Rejected
                Database.LogAction(
                    DbSession,
                    Payment.ClientID,
                    f"Admin Rejected Payment ID {PaymentID} for Team ID {Payment.TeamID}.",
                    IsAdminAction=True,
                )
                Flash("پرداخت رد شد.", "Warning")

            DbSession.commit()

        except Exception as Error:
            DbSession.rollback()
            App.FlaskApp.logger.error(f"Error processing Payment {PaymentID}: {Error}")
            Flash("خطایی در پردازش پرداخت رخ داد. عملیات لغو شد.", "Error")

    return ReDirect(URLFor("AdminDashboard"))
