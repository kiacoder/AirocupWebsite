"tood"

import os
import math
import uuid
import datetime
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
    jsonify,
)
from sqlalchemy import exc, select, func
from sqlalchemy.orm import joinedload
import bleach
import bcrypt
from werkzeug.utils import secure_filename
import config
import database
import constants
import models
import utils
import persiantools.digits
import app

AdminBlueprint = Blueprint(
    "Admin", __name__, url_prefix="/Admin", template_folder="Admin"
)


@app.FlaskApp.route("/UploadsGallery/<filename>")
def UploadedGalleryImage(filename):
    return send_from_directory(constants.Path.GalleryDir, filename)


def GetAdminPersonas():
    return [Member["Name"] for Member in constants.CommitteeMembersData] + [
        "Website Dev",
        "Admin",
    ]


@app.FlaskApp.route("/AdminLogin", methods=["GET", "PosT"])
def AdminLogin():
    if request.method == "PosT":
        app.CSRF_Protector.protect()
        if bcrypt.checkpw(
            request.form["Password"].encode("utf-8"),
            config.AdminPasswordHash.encode("utf-8"),
        ):
            session["AdminLoggedIn"] = True
            flash("ورود به پنل مدیریت با موفقیت انجام شد.", "Success")
            return redirect(url_for("AdminDashboard"))
        else:
            flash("رمز عبور ادمین نامعتبر است.", "Error")

    return render_template(constants.AdminHTMLNamesData["AdminLogin"])


@app.FlaskApp.route("/Admin/GetChatHistory/<int:ClientID>")
@app.AdminRequired
def GetChatHistory(ClientID):
    with database.get_db_session() as db:
        return jsonify(
            {
                "Messages": [
                    {
                        "MessageText": Message.MessageText,
                        "Timestamp": Message.Timestamp.isoformat(),
                        "Sender": Message.Sender,
                    }
                    for Message in database.GetChatHistoryByClientID(db, ClientID)
                ]
            }
        )


@app.FlaskApp.route("/API/GetChatClients")
@app.AdminRequired
def ApiGetChatClients():
    with database.get_db_session() as db:
        ClientList = [
            {"ID": c.ClientID, "Email": c.Email}
            for c in database.GetAllActiveClients(db)
        ]
    return jsonify(ClientList)


@app.FlaskApp.route("/Admin/Chat/<int:ClientID>")
@app.AdminRequired
def AdminChat(ClientID):
    with database.get_db_session() as DbSession:
        Client = database.GetClientBy(DbSession, "ClientID", ClientID)
    if not Client or Client.Status != models.EntityStatus.Active:
        flash("کاربر مورد نظر یافت نشد یا غیرفعال است.", "Error")
        return redirect(url_for("AdminSelectChat"))
    return render_template(
        constants.AdminHTMLNamesData["AdminChat"],
        Client=Client,
        Personas=GetAdminPersonas(),
    )


@app.FlaskApp.route("/Admin/AddTeam/<int:ClientID>", methods=["PosT"])
@app.AdminRequired
def AdminAddTeam(ClientID):
    TeamName = bleach.clean(request.form.get("TeamName", "").strip())

    if not TeamName:
        flash("نام تیم نمی‌تواند خالی باشد.", "Error")
        return redirect(url_for("AdminManageClient", ClientID=ClientID))

    with database.get_db_session() as DbSession:
        try:
            NewTeam = models.Team(
                ClientID=ClientID,
                TeamName=TeamName,
                TeamRegistrationDate=datetime.datetime.now(datetime.timezone.utc),
            )
            DbSession.add(NewTeam)
            DbSession.commit()
            flash(f"تیم «{TeamName}» با موفقیت برای این کاربر ساخته شد.", "Success")
        except exc.IntegrityError:
            DbSession.rollback()
            flash(
                "تیمی با این نام از قبل در سیستم وجود دارد. لطفا نام دیگری انتخاب کنید.",
                "Error",
            )

    return redirect(url_for("AdminManageClient", ClientID=ClientID))


