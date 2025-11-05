"Admin panel routes and functionalities for managing clients, teams, members, news, and chat"
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
import persiantools.digits # type: ignore
import app

admin_blueprint = Blueprint(
    "Admin", __name__, url_prefix="/Admin", template_folder="Admin"
)


@app.flask_app.route("/UploadsGallery/<filename>")
def uploaded_gallery_image(filename):
    "Serve uploaded gallery images securely"
    return send_from_directory(constants.Path.gallery_dir, filename)


def get_admin_personas():
    "Get list of admin personas for chat"
    return [member["Name"] for member in constants.committee_members_data] + [
        "Website Dev",
        "Admin",
    ]


@app.flask_app.route("/AdminLogin", methods=["GET", "POST"])
def admin_login():
    "Admin login page and authentication"
    if request.method == "POST":
        app.CSRF_Protector.protect()
        if config.admin_password_hash and bcrypt.checkpw(
            request.form["Password"].encode("utf-8"),
            config.admin_password_hash.encode("utf-8"),
        ):
            session["AdminLoggedIn"] = True
            flash("ورود به پنل مدیریت با موفقیت انجام شد.", "Success")
            return redirect(url_for("AdminDashboard"))
        else:
            flash("رمز عبور ادمین نامعتبر است.", "error")

    return render_template(constants.admin_html_names_data["AdminLogin"])


@app.flask_app.route("/Admin/GetChatHistory/<int:client_id>")
@app.admin_required
def get_chat_history(client_id):
    "Retrieve chat history for a specific client"
    with database.get_db_session() as db:
        return jsonify(
            {
                "Messages": [
                    {
                        "MessageText": message.message_text,
                        "Timestamp": message.timestamp.isoformat(),
                        "Sender": message.sender,
                    }
                    for message in database.get_chat_history_by_client_id(db, client_id)
                ]
            }
        )


@app.flask_app.route("/API/GetChatClients")
@app.admin_required
def api_get_chat_clients():
    "API endpoint to get list of ACTIVE chat clients"
    with database.get_db_session() as db:
        client_list = [
            {"ID": c.client_id, "Email": c.email}
            for c in database.get_all_active_clients(db)
        ]
    return jsonify(client_list)


@app.flask_app.route("/Admin/Chat/<int:client_id>")
@app.admin_required
def admin_chat(client_id):
    "Admin chat interface for a specific client"
    with database.get_db_session() as db_session:
        client = database.get_client_by(db_session, "client_id", client_id)
    if not client or client.status != models.EntityStatus.ACTIVE:
        flash("کاربر مورد نظر یافت نشد یا غیرفعال است.", "error")
        return redirect(url_for("AdminSelectChat"))
    return render_template(
        constants.admin_html_names_data["AdminChat"],
        client=client,
        personas=get_admin_personas(),
    )