@app.FlaskApp.route("/Admin/Chat/Select")
@app.AdminRequired
def AdminSelectChat():
    with database.get_db_session() as DbSession:
        ClientsQuery = (
            DbSession.query(
                models.Client.client_id,
                models.Client.Email,
                func.count(models.ChatMessage.MessageID).label("UnreadCount"),
                func.max(models.ChatMessage.Timestamp).label("LastMessageTimestamp"),
            )
            .join(
                models.ChatMessage,
                models.Client.client_id == models.ChatMessage.ClientID,
            )
            .filter(models.ChatMessage.Sender.notin_(GetAdminPersonas()))
            .group_by(models.Client.client_id)
            .order_by(func.max(models.ChatMessage.Timestamp).desc())
        )

    return render_template(
        constants.AdminHTMLNamesData["AdminChatList"], Clients=ClientsQuery.all()
    )


@app.FlaskApp.route("/Admin/UpdatePaymentStatus/<int:TeamID>", methods=["PosT"])
@app.AdminActionRequired
def AdminUpdatePaymentStatus(TeamID):
    try:
        NewStatus = models.PaymentStatus(request.form.get("NewStatus"))
    except ValueError:
        flash("وضعیت ارسالی نامعتبر است.", "Error")
        return redirect(url_for("AdminManageTeams"))

    with database.get_db_session() as DbSession:
        LatestPayment = (
            DbSession.query(models.Payment)
            .filter(models.Payment.TeamID == TeamID)
            .order_by(models.Payment.UploadDate.desc())
            .first()
        )

        if not LatestPayment:
            flash("هیچ پرداختی برای این تیم یافت نشد.", "Error")
            return redirect(url_for("AdminManageTeams"))

        try:
            LatestPayment.Status = NewStatus
            DbSession.commit()
            flash(
                f"وضعیت آخرین پرداخت تیم به '{NewStatus.value}' تغییر یافت.", "Success"
            )

        except Exception as Error:
            DbSession.rollback()
            app.FlaskApp.logger.error(
                f"Error updating payment status for Team {TeamID}: {Error}"
            )
            flash("خطایی در هنگام به‌روزرسانی وضعیت پرداخت رخ داد.", "Error")

    return redirect(url_for("AdminManageTeams"))


@app.FlaskApp.route("/Admin/DeleteTeam/<int:TeamID>", methods=["PosT"])
@app.AdminActionRequired
def AdminDeleteTeam(TeamID):
    with database.get_db_session() as DbSession:
        try:
            Team = (
                DbSession.query(models.Team)
                .filter(models.Team.TeamID == TeamID)
                .first()
            )
            if not Team:
                abort(404)

            Team.Status = models.EntityStatus.Inactive
            for Member in Team.Members:
                Member.Status = models.EntityStatus.Withdrawn  # Status is white

            database.LogAction(
                DbSession,
                Team.ClientID,
                f"Admin archived Team '{Team.TeamName}' (ID: {TeamID}) as withdrawn.",
                IsAdminAction=True,
            )

            DbSession.commit()
            flash(
                f"تیم «{Team.TeamName}» با موفقیت به عنوان منصرف شده آرشیو شد.",
                "Success",
            )

        except Exception as Error:
            DbSession.rollback()
            app.FlaskApp.logger.error(
                f"Error in AdminDeleteTeam for Team {TeamID}: {Error}"
            )
            flash("خطایی در هنگام آرشیو تیم رخ داد.", "Error")

    return redirect(url_for("AdminManageClient", ClientID=Team.ClientID))


@app.FlaskApp.route(
    "/Admin/Team/<int:TeamID>/DeleteMember/<int:MemberID>", methods=["PosT"]
)
@app.AdminActionRequired
def AdminDeleteMember(TeamID, MemberID):
    with database.get_db_session() as DbSession:
        Member = (
            DbSession.query(models.Member)
            .options(joinedload(models.Member.Team))
            .filter(models.Member.MemberID == MemberID, models.Member.TeamID == TeamID)
            .first()
        )

        if not Member:
            flash("عضو مورد نظر یافت نشد.", "Error")
            return redirect(url_for("AdminEditTeam", TeamID=TeamID))

        Member.Status = models.EntityStatus.Withdrawn

        database.LogAction(
            DbSession,
            Member.Team.ClientID,  # ClientID is white
            f"Admin marked member '{Member.Name}' as resigned from Team ID {TeamID}.",
            IsAdminAction=True,
        )

        DbSession.commit()
        utils.UpdateTeamStats(DbSession, TeamID)

        flash("عضو با موفقیت به عنوان منصرف شده علامت‌گذاری و آرشیو شد.", "Success")

    return redirect(url_for("AdminEditTeam", TeamID=TeamID))


@app.FlaskApp.route("/Admin/ManageNews", methods=["GET", "PosT"])
@app.AdminRequired
def AdminManageNews():
    with database.get_db_session() as DbSession:
        if request.method == "PosT":
            TemplatePath = request.form.get("TemplatePath", "").strip()
            TitleString = bleach.clean(request.form.get("Title", "").strip())
            ContentString = bleach.clean(request.form.get("Content", "").strip())
            ImageFile = request.files.get("Image")

            if not TitleString or not ContentString:
                flash("عنوان و محتوای خبر نمی‌توانند خالی باشند.", "Error")
                return redirect(url_for("AdminManageNews"))

            ExistingNews = (
                DbSession.query(models.News)
                .filter(
                    func.lower(models.News.Title) == func.lower(TitleString)
                )  # both lowers are white
                .first()
            )
            if ExistingNews:
                flash("خبری با این عنوان از قبل وجود دارد.", "Error")
                return redirect(url_for("AdminManageNews"))

            NewArticle = models.News(
                Title=TitleString,
                Content=ContentString,
                PublishDate=datetime.datetime.now(datetime.timezone.utc),
                TemplatePath=TemplatePath,
            )

            if ImageFile and ImageFile.filename:
                ImageFile.stream.seek(0)
                if not utils.IsFileAllowed(ImageFile.stream):
                    flash("خطا: فرمت فایل تصویر مجاز نیست.", "Error")
                    return redirect(url_for("AdminManageNews"))
                ImageFile.stream.seek(0)

                OriginalFileName = secure_filename(ImageFile.filename)
                Extension = OriginalFileName.rsplit(".", 1)[-1].lower()
                NewArticle.ImagePath = f"{uuid.uuid4()}.{Extension}"

                try:
                    ImageFile.save(
                        os.path.join(
                            app.FlaskApp.config["UPLOAD_FOLDER_NEWS"],
                            f"{uuid.uuid4()}.{Extension}",
                        )
                    )
                except Exception as Error:
                    app.FlaskApp.logger.error(f"News image save failed: {Error}")
                    flash("خطا در ذخیره تصویر خبر.", "Error")
                    return redirect(url_for("AdminManageNews"))

            try:
                DbSession.add(NewArticle)
                DbSession.commit()
                flash("خبر جدید با موفقیت اضافه شد.", "Success")
            except exc.IntegrityError:
                DbSession.rollback()
                flash("خبری با این عنوان از قبل وجود دارد.", "Error")
            except Exception as Error:
                DbSession.rollback()
                app.FlaskApp.logger.error(f"Error creating news: {Error}")
                flash("خطایی در ایجاد خبر رخ داد.", "Error")

            return redirect(url_for("AdminManageNews"))

        ArticlesList = database.GetAllArticles(DbSession)
    return render_template(
        constants.AdminHTMLNamesData["AdminManageNews"], Articles=ArticlesList
    )