@app.flask_app.route("/Admin/AddTeam/<int:client_id>", methods=["PosT"])
@app.admin_required
def admin_add_team(client_id):
    "Add a new team for a specific client"
    team_name = bleach.clean(request.form.get("team_name", "").strip())

    if not team_name:
        flash("نام تیم نمی‌تواند خالی باشد.", "error")
        return redirect(url_for("AdminManageClient", client_id=client_id))

    with database.get_db_session() as db:
        try:
            new_team = models.Team(
                client_id=client_id,
                team_name=team_name,
                TeamRegistrationDate=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(new_team)
            db.commit()
            flash(f"تیم «{team_name}» با موفقیت برای این کاربر ساخته شد.", "Success")
        except exc.Integrityerror:
            db.rollback()
            flash(
                "تیمی با این نام از قبل در سیستم وجود دارد. لطفا نام دیگری انتخاب کنید.",
                "error",
            )

    return redirect(url_for("AdminManageClient", client_id=client_id))


@app.flask_app.route("/Admin/Chat/Select")
@app.admin_required
def admin_select_chat():
    "Select a client for chat"
    with database.get_db_session() as db:
        clients_query = (
            db.query(
                models.Client.client_id,
                models.Client.email,
                func.count().label("UnreadCount"),
                func.max(models.ChatMessage.timestamp).label("LastMessageTimestamp"),
            )
            .join(
                models.ChatMessage,
                models.Client.client_id == models.ChatMessage.client_id,
            )
            .filter(models.ChatMessage.sender.notin_(get_admin_personas()))
            .group_by(models.Client.client_id)
            .order_by(func.max(models.ChatMessage.timestamp).desc())
        )

    return render_template(
        constants.admin_html_names_data["AdminChatList"], Clients=clients_query.all()
    )


@app.flask_app.route("/Admin/UpdatePaymentStatus/<int:team_id>", methods=["POST"])
@app.admin_action_required
def admin_update_payment_status(team_id):
    "Update the status of a payment for a specific team"
    try:
        new_status_str = request.form.get("NewStatus")
        if not new_status_str:
            raise Valueerror
        new_status = getattr(models.PaymentStatus, new_status_str)
    except (Valueerror, Attributeerror):
        flash("وضعیت ارسالی نامعتبر است.", "error")
        return redirect(url_for("AdminManageTeams"))

    with database.get_db_session() as db:
        latest_payment = (
            db.query(models.Payment)
            .filter(models.Payment.team_id == team_id)
            .order_by(models.Payment.upload_date.desc())
            .first()
        )

        if not latest_payment:
            flash("هیچ پرداختی برای این تیم یافت نشد.", "error")
            return redirect(url_for("AdminManageTeams"))

        try:
            latest_payment.status = new_status
            db.commit()
            flash(
                f"وضعیت آخرین پرداخت تیم به '{new_status.value}' تغییر یافت.", "Success"
            )

        except exc.SQLAlchemyerror as error:
            db.rollback()
            app.flask_app.logger.error(
                "error updating payment status for Team %s: %s", team_id, error
            )
            flash("خطایی در هنگام به‌روزرسانی وضعیت پرداخت رخ داد.", "error")

    return redirect(url_for("AdminManageTeams"))


@app.flask_app.route("/Admin/DeleteTeam/<int:team_id>", methods=["PosT"])
@app.admin_action_required
def admin_delete_team(team_id):
    "Delete a team and its members"
    team = None
    with database.get_db_session() as db:
        try:
            team = (
                db.query(models.Team)
                .filter(models.Team.team_id == team_id)
                .first()
            )
            if not team:
                abort(404)

            team.status = models.EntityStatus.INACTIVE
            for member in team.members:
                member.status = models.EntityStatus.WITHDRAWN  # Status is white

            database.log_action(
                db,
                team.client_id,
                f"Admin archived Team '{team.team_name}' (ID: {team_id}) as withdrawn.",
                is_admin_action=True,
            )

            db.commit()
            flash(
                f"تیم «{team.team_name}» با موفقیت به عنوان منصرف شده آرشیو شد.",
                "Success",
            )

        except exc.SQLAlchemyerror as error:
            db.rollback()
            app.flask_app.logger.error(
                "error in AdminDeleteTeam for Team %s: %s", team_id, error
            )
            flash("خطایی در هنگام آرشیو تیم رخ داد.", "error")

    if team:
        return redirect(url_for("AdminManageClient", client_id=team.client_id))
    return redirect(url_for("AdminManageTeams"))


@app.flask_app.route(
    "/Admin/Team/<int:team_id>/DeleteMember/<int:member_id>", methods=["PosT"]
)
@app.admin_action_required
def admin_delete_member(team_id, member_id):
    "Mark a team member as withdrawn"
    with database.get_db_session() as db:
        member = (
            db.query(models.Member)
            .options(joinedload(models.Member.team))
            .filter(models.Member.member_id == member_id, models.Member.team_id == team_id)
            .first()
        )

        if not member:
            flash("عضو مورد نظر یافت نشد.", "error")
            return redirect(url_for("AdminEditTeam", team_id=team_id))

        member.status = models.EntityStatus.WITHDRAWN

        database.log_action(
            db,
            member.team.client_id,  # client_id is white
            f"Admin marked member '{member.name}' as resigned from Team ID {team_id}.",
            is_admin_action=True,
        )

        db.commit()
        utils.update_team_stats(db, team_id)

        flash("عضو با موفقیت به عنوان منصرف شده علامت‌گذاری و آرشیو شد.", "Success")

    return redirect(url_for("AdminEditTeam", team_id=team_id))


@app.flask_app.route("/Admin/ManageNews", methods=["GET", "POST"])
@app.admin_required
def admin_manage_news():
    "Manage news articles: create, list, and edit"
    with database.get_db_session() as db:
        if request.method == "POST":
            template_path = request.form.get("TemplatePath", "").strip()
            title_string = bleach.clean(request.form.get("Title", "").strip())
            content_string = bleach.clean(request.form.get("Content", "").strip())
            image_file = request.files.get("Image")

            if not title_string or not content_string:
                flash("عنوان و محتوای خبر نمی‌توانند خالی باشند.", "error")
                return redirect(url_for("AdminManageNews"))

            existing_news = (
                db.query(models.News)
                .filter(
                    func.lower(models.News.title) == func.lower(title_string)
                )  # both lowers are white
                .first()
            )
            if existing_news:
                flash("خبری با این عنوان از قبل وجود دارد.", "error")
                return redirect(url_for("AdminManageNews"))

            new_article = models.News(
                title=title_string,
                content=content_string,
                publish_date=datetime.datetime.now(datetime.timezone.utc),
                template_path=template_path,
            )

            if image_file and image_file.filename:
                image_file.stream.seek(0)
                if not utils.is_file_allowed(image_file.stream):
                    flash("خطا: فرمت فایل تصویر مجاز نیست.", "error")
                    return redirect(url_for("AdminManageNews"))
                image_file.stream.seek(0)

                original_file_name = secure_filename(image_file.filename)
                extension = original_file_name.rsplit(".", 1)[-1].lower()
                image_filename = f"{uuid.uuid4()}.{extension}"
                new_article.image_path = image_filename

                try:
                    image_file.save(
                        os.path.join(
                            app.flask_app.config["UPLOAD_FOLDER_NEWS"],
                            image_filename,
                        )
                    )
                except IOerror as error:
                    app.flask_app.logger.error("News image save failed: %s", error)
                    flash("خطا در ذخیره تصویر خبر.", "error")
                    return redirect(url_for("AdminManageNews"))

            try:
                db.add(new_article)
                db.commit()
                flash("خبر جدید با موفقیت اضافه شد.", "Success")
            except exc.Integrityerror:
                db.rollback()
                flash("خبری با این عنوان از قبل وجود دارد.", "error")
            except exc.SQLAlchemyerror as error:
                db.rollback()
                app.flask_app.logger.error("error creating news: %s", error)
                flash("خطایی در ایجاد خبر رخ داد.", "error")

            return redirect(url_for("AdminManageNews"))

        articles_list = database.get_all_articles(db)
    return render_template(
        constants.admin_html_names_data["AdminManageNews"], articles=articles_list
    )


@app.flask_app.route("/Admin/EditNews/<int:ArticleID>", methods=["GET", "POST"])
@app.admin_required
def AdminEditNews(ArticleID):
    with database.get_db_session() as db:
        article = database.get_article_by_id(db, ArticleID)
        if not article:
            abort(404)

        if request.method == "PosT":
            try:
                article.TemplatePath = request.form.get("TemplatePath", "").strip()
                NewTitle = bleach.clean(request.form.get("Title", "").strip())
                article.Content = bleach.clean(request.form.get("Content", "").strip())

                if NewTitle != article.Title:
                    ExistingNews = (
                        db.query(models.News)
                        .filter(
                            func.lower(models.News.Title)
                            == func.lower(NewTitle),  # both lowers is white
                            models.News.NewsID != ArticleID,
                        )
                        .first()
                    )
                    if ExistingNews:
                        flash("خبری با این عنوان از قبل وجود دارد.", "error")
                        return redirect(url_for("AdminEditNews", ArticleID=ArticleID))
                    article.Title = NewTitle

                ImageFile = request.files.get("Image")
                if ImageFile and ImageFile.filename:
                    ImageFile.stream.seek(0)
                    if not utils.is_file_allowed(ImageFile.stream):
                        flash("خطا: فرمت فایل تصویر مجاز نیست.", "error")
                        return redirect(url_for("AdminEditNews", ArticleID=ArticleID))
                    ImageFile.stream.seek(0)

                    OriginalFileName = secure_filename(ImageFile.filename)
                    Extension = OriginalFileName.rsplit(".", 1)[-1].lower()
                    SecureName = f"{uuid.uuid4()}.{Extension}"
                    NewImagePath = os.path.join(
                        app.flask_app.config["UPLOAD_FOLDER_NEWS"], SecureName
                    )

                    OldImagePath = None
                    if article.ImagePath:
                        OldImagePath = os.path.join(
                            app.flask_app.config["UPLOAD_FOLDER_NEWS"],
                            article.ImagePath,
                        )

                    ImageFile.save(NewImagePath)

                    if OldImagePath and os.path.exists(OldImagePath):
                        os.remove(OldImagePath)

                    article.ImagePath = SecureName

                db.commit()
                flash("خبر با موفقیت ویرایش شد.", "Success")
                return redirect(url_for("AdminManageNews"))

            except Exception as error:
                db.rollback()
                app.flask_app.logger.error(f"error editing news {ArticleID}: {error}")
                flash("خطایی در ویرایش خبر رخ داد.", "error")
                return redirect(url_for("AdminEditNews", ArticleID=ArticleID))

    return render_template(
        constants.admin_html_names_data["AdminEditNews"], Article=article
    )


@app.flask_app.route("/Admin/ManageClient/<int:client_id>")
@app.admin_required
def AdminManageClient(client_id):
    with database.get_db_session() as db:
        Client = (
            db.query(models.Client)
            .filter(models.Client.client_id == client_id)
            .first()
        )
        if not Client:
            abort(404, "کاربر مورد نظر یافت نشد.")

        LatestPaymentSubquery = (
            select(models.Payment.status)
            .where(models.Payment.team_id == models.Team.team_id)
            .order_by(models.Payment.UploadDate.desc())
            .limit(1)
            .scalar_subquery()
            .label("LastPaymentStatus")
        )

        TeamsQuery = (
            db.query(
                models.Team,
                func.count(models.Member.member_id).label("TotalMembers"),
                LatestPaymentSubquery,
            )
            .outerjoin(
                models.Member,
                (models.Member.team_id == models.Team.team_id)
                & (models.Member.status == models.EntityStatus.ACTIVE),
            )
            .filter(
                models.Team.client_id == client_id,
                models.Team.status == models.EntityStatus.ACTIVE,
            )
            .group_by(models.Team.team_id)
            .order_by(models.Team.TeamRegistrationDate.desc())
            .all()
        )

        TeamsWithStatus = []
        for Team, MemberCount, LastPaymentStatus in TeamsQuery:
            Team.TotalMembers = MemberCount  # TotalMembers is white
            Team.LastPaymentStatus = LastPaymentStatus  # LastPaymentStatus is white
            TeamsWithStatus.append(Team)

    return render_template(
        constants.admin_html_names_data["AdminManageClient"],
        Client=Client,
        Teams=TeamsWithStatus,
    )


@app.flask_app.route("/Admin/ManageTeams")
@app.admin_required
def AdminManageTeams():
    with database.get_db_session() as db:
        Subquery = (
            select(models.Payment.status)
            .where(models.Payment.team_id == models.Team.team_id)
            .order_by(models.Payment.UploadDate.desc())
            .limit(1)
            .scalar_subquery()
        )

        AllTeams = (
            db.query(
                models.Team.team_id,
                models.Team.team_name,
                models.Client.Email.label("ClientEmail"),
                func.count(models.Member.member_id).label("MemberCount"),
                Subquery.label("LastPaymentStatus"),
            )
            .join(models.Client, models.Team.client_id == models.Client.client_id)
            .outerjoin(
                models.Member,
                (models.Team.team_id == models.Member.team_id)
                & (models.Member.status == models.EntityStatus.ACTIVE),
            )
            .filter(models.Team.status == models.EntityStatus.ACTIVE)
            .group_by(models.Team.team_id)
            .order_by(models.Team.TeamRegistrationDate.desc())
            .all()
        )

    return render_template(
        constants.admin_html_names_data["AdminManageTeams"], Teams=AllTeams
    )


@app.flask_app.route("/Admin/Team/<int:team_id>/AddMember", methods=["GET", "PosT"])
@app.admin_required
def AdminAddMember(team_id):
    with database.get_db_session() as db:
        Team = database.GetTeamByID(db, team_id)
        if not Team:
            abort(404)

        if request.method == "PosT":
            app.CSRF_Protector.protect()
            try:
                Success, Message = utils.internaladdmember(
                    db, team_id, request.form
                )
                if Success:
                    if database.check_if_team_is_paid(db, team_id):
                        Team.UnpaidMembersCount += 1
                        flash(
                            "عضو جدید با موفقیت اضافه شد. (توجه: تیم پرداخت‌شده است، هزینه عضو جدید باید محاسبه شود).",
                            "Warning",
                        )
                    else:
                        flash("عضو جدید با موفقیت توسط ادمین اضافه شد.", "Success")

                    db.commit()
                    utils.update_team_stats(db, team_id)
                    return redirect(url_for("AdminEditTeam", team_id=team_id))
                else:
                    flash(Message, "error")
            except Exception as error:
                db.rollback()
                app.flask_app.logger.error(
                    f"error in AdminAddMember for Team {team_id}: {error}"
                )
                flash("خطایی در هنگام افزودن عضو رخ داد.", "error")

    FormContext = utils.get_form_context()
    return render_template(
        constants.admin_html_names_data["AdminAddMember"], Team=Team, **FormContext
    )


@app.flask_app.route("/Admin/EditTeam/<int:team_id>", methods=["GET", "PosT"])
@app.admin_required
def AdminEditTeam(team_id):
    with database.get_db_session() as db:
        Team = db.query(models.Team).filter(models.Team.team_id == team_id).first()
        if not Team:
            abort(404)

        if request.method == "PosT":
            try:
                Newteam_name = bleach.clean(request.form.get("team_name", "").strip())
                LeagueOneID = request.form.get("LeagueOneID")
                LeagueTwoID = request.form.get("LeagueTwoID")

                IsValid, errorMessage = utils.is_valid_team_name(Newteam_name)
                if not IsValid:
                    flash(errorMessage, "error")
                else:
                    ExistingTeam = (
                        db.query(models.Team)
                        .filter(
                            func.lower(models.Team.team_name) == func.lower(Newteam_name),
                            models.Team.team_id != team_id,
                        )
                        .first()
                    )
                    if ExistingTeam:
                        flash("تیمی با این نام از قبل وجود دارد.", "error")
                    else:
                        Team.team_name = Newteam_name
                        Team.LeagueOneID = int(LeagueOneID) if LeagueOneID else None
                        Team.LeagueTwoID = int(LeagueTwoID) if LeagueTwoID else None
                        db.commit()
                        utils.update_team_stats(db, team_id)
                        flash("جزئیات تیم با موفقیت ذخیره شد", "Success")

            except Exception as error:
                db.rollback()
                app.flask_app.logger.error(
                    f"error in AdminEditTeam for Team {team_id}: {error}"
                )
                flash("خطایی در هنگام ویرایش تیم رخ داد.", "error")

            return redirect(url_for("AdminEditTeam", team_id=team_id))

        Members = (
            db.query(models.Member).filter(models.Member.team_id == team_id).all()
        )
        FormContext = utils.get_form_context()

    return render_template(
        constants.admin_html_names_data["AdminEditTeam"],
        Team=Team,
        Members=Members,
        **FormContext,
    )


@app.flask_app.route(
    "/Admin/Team/<int:team_id>/EditMember/<int:member_id>", methods=["PosT"]
)
@app.admin_required
def AdminEditMember(team_id, member_id):
    with database.get_db_session() as db:
        UpdatedMemberData, error = utils.create_member_from_form_data(
            db, request.form
        )
        if error:
            flash(error, "error")
        else:
            if UpdatedMemberData["Role"] == models.MemberRole.Leader:
                if database.HasExistingLeader(
                    db, team_id, member_idToExclude=member_id
                ):
                    flash("خطا: این تیم از قبل یک سرپرست دارد.", "error")
                    return redirect(url_for("AdminEditTeam", team_id=team_id))

            MemberToUpdate = (
                db.query(models.Member)
                .filter(models.Member.member_id == member_id)
                .first()
            )
            if MemberToUpdate:
                MemberToUpdate.Name = UpdatedMemberData["Name"]
                MemberToUpdate.BirthDate = UpdatedMemberData["BirthDate"]
                MemberToUpdate.NationalID = UpdatedMemberData["NationalID"]
                MemberToUpdate.Role = UpdatedMemberData["Role"]
                MemberToUpdate.CityID = UpdatedMemberData["CityID"]

                db.commit()
                utils.update_team_stats(db, team_id)
                flash("اطلاعات عضو با موفقیت ویرایش شد.", "Success")
            else:
                flash("عضو مورد نظر برای ویرایش یافت نشد.", "error")

    return redirect(url_for("AdminEditTeam", team_id=team_id))


@app.flask_app.route("/Admin/ManageClients")
@app.admin_required
def AdminClientsList():
    with database.get_db_session() as db:

        return render_template(
            constants.admin_html_names_data["AdminClientsList"],
            Clients=(
                db.query(models.Client)
                .filter(models.Client.status == models.EntityStatus.ACTIVE)
                .order_by(models.Client.RegistrationDate.desc())
                .limit(10)
                .offset((request.args.get("page", 1, type=int) - 1) * 10)
                .all()
            ),
            CurrentPage=request.args.get("page", 1, type=int),
            TotalPagesCount=math.ceil(
                (
                    db.query(func.count(models.Client.client_id))
                    .filter(models.Client.status == models.EntityStatus.ACTIVE)
                    .scalar()
                )
                / 10
            ),
        )


@app.flask_app.route("/Admin/AddClient", methods=["PosT"])
@app.admin_required
def AdminAddClient():
    Email = request.form.get("Email", "").strip().lower()
    Phone = request.form.get("PhoneNumber", "").strip()
    Password = request.form.get("Password", "")

    if not all(
        [
            utils.is_valid_email(request.form.get("Email", "").strip().lower()),
            utils.is_valid_iranian_phone(Phone),
            Password,
        ]
    ):
        flash("لطفا تمام فیلدها را با مقادیر معتبر پر کنید.", "error")
        return redirect(url_for("AdminClientsList"))

    with database.get_db_session() as db:
        try:
            if (
                db.query(models.Client)
                .filter(
                    (models.Client.Email == Email)
                    | (models.Client.PhoneNumber == Phone)
                )
                .first()
            ):
                flash("کاربری با این ایمیل یا شماره تلفن از قبل وجود دارد.", "error")
                return redirect(url_for("AdminClientsList"))

            db.add(
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
            db.commit()
            flash("کاربر جدید با موفقیت اضافه شد.", "Success")

        except exc.Integrityerror:
            db.rollback()
            flash("کاربری با این ایمیل یا شماره تلفن از قبل وجود دارد.", "error")
        except Exception as error:
            db.rollback()
            app.flask_app.logger.error(f"error adding Client: {error}")
            flash("خطایی در ایجاد کاربر رخ داد.", "error")

    return redirect(url_for("AdminClientsList"))


@app.flask_app.route("/Admin/EditClient/<int:client_id>", methods=["PosT"])
@app.admin_required
def AdminEditClient(client_id):
    with database.get_db_session() as db:
        try:
            CleanData, errors = database.validate_client_update(
                db,
                client_id,
                request.form,
                utils.IsValidPassword,
                utils.is_valid_email,
                utils.is_valid_iranian_phone,
                persiantools.digits.fa_to_en,
            )

            if errors:
                for error in errors:
                    flash(error, "error")
            else:
                if CleanData:
                    database.UpdateClientDetails(db, client_id, CleanData)
                    flash("اطلاعات کاربر با موفقیت ویرایش شد.", "Success")
                else:
                    flash("هیچ تغییری برای ذخیره وجود نداشت.", "Info")

        except Exception as error:
            db.rollback()
            app.flask_app.logger.error(f"error editing Client {client_id}: {error}")
            flash("خطایی در هنگام ویرایش اطلاعات کاربر رخ داد.", "error")

    return redirect(url_for("AdminManageClient", client_id=client_id))


@app.flask_app.route("/Admin/DeleteClient/<int:client_id>", methods=["PosT"])
@app.admin_required
def AdminDeleteClient(client_id):
    with database.get_db_session() as db:
        Client = (
            db.query(models.Client)
            .filter(models.Client.client_id == client_id)
            .first()
        )
        if Client:
            Client.status = models.EntityStatus.InACTIVE

            for Team in (
                db.query(models.Team)
                .filter(
                    models.Team.client_id == client_id,
                    models.Team.status == models.EntityStatus.ACTIVE,
                )
                .all()
            ):
                Team.status = models.EntityStatus.InACTIVE

            db.commit()
            flash("کاربر و تمام تیم‌های مرتبط با او با موفقیت غیرفعال شدند.", "Success")
        else:
            flash("کاربر یافت نشد.", "error")
    return redirect(url_for("AdminClientsList"))


@app.flask_app.route("/AdminDashboard")
@app.admin_required
def AdminDashboard():
    with database.get_db_session() as db:
        TotalClients = (
            db.query(func.count(models.Client.client_id))
            .filter(models.Client.status == models.EntityStatus.ACTIVE)
            .scalar()
        )
        TotalTeams = (
            db.query(func.count(models.Team.team_id))
            .filter(models.Team.status == models.EntityStatus.ACTIVE)
            .scalar()
        )
        ApprovedTeams = (
            db.query(func.count(func.distinct(models.Payment.team_id)))
            .filter(models.Payment.status == models.PaymentStatus.Approved)
            .scalar()
        )
        TotalMembers = (
            db.query(func.count(models.Member.member_id))
            .filter(models.Member.status == models.EntityStatus.ACTIVE)
            .scalar()
        )
        TotalLeaders = (
            db.query(func.count(models.Member.member_id))
            .filter(
                models.Member.status == models.EntityStatus.ACTIVE,
                models.Member.Role == models.MemberRole.Leader,
            )
            .scalar()
        )
        TotalCoaches = (
            db.query(func.count(models.Member.member_id))
            .filter(
                models.Member.status == models.EntityStatus.ACTIVE,
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
            db.query(models.Payment, models.Team.team_name, models.Client.Email)
            .join(models.Team, models.Payment.team_id == models.Team.team_id)
            .join(models.Client, models.Payment.client_id == models.Client.client_id)
            .filter(models.Payment.status == models.PaymentStatus.Pending)
            .order_by(models.Payment.UploadDate.asc())
            .all()
        )

    return render_template(
        constants.admin_html_names_data["AdminDashboard"],
        Stats=Stats,
        PendingPayments=PendingPayments,
    )


@app.flask_app.route("/Admin/ManagePayment/<int:PaymentID>/<Action>", methods=["PosT"])
@app.admin_required
def AdminManagePayment(PaymentID, Action):
    if Action not in ["approve", "reject"]:
        abort(400)

    with database.get_db_session() as db_session:
        try:
            Payment = (
                db_session.query(models.Payment)
                .filter(
                    models.Payment.PaymentID == PaymentID,
                    models.Payment.status == models.PaymentStatus.Pending,
                )
                .first()
            )

            if not Payment:
                flash("این پرداخت قبلاً پردازش شده یا یافت نشد.", "Warning")
                return redirect(url_for("AdminDashboard"))

            if Action == "approve":
                Payment.status = models.PaymentStatus.Approved
                db_session.query(models.Member).filter(
                    models.Member.team_id == Payment.team_id,
                    models.Member.status != models.EntityStatus.ACTIVE,
                ).update(
                    {"Status": models.EntityStatus.ACTIVE}, synchronize_session=False
                )

                MembersJustPaidFor = Payment.MembersPaidFor
                db_session.query(models.Team).filter(
                    models.Team.team_id == Payment.team_id
                ).update(
                    {
                        "UnpaidMembersCount": models.Team.UnpaidMembersCount
                        - MembersJustPaidFor
                    },
                    synchronize_session=False,
                )

                database.LogAction(
                    db_session,
                    Payment.client_id,
                    f"Admin Approved Payment ID {PaymentID} for Team ID {Payment.team_id}.",
                    IsAdminAction=True,
                )
                flash("پرداخت با موفقیت تایید شد و اعضای تیم فعال شدند.", "Success")

            elif Action == "reject":
                Payment.status = models.PaymentStatus.Rejected
                database.LogAction(
                    db_session,
                    Payment.client_id,
                    f"Admin Rejected Payment ID {PaymentID} for Team ID {Payment.team_id}.",
                    IsAdminAction=True,
                )
                flash("پرداخت رد شد.", "Warning")

            db_session.commit()

        except Exception as error:
            db_session.rollback()
            app.flask_app.logger.error(f"error processing Payment {PaymentID}: {error}")
            flash("خطایی در پردازش پرداخت رخ داد. عملیات لغو شد.", "error")

    return redirect(url_for("AdminDashboard"))