@app.FlaskApp.route("/Admin/EditNews/<int:ArticleID>", methods=["GET", "PosT"])
@app.AdminRequired
def AdminEditNews(ArticleID):
    with database.get_db_session() as DbSession:
        Article = database.GetArticleByID(DbSession, ArticleID)
        if not Article:
            abort(404)

        if request.method == "PosT":
            try:
                Article.TemplatePath = request.form.get("TemplatePath", "").strip()
                NewTitle = bleach.clean(request.form.get("Title", "").strip())
                Article.Content = bleach.clean(request.form.get("Content", "").strip())

                if NewTitle != Article.Title:
                    ExistingNews = (
                        DbSession.query(models.News)
                        .filter(
                            func.lower(models.News.Title)
                            == func.lower(NewTitle),  # both lowers is white
                            models.News.NewsID != ArticleID,
                        )
                        .first()
                    )
                    if ExistingNews:
                        flash("خبری با این عنوان از قبل وجود دارد.", "Error")
                        return redirect(url_for("AdminEditNews", ArticleID=ArticleID))
                    Article.Title = NewTitle

                ImageFile = request.files.get("Image")
                if ImageFile and ImageFile.filename:
                    ImageFile.stream.seek(0)
                    if not utils.IsFileAllowed(ImageFile.stream):
                        flash("خطا: فرمت فایل تصویر مجاز نیست.", "Error")
                        return redirect(url_for("AdminEditNews", ArticleID=ArticleID))
                    ImageFile.stream.seek(0)

                    OriginalFileName = secure_filename(ImageFile.filename)
                    Extension = OriginalFileName.rsplit(".", 1)[-1].lower()
                    SecureName = f"{uuid.uuid4()}.{Extension}"
                    NewImagePath = os.path.join(
                        app.FlaskApp.config["UPLOAD_FOLDER_NEWS"], SecureName
                    )

                    OldImagePath = None
                    if Article.ImagePath:
                        OldImagePath = os.path.join(
                            app.FlaskApp.config["UPLOAD_FOLDER_NEWS"],
                            Article.ImagePath,
                        )

                    ImageFile.save(NewImagePath)

                    if OldImagePath and os.path.exists(OldImagePath):
                        os.remove(OldImagePath)

                    Article.ImagePath = SecureName

                DbSession.commit()
                flash("خبر با موفقیت ویرایش شد.", "Success")
                return redirect(url_for("AdminManageNews"))

            except Exception as Error:
                DbSession.rollback()
                app.FlaskApp.logger.error(f"Error editing news {ArticleID}: {Error}")
                flash("خطایی در ویرایش خبر رخ داد.", "Error")
                return redirect(url_for("AdminEditNews", ArticleID=ArticleID))

    return render_template(
        constants.AdminHTMLNamesData["AdminEditNews"], Article=Article
    )


@app.FlaskApp.route("/Admin/ManageClient/<int:ClientID>")
@app.AdminRequired
def AdminManageClient(ClientID):
    with database.get_db_session() as DbSession:
        Client = (
            DbSession.query(models.Client)
            .filter(models.Client.client_id == ClientID)
            .first()
        )
        if not Client:
            abort(404, "کاربر مورد نظر یافت نشد.")

        LatestPaymentSubquery = (
            select(models.Payment.Status)
            .where(models.Payment.TeamID == models.Team.TeamID)
            .order_by(models.Payment.UploadDate.desc())
            .limit(1)
            .scalar_subquery()
            .label("LastPaymentStatus")
        )

        TeamsQuery = (
            DbSession.query(
                models.Team,
                func.count(models.Member.MemberID).label("TotalMembers"),
                LatestPaymentSubquery,
            )
            .outerjoin(
                models.Member,
                (models.Member.TeamID == models.Team.TeamID)
                & (models.Member.Status == models.EntityStatus.Active),
            )
            .filter(
                models.Team.ClientID == ClientID,
                models.Team.Status == models.EntityStatus.Active,
            )
            .group_by(models.Team.TeamID)
            .order_by(models.Team.TeamRegistrationDate.desc())
            .all()
        )

        TeamsWithStatus = []
        for Team, MemberCount, LastPaymentStatus in TeamsQuery:
            Team.TotalMembers = MemberCount  # TotalMembers is white
            Team.LastPaymentStatus = LastPaymentStatus  # LastPaymentStatus is white
            TeamsWithStatus.append(Team)

    return render_template(
        constants.AdminHTMLNamesData["AdminManageClient"],
        Client=Client,
        Teams=TeamsWithStatus,
    )


@app.FlaskApp.route("/Admin/ManageTeams")
@app.AdminRequired
def AdminManageTeams():
    with database.get_db_session() as DbSession:
        Subquery = (
            select(models.Payment.Status)
            .where(models.Payment.TeamID == models.Team.TeamID)
            .order_by(models.Payment.UploadDate.desc())
            .limit(1)
            .scalar_subquery()
        )

        AllTeams = (
            DbSession.query(
                models.Team.TeamID,
                models.Team.TeamName,
                models.Client.Email.label("ClientEmail"),
                func.count(models.Member.MemberID).label("MemberCount"),
                Subquery.label("LastPaymentStatus"),
            )
            .join(models.Client, models.Team.ClientID == models.Client.client_id)
            .outerjoin(
                models.Member,
                (models.Team.TeamID == models.Member.TeamID)
                & (models.Member.Status == models.EntityStatus.Active),
            )
            .filter(models.Team.Status == models.EntityStatus.Active)
            .group_by(models.Team.TeamID)
            .order_by(models.Team.TeamRegistrationDate.desc())
            .all()
        )

    return render_template(
        constants.AdminHTMLNamesData["AdminManageTeams"], Teams=AllTeams
    )


@app.FlaskApp.route("/Admin/Team/<int:TeamID>/AddMember", methods=["GET", "PosT"])
@app.AdminRequired
def AdminAddMember(TeamID):
    with database.get_db_session() as DbSession:
        Team = database.GetTeamByID(DbSession, TeamID)
        if not Team:
            abort(404)

        if request.method == "PosT":
            app.CSRF_Protector.protect()
            try:
                Success, Message = utils.InternalAddMember(
                    DbSession, TeamID, request.form
                )
                if Success:
                    if database.CheckIfTeamIsPaid(DbSession, TeamID):
                        Team.UnpaidMembersCount += 1
                        flash(
                            "عضو جدید با موفقیت اضافه شد. (توجه: تیم پرداخت‌شده است، هزینه عضو جدید باید محاسبه شود).",
                            "Warning",
                        )
                    else:
                        flash("عضو جدید با موفقیت توسط ادمین اضافه شد.", "Success")

                    DbSession.commit()
                    utils.UpdateTeamStats(DbSession, TeamID)
                    return redirect(url_for("AdminEditTeam", TeamID=TeamID))
                else:
                    flash(Message, "Error")
            except Exception as Error:
                DbSession.rollback()
                app.FlaskApp.logger.error(
                    f"Error in AdminAddMember for Team {TeamID}: {Error}"
                )
                flash("خطایی در هنگام افزودن عضو رخ داد.", "Error")

    FormContext = utils.GetFormContext()
    return render_template(
        constants.AdminHTMLNamesData["AdminAddMember"], Team=Team, **FormContext
    )


@app.FlaskApp.route("/Admin/EditTeam/<int:TeamID>", methods=["GET", "PosT"])
@app.AdminRequired
def AdminEditTeam(TeamID):
    with database.get_db_session() as DbSession:
        Team = DbSession.query(models.Team).filter(models.Team.TeamID == TeamID).first()
        if not Team:
            abort(404)

        if request.method == "PosT":
            try:
                NewTeamName = bleach.clean(request.form.get("TeamName", "").strip())
                LeagueOneID = request.form.get("LeagueOneID")
                LeagueTwoID = request.form.get("LeagueTwoID")

                IsValid, ErrorMessage = utils.IsValidTeamName(NewTeamName)
                if not IsValid:
                    flash(ErrorMessage, "Error")
                else:
                    ExistingTeam = (
                        DbSession.query(models.Team)
                        .filter(
                            func.lower(models.Team.TeamName) == func.lower(NewTeamName),
                            models.Team.TeamID != TeamID,
                        )
                        .first()
                    )
                    if ExistingTeam:
                        flash("تیمی با این نام از قبل وجود دارد.", "Error")
                    else:
                        Team.TeamName = NewTeamName
                        Team.LeagueOneID = int(LeagueOneID) if LeagueOneID else None
                        Team.LeagueTwoID = int(LeagueTwoID) if LeagueTwoID else None
                        DbSession.commit()
                        utils.UpdateTeamStats(DbSession, TeamID)
                        flash("جزئیات تیم با موفقیت ذخیره شد", "Success")

            except Exception as Error:
                DbSession.rollback()
                app.FlaskApp.logger.error(
                    f"Error in AdminEditTeam for Team {TeamID}: {Error}"
                )
                flash("خطایی در هنگام ویرایش تیم رخ داد.", "Error")

            return redirect(url_for("AdminEditTeam", TeamID=TeamID))

        Members = (
            DbSession.query(models.Member).filter(models.Member.TeamID == TeamID).all()
        )
        FormContext = utils.GetFormContext()

    return render_template(
        constants.AdminHTMLNamesData["AdminEditTeam"],
        Team=Team,
        Members=Members,
        **FormContext,
    )


@app.FlaskApp.route(
    "/Admin/Team/<int:TeamID>/EditMember/<int:MemberID>", methods=["PosT"]
)
@app.AdminRequired
def AdminEditMember(TeamID, MemberID):
    with database.get_db_session() as DbSession:
        UpdatedMemberData, Error = utils.CreateMemberFromFormData(
            DbSession, request.form
        )
        if Error:
            flash(Error, "Error")
        else:
            if UpdatedMemberData["Role"] == models.MemberRole.Leader:
                if database.HasExistingLeader(
                    DbSession, TeamID, MemberIDToExclude=MemberID
                ):
                    flash("خطا: این تیم از قبل یک سرپرست دارد.", "Error")
                    return redirect(url_for("AdminEditTeam", TeamID=TeamID))

            MemberToUpdate = (
                DbSession.query(models.Member)
                .filter(models.Member.MemberID == MemberID)
                .first()
            )
            if MemberToUpdate:
                MemberToUpdate.Name = UpdatedMemberData["Name"]
                MemberToUpdate.BirthDate = UpdatedMemberData["BirthDate"]
                MemberToUpdate.NationalID = UpdatedMemberData["NationalID"]
                MemberToUpdate.Role = UpdatedMemberData["Role"]
                MemberToUpdate.CityID = UpdatedMemberData["CityID"]

                DbSession.commit()
                utils.UpdateTeamStats(DbSession, TeamID)
                flash("اطلاعات عضو با موفقیت ویرایش شد.", "Success")
            else:
                flash("عضو مورد نظر برای ویرایش یافت نشد.", "Error")

    return redirect(url_for("AdminEditTeam", TeamID=TeamID))


@app.FlaskApp.route("/Admin/ManageClients")
@app.AdminRequired
def AdminClientsList():
    with database.get_db_session() as DbSession:

        return render_template(
            constants.AdminHTMLNamesData["AdminClientsList"],
            Clients=(
                DbSession.query(models.Client)
                .filter(models.Client.Status == models.EntityStatus.Active)
                .order_by(models.Client.RegistrationDate.desc())
                .limit(10)
                .offset((request.args.get("page", 1, type=int) - 1) * 10)
                .all()
            ),
            CurrentPage=request.args.get("page", 1, type=int),
            TotalPagesCount=math.ceil(
                (
                    DbSession.query(func.count(models.Client.client_id))
                    .filter(models.Client.Status == models.EntityStatus.Active)
                    .scalar()
                )
                / 10
            ),
        )


@app.FlaskApp.route("/Admin/AddClient", methods=["PosT"])
@app.AdminRequired
def AdminAddClient():
    Email = request.form.get("Email", "").strip().lower()
    Phone = request.form.get("PhoneNumber", "").strip()
    Password = request.form.get("Password", "")

    if not all(
        [
            utils.IsValidEmail(request.form.get("Email", "").strip().lower()),
            utils.IsValidIranianPhone(Phone),
            Password,
        ]
    ):
        flash("لطفا تمام فیلدها را با مقادیر معتبر پر کنید.", "Error")
        return redirect(url_for("AdminClientsList"))

    with database.get_db_session() as DbSession:
        try:
            if (
                DbSession.query(models.Client)
                .filter(
                    (models.Client.Email == Email)
                    | (models.Client.PhoneNumber == Phone)
                )
                .first()
            ):
                flash("کاربری با این ایمیل یا شماره تلفن از قبل وجود دارد.", "Error")
                return redirect(url_for("AdminClientsList"))

            DbSession.add(
                models.Client(
                    PhoneNumber=Phone,
                    Email=Email,
                    Password=bcrypt.hashpw(
                        Password.encode("utf-8"), bcrypt.gensalt()
                    ).decode("utf-8"),
                    RegistrationDate=datetime.datetime.now(datetime.timezone.utc),
                    IsPhoneVerified=1,
                )
            )
            DbSession.commit()
            flash("کاربر جدید با موفقیت اضافه شد.", "Success")

        except exc.IntegrityError:
            DbSession.rollback()
            flash("کاربری با این ایمیل یا شماره تلفن از قبل وجود دارد.", "Error")
        except Exception as Error:
            DbSession.rollback()
            app.FlaskApp.logger.error(f"Error adding Client: {Error}")
            flash("خطایی در ایجاد کاربر رخ داد.", "Error")

    return redirect(url_for("AdminClientsList"))


@app.FlaskApp.route("/Admin/EditClient/<int:ClientID>", methods=["PosT"])
@app.AdminRequired
def AdminEditClient(ClientID):
    with database.get_db_session() as DbSession:
        try:
            CleanData, Errors = database.ValidateClientUpdate(
                DbSession,
                ClientID,
                request.form,
                utils.IsValidPassword,
                utils.IsValidEmail,
                utils.IsValidIranianPhone,
                persiantools.digits.fa_to_en,
            )

            if Errors:
                for Error in Errors:
                    flash(Error, "Error")
            else:
                if CleanData:
                    database.UpdateClientDetails(DbSession, ClientID, CleanData)
                    flash("اطلاعات کاربر با موفقیت ویرایش شد.", "Success")
                else:
                    flash("هیچ تغییری برای ذخیره وجود نداشت.", "Info")

        except Exception as Error:
            DbSession.rollback()
            app.FlaskApp.logger.error(f"Error editing Client {ClientID}: {Error}")
            flash("خطایی در هنگام ویرایش اطلاعات کاربر رخ داد.", "Error")

    return redirect(url_for("AdminManageClient", ClientID=ClientID))


@app.FlaskApp.route("/Admin/DeleteClient/<int:ClientID>", methods=["PosT"])
@app.AdminRequired
def AdminDeleteClient(ClientID):
    with database.get_db_session() as DbSession:
        Client = (
            DbSession.query(models.Client)
            .filter(models.Client.client_id == ClientID)
            .first()
        )
        if Client:
            Client.Status = models.EntityStatus.Inactive

            for Team in (
                DbSession.query(models.Team)
                .filter(
                    models.Team.ClientID == ClientID,
                    models.Team.Status == models.EntityStatus.Active,
                )
                .all()
            ):
                Team.Status = models.EntityStatus.Inactive

            DbSession.commit()
            flash("کاربر و تمام تیم‌های مرتبط با او با موفقیت غیرفعال شدند.", "Success")
        else:
            flash("کاربر یافت نشد.", "Error")
    return redirect(url_for("AdminClientsList"))


@app.FlaskApp.route("/AdminDashboard")
@app.AdminRequired
def AdminDashboard():
    with database.get_db_session() as DbSession:
        TotalClients = (
            DbSession.query(func.count(models.Client.client_id))
            .filter(models.Client.Status == models.EntityStatus.Active)
            .scalar()
        )
        TotalTeams = (
            DbSession.query(func.count(models.Team.TeamID))
            .filter(models.Team.Status == models.EntityStatus.Active)
            .scalar()
        )
        ApprovedTeams = (
            DbSession.query(func.count(func.distinct(models.Payment.TeamID)))
            .filter(models.Payment.Status == models.PaymentStatus.Approved)
            .scalar()
        )
        TotalMembers = (
            DbSession.query(func.count(models.Member.MemberID))
            .filter(models.Member.Status == models.EntityStatus.Active)
            .scalar()
        )
        TotalLeaders = (
            DbSession.query(func.count(models.Member.MemberID))
            .filter(
                models.Member.Status == models.EntityStatus.Active,
                models.Member.Role == models.MemberRole.Leader,
            )
            .scalar()
        )
        TotalCoaches = (
            DbSession.query(func.count(models.Member.MemberID))
            .filter(
                models.Member.Status == models.EntityStatus.Active,
                models.Member.Role == models.MemberRole.Coach,
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
            DbSession.query(models.Payment, models.Team.TeamName, models.Client.Email)
            .join(models.Team, models.Payment.TeamID == models.Team.TeamID)
            .join(models.Client, models.Payment.ClientID == models.Client.client_id)
            .filter(models.Payment.Status == models.PaymentStatus.Pending)
            .order_by(models.Payment.UploadDate.asc())
            .all()
        )

    return render_template(
        constants.AdminHTMLNamesData["AdminDashboard"],
        Stats=Stats,
        PendingPayments=PendingPayments,
    )


@app.FlaskApp.route("/Admin/ManagePayment/<int:PaymentID>/<Action>", methods=["PosT"])
@app.AdminRequired
def AdminManagePayment(PaymentID, Action):
    if Action not in ["approve", "reject"]:
        abort(400)

    with database.get_db_session() as db_session:
        try:
            Payment = (
                db_session.query(models.Payment)
                .filter(
                    models.Payment.PaymentID == PaymentID,
                    models.Payment.Status == models.PaymentStatus.Pending,
                )
                .first()
            )

            if not Payment:
                flash("این پرداخت قبلاً پردازش شده یا یافت نشد.", "Warning")
                return redirect(url_for("AdminDashboard"))

            if Action == "approve":
                Payment.Status = models.PaymentStatus.Approved
                db_session.query(models.Member).filter(
                    models.Member.TeamID == Payment.TeamID,
                    models.Member.Status != models.EntityStatus.Active,
                ).update(
                    {"Status": models.EntityStatus.Active}, synchronize_session=False
                )

                MembersJustPaidFor = Payment.MembersPaidFor
                db_session.query(models.Team).filter(
                    models.Team.TeamID == Payment.TeamID
                ).update(
                    {
                        "UnpaidMembersCount": models.Team.UnpaidMembersCount
                        - MembersJustPaidFor
                    },
                    synchronize_session=False,
                )

                database.LogAction(
                    db_session,
                    Payment.ClientID,
                    f"Admin Approved Payment ID {PaymentID} for Team ID {Payment.TeamID}.",
                    IsAdminAction=True,
                )
                flash("پرداخت با موفقیت تایید شد و اعضای تیم فعال شدند.", "Success")

            elif Action == "reject":
                Payment.Status = models.PaymentStatus.Rejected
                database.LogAction(
                    db_session,
                    Payment.ClientID,
                    f"Admin Rejected Payment ID {PaymentID} for Team ID {Payment.TeamID}.",
                    IsAdminAction=True,
                )
                flash("پرداخت رد شد.", "Warning")

            db_session.commit()

        except Exception as Error:
            db_session.rollback()
            app.FlaskApp.logger.error(f"Error processing Payment {PaymentID}: {Error}")
            flash("خطایی در پردازش پرداخت رخ داد. عملیات لغو شد.", "Error")

    return redirect(url_for("AdminDashboard"))
