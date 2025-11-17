"""admin panel routes and functionalities for managing clients, teams, members, news, and chat"""
import os
import math
import uuid
import datetime
from types import SimpleNamespace
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
    current_app,
)
import persiantools.digits  # type:ignore
from sqlalchemy import exc, func, select
from sqlalchemy.sql.functions import count
from sqlalchemy.orm import joinedload, subqueryload
import bleach
import bcrypt
from werkzeug.utils import secure_filename

from . import config
from . import database
from . import constants
from . import models
from . import utils
from .auth import admin_required, admin_action_required

admin_blueprint = Blueprint("admin", __name__, template_folder="admin")


def _coerce_payment_status(raw_status):
    """Return a ``PaymentStatus`` enum when ``raw_status`` is truthy"""
    if raw_status is None:
        return None
    if isinstance(raw_status, models.PaymentStatus):
        return raw_status
    try:
        return models.PaymentStatus(raw_status)
    except ValueError:
        return None


@admin_blueprint.route("/UploadsGallery/<filename>")
def uploaded_gallery_image(filename):
    """Serve uploaded gallery images securely"""
    return send_from_directory(constants.Path.gallery_dir, filename)


def get_admin_personas():
    """Get list of admin personas for chat"""
    personas = []
    for member in getattr(constants, "committee_members_data", []):
        if isinstance(member, dict):
            personas.append(member.get("name"))
    personas = [p for p in personas if p]
    personas.extend(["Website Dev", "admin"])
    return personas


@admin_blueprint.route("/AdminLogin", methods=["GET", "POST"])
def admin_login():
    """admin login page and authentication"""
    if request.method == "POST":
        admin_pass = request.form.get("password", "")
        if config.admin_password_hash and bcrypt.checkpw(
            admin_pass.encode("utf-8"),
            config.admin_password_hash.encode("utf-8"),
        ):
            session["admin_logged_in"] = True
            flash("ورود به پنل مدیریت با موفقیت انجام شد.", "success")
            return redirect(url_for("admin.admin_dashboard"))
        else:
            flash("رمز عبور ادمین نامعتبر است.", "error")

    return render_template(constants.admin_html_names_data["admin_login"])


@admin_blueprint.route("/Admin/GetChatHistory/<int:client_id>")
@admin_required
def get_chat_history(client_id):
    """Retrieve chat history for a specific client"""
    with database.get_db_session() as db:
        msgs = database.get_chat_history_by_client_id(db, client_id)
        return jsonify(
            {
                "messages": [
                    {
                        "message_text": message.message_text,
                        "timestamp": message.timestamp.isoformat(),
                        "sender": message.sender,
                    }
                    for message in msgs
                ]
            }
        )


@admin_blueprint.route("/API/GetChatClients")
@admin_required
def api_get_chat_clients():
    "api endpoint to get list of active chat clients"
    with database.get_db_session() as db:
        client_list = [
            {"id": c.client_id, "email": c.email}
            for c in database.get_all_active_clients(db)
        ]
    return jsonify(client_list)


@admin_blueprint.route("/Admin/Chat/<int:client_id>")
@admin_required
def admin_chat(client_id):
    "admin chat interface for a specific client"
    with database.get_db_session() as db_session:
        client = database.get_client_by(db_session, "client_id", client_id)
    if not client or client.status != models.EntityStatus.ACTIVE:
        flash("کاربر مورد نظر یافت نشد یا غیرفعال است.", "error")
        return redirect(url_for("admin.admin_select_chat"))
    return render_template(
        constants.admin_html_names_data["admin_chat"],
        client=client,
        personas=get_admin_personas(),
    )


@admin_blueprint.route("/Admin/AddTeam/<int:client_id>", methods=["POST"])
@admin_required
def admin_add_team(client_id):
    "add a new team for a specific client"
    team_name = bleach.clean(request.form.get("team_name", "").strip())
    league_one_raw = request.form.get("LeagueOne", "").strip()
    league_two_raw = request.form.get("LeagueTwo", "").strip()
    education_level = request.form.get("EducationLevel", "").strip()

    if not team_name:
        flash("نام تیم نمی‌تواند خالی باشد.", "error")
        return redirect(url_for("admin.admin_manage_client", client_id=client_id))

    if education_level not in constants.allowed_education:
        flash("لطفاً مقطع تحصیلی معتبری انتخاب کنید.", "error")
        return redirect(url_for("admin.admin_manage_client", client_id=client_id))

    if not league_one_raw:
        flash("لطفاً لیگ اصلی تیم را مشخص کنید.", "error")
        return redirect(url_for("admin.admin_manage_client", client_id=client_id))

    if league_two_raw and league_two_raw == league_one_raw:
        flash("نمی‌توانید یک لیگ را به عنوان لیگ اول و دوم انتخاب کنید.", "error")
        return redirect(url_for("admin.admin_manage_client", client_id=client_id))

    league_one_id = int(league_one_raw) if league_one_raw else None
    league_two_id = int(league_two_raw) if league_two_raw else None

    with database.get_db_session() as db:
        try:
            db.add(
                models.Team(
                    client_id=client_id,
                    team_name=team_name,
                    team_registration_date=datetime.datetime.now(
                        datetime.timezone.utc
                    ),
                    league_one_id=league_one_id,
                    league_two_id=league_two_id,
                    education_level=education_level,
                )
            )
            db.commit()
            flash(f"تیم «{team_name}» با موفقیت برای این کاربر ساخته شد.", "success")
        except exc.IntegrityError:
            db.rollback()
            flash(
                "تیمی با این نام از قبل در سیستم وجود دارد. لطفا نام دیگری انتخاب کنید.",
                "error",
            )
        except exc.SQLAlchemyError as err:
            db.rollback()
            current_app.logger.error(
                "error adding team for client %s: %s", client_id, err
            )
            flash("خطایی در ایجاد تیم رخ داد.", "error")

    return redirect(url_for("admin.admin_manage_client", client_id=client_id))


@admin_blueprint.route("/Admin/Chat/Select")
@admin_required
def admin_select_chat():
    "Select a client for chat"
    with database.get_db_session() as db:
        clients_query = (
            db.query(
                models.Client.client_id,
                count(models.ChatMessage.message_id).label("unread_count"),
                func.max(models.ChatMessage.timestamp).label("last_message_timestamp"),
            )
            .join(
                models.ChatMessage,
                models.Client.client_id == models.ChatMessage.client_id,
            )
            .filter(models.ChatMessage.sender.notin_(get_admin_personas()))
            .group_by(models.Client.client_id)
            .order_by(func.max(models.ChatMessage.timestamp).desc())
        ).all()

    return render_template(
        constants.admin_html_names_data["admin_select_chat"],
        clients=clients_query.all(),
    )


@admin_blueprint.route("/Admin/UpdatePaymentStatus/<int:team_id>", methods=["POST"])
@admin_action_required
def admin_update_payment_status(team_id):
    """Update the status of a payment for a specific team."""
    try:
        new_status_str = request.form.get("new_status", "").strip()
        if not new_status_str:
            raise ValueError
        new_status = getattr(models.PaymentStatus, new_status_str)
    except (ValueError, AttributeError):
        flash("وضعیت ارسالی نامعتبر است.", "error")
        return redirect(url_for("admin.admin_manage_teams"))

    with database.get_db_session() as db:
        latest_payment = (
            db.query(models.Payment)
            .filter(models.Payment.team_id == team_id)
            .order_by(models.Payment.upload_date.desc())
            .first()
        )

        if not latest_payment:
            flash("هیچ پرداختی برای این تیم یافت نشد.", "error")
            return redirect(url_for("admin.admin_manage_teams"))

        try:
            team = latest_payment.team
            previous_status = latest_payment.status
            latest_payment.status = new_status

            if (
                team and new_status == models.PaymentStatus.APPROVED and previous_status != models.PaymentStatus.APPROVED
            ):
                paid_members = latest_payment.members_paid_for or 0
                current_unpaid = team.unpaid_members_count or 0
                team.unpaid_members_count = max(0, current_unpaid - paid_members)

            db.commit()
            flash(
                f"وضعیت آخرین پرداخت تیم به '{new_status.value}' تغییر یافت.", "success"
            )

        except exc.SQLAlchemyError as error:
            db.rollback()
            current_app.logger.error(
                "error updating payment status for Team %s: %s", team_id, error
            )
            flash("خطایی در هنگام به‌روزرسانی وضعیت پرداخت رخ داد.", "error")

    return redirect(url_for("admin.admin_manage_teams"))


@admin_blueprint.route("/Admin/DeleteTeam/<int:team_id>", methods=["POST"])
@admin_action_required
def admin_delete_team(team_id):
    "Delete (archive) a team and mark its members withdrawn"
    team = None
    with database.get_db_session() as db:
        try:
            team = db.query(models.Team).filter(models.Team.team_id == team_id).first()
            if not team:
                abort(404)

            team.status = models.EntityStatus.INACTIVE
            for member in team.members:
                member.status = models.EntityStatus.WITHDRAWN

            database.log_action(
                db,
                team.client_id,
                f"admin archived Team '{team.team_name}' (ID: {team_id}) as withdrawn.",
                is_admin_action=True,
            )

            db.commit()
            flash(
                f"تیم «{team.team_name}» با موفقیت به عنوان منصرف شده آرشیو شد.",
                "success",
            )

        except exc.SQLAlchemyError as error:
            db.rollback()
            current_app.logger.error(
                "error in admin_delete_team for Team %s: %s", team_id, error
            )
            flash("خطایی در هنگام آرشیو تیم رخ داد.", "error")

    if team:
        return redirect(url_for("admin.admin_manage_client", client_id=team.client_id))
    return redirect(url_for("admin.admin_manage_teams"))


@admin_blueprint.route(
    "/Admin/Team/<int:team_id>/DeleteMember/<int:member_id>", methods=["POST"]
)
@admin_action_required
def admin_delete_member(team_id, member_id):
    "Mark a team member as withdrawn"
    with database.get_db_session() as db:
        member = (
            db.query(models.Member)
            .options(joinedload(models.Member.team))
            .filter(
                models.Member.member_id == member_id, models.Member.team_id == team_id
            )
            .first()
        )

        if not member:
            flash("عضو مورد نظر یافت نشد.", "error")
            return redirect(url_for("admin.admin_edit_team", team_id=team_id))

        member.status = models.EntityStatus.WITHDRAWN

        database.log_action(
            db,
            getattr(member.team, "client_id"),
            f"admin marked member '{member.name}' as resigned from Team ID {team_id}.",
            is_admin_action=True,
        )

        db.commit()
        utils.update_team_stats(db, team_id)

        flash("عضو با موفقیت به عنوان منصرف شده علامت‌گذاری و آرشیو شد.", "success")

    return redirect(url_for("admin.admin_edit_team", team_id=team_id))


@admin_blueprint.route("/Admin/ManageNews", methods=["GET", "POST"])
@admin_required
def admin_manage_news():
    """Manage news articles: create, list, and edit."""
    with database.get_db_session() as db:
        if request.method == "POST":
            template_path = request.form.get("template_path", "").strip()
            title_string = bleach.clean(request.form.get("title", "")).strip()
            content_string = bleach.clean(request.form.get("content", "")).strip()
            image_file = request.files.get("image")

            if not title_string or not content_string:
                flash("عنوان و محتوای خبر نمی‌توانند خالی باشند.", "error")
                return redirect(url_for("admin.admin_manage_news"))

            existing_news = (
                db.query(models.News)
                .filter(func.lower(models.News.title) == func.lower(title_string))
                .first()
            )
            if existing_news:
                flash("خبری با این عنوان از قبل وجود دارد.", "error")
                return redirect(url_for("admin.admin_manage_news"))

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
                    return redirect(url_for("admin.admin_manage_news"))
                image_file.stream.seek(0)

                original_file_name = secure_filename(image_file.filename)
                extension = original_file_name.rsplit(".", 1)[-1].lower()
                image_filename = f"{uuid.uuid4()}.{extension}"
                setattr(new_article, "image_path", image_filename)

                try:
                    image_file.save(
                        os.path.join(
                            current_app.config["UPLOAD_FOLDER_NEWS"],
                            image_filename,
                        )
                    )
                except IOError as error:
                    current_app.logger.error("News image save failed: %s", error)
                    flash("خطا در ذخیره تصویر خبر.", "error")
                    return redirect(url_for("admin.admin_manage_news"))

            try:
                db.add(new_article)
                db.commit()
                flash("خبر جدید با موفقیت اضافه شد.", "success")
            except exc.IntegrityError:
                db.rollback()
                flash("خبری با این عنوان از قبل وجود دارد.", "error")
            except exc.SQLAlchemyError as error:
                db.rollback()
                current_app.logger.error("error creating news: %s", error)
                flash("خطایی در ایجاد خبر رخ داد.", "error")

            return redirect(url_for("admin.admin_manage_news"))

        articles_list = database.get_all_articles(db)
    return render_template(
        constants.admin_html_names_data["admin_manage_news"], articles=articles_list
    )


@admin_blueprint.route("/Admin/EditNews/<int:article_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_news(article_id):
    """Edit an existing news article"""
    with database.get_db_session() as db:
        article = (
            db.query(models.News).filter(models.News.news_id == article_id).first()
        )
        if not article:
            abort(404)

        if request.method == "POST":
            try:
                article.template_path = request.form.get("template_path", "").strip()
                article.content = bleach.clean(request.form.get("content", "").strip())
                new_title = bleach.clean(request.form.get("title", "").strip())

                if new_title and new_title != article.title:
                    existing_news = (
                        db.query(models.News)
                        .filter(
                            func.lower(models.News.title) == func.lower(new_title),
                            models.News.news_id != article_id,
                        )
                        .first()
                    )
                    if existing_news:
                        flash("خبری با این عنوان از قبل وجود دارد.", "error")
                        return redirect(
                            url_for("admin.admin_edit_news", article_id=article_id)
                        )

                    article.title = new_title

                image_file = request.files.get("image")
                if image_file and image_file.filename:
                    image_file.stream.seek(0)
                    if not utils.is_file_allowed(image_file.stream):
                        flash("خطا: فرمت فایل تصویر مجاز نیست.", "error")
                        return redirect(
                            url_for("admin.admin_edit_news", article_id=article_id)
                        )
                    image_file.stream.seek(0)

                    original_file_name = secure_filename(image_file.filename)
                    extension = original_file_name.rsplit(".", 1)[-1].lower()
                    secure_name = f"{uuid.uuid4()}.{extension}"
                    new_image_path = os.path.join(
                        current_app.config["UPLOAD_FOLDER_NEWS"], secure_name
                    )

                    old_image_path = None
                    if article.image_path:
                        old_image_path = os.path.join(
                            current_app.config["UPLOAD_FOLDER_NEWS"],
                            article.image_path,
                        )

                    image_file.save(new_image_path)

                    if old_image_path and os.path.exists(old_image_path):
                        try:
                            os.remove(old_image_path)
                        except OSError:
                            current_app.logger.exception(
                                "failed to remove old news image %s", old_image_path
                            )

                    article.image_path = secure_name

                db.commit()
                flash("خبر با موفقیت ویرایش شد.", "success")
            except (exc.SQLAlchemyError, IOError) as error:
                db.rollback()
                current_app.logger.error("error editing news %s: %s", article_id, error)
                flash("خطایی در ویرایش خبر رخ داد.", "error")
                return redirect(url_for("admin.admin_edit_news", article_id=article_id))

        return render_template(
            constants.admin_html_names_data["admin_edit_news"], article=article
        )


@admin_blueprint.route("/Admin/ManageClient/<int:client_id>")
@admin_required
def admin_manage_client(client_id):
    "Manage a specific client and their teams"
    with database.get_db_session() as db:
        client = (
            db.query(models.Client).filter(models.Client.client_id == client_id).first()
        )
        if not client:
            abort(404, "کاربر مورد نظر یافت نشد.")

        latest_payment_subquery = (
            select(models.Payment.status)
            .where(models.Payment.team_id == models.Team.team_id)
            .order_by(models.Payment.upload_date.desc())
            .limit(1)
            .scalar_subquery()
            .label("last_payment_status")
        )

        teams_query = (
            db.query(
                models.Team,
                count(models.Member.member_id).label("total_members"),
                latest_payment_subquery,
            )
            .outerjoin(
                models.Member,
                (models.Team.team_id == models.Member.team_id) & (models.Member.status == models.EntityStatus.ACTIVE),
            )
            .filter(
                models.Team.client_id == client_id,
                models.Team.status == models.EntityStatus.ACTIVE,
            )
            .group_by(models.Team.team_id)
            .order_by(models.Team.team_registration_date.desc())
            .all()
        )

        teams_with_status = []
        for team, member_count, last_payment_status in teams_query:
            setattr(team, "total_members", member_count)
            setattr(team, "last_payment_status", _coerce_payment_status(last_payment_status))
            teams_with_status.append(team)

    return render_template(
        constants.admin_html_names_data["admin_manage_client"],
        client=client,
        teams=teams_with_status,
        education_levels=constants.education_levels,
    )


@admin_blueprint.route("/Admin/ManageTeams")
@admin_required
def admin_manage_teams():
    "List and manage all teams"
    with database.get_db_session() as db:
        subquery = (
            select(models.Payment.status)
            .where(models.Payment.team_id == models.Team.team_id)
            .order_by(models.Payment.upload_date.desc())
            .limit(1)
            .scalar_subquery()
        )

        team_rows = (
            db.query(
                models.Team.team_id,
                models.Team.team_name,
                models.Client.email.label("client_email"),
                count(models.Member.member_id).label("member_count"),
                subquery.label("last_payment_status"),
            )
            .join(models.Client, models.Team.client_id == models.Client.client_id)
            .outerjoin(
                models.Member,
                (models.Team.team_id == models.Member.team_id) & (models.Member.status == models.EntityStatus.ACTIVE),
            )
            .filter(models.Team.status == models.EntityStatus.ACTIVE)
            .group_by(models.Team.team_id, models.Client.email)
            .order_by(models.Team.team_registration_date.desc())
            .all()
        )

        all_teams = [
            SimpleNamespace(
                team_id=row.team_id,
                team_name=row.team_name,
                client_email=row.client_email,
                member_count=row.member_count,
                last_payment_status=_coerce_payment_status(row.last_payment_status),
            )
            for row in team_rows
        ]

    return render_template(
        constants.admin_html_names_data["admin_manage_teams"], teams=all_teams
    )


@admin_blueprint.route("/Admin/Team/<int:team_id>/AddMember", methods=["GET", "POST"])
@admin_action_required
def admin_add_member(team_id):
    "add a new member to a specific team from the admin panel"
    with database.get_db_session() as db:
        team = database.get_team_by_id(db, team_id)
        if not team:
            abort(404)

        if request.method == "POST":
            new_member, error_message = utils.internal_add_member(
                db, team_id, request.form
            )

            if error_message:
                flash(error_message, "error")
            else:

                has_any_payment = database.has_team_made_any_payment(db, team_id)

                if has_any_payment:
                    team.unpaid_members_count = (team.unpaid_members_count or 0) + 1
                    flash(
                        f"عضو «{new_member.name}» اضافه شد. چون این تیم قبلاً رسید پرداختی ارسال کرده است، باید هزینه ۹,۵۰۰,۰۰۰ ریال به ازای هر لیگ برای عضو جدید پرداخت و رسید آن بارگذاری شود تا ثبت‌نام کامل گردد.".format(),
                        "warning",
                    )
                else:
                    flash(
                        f"عضو «{new_member.name}» با موفقیت توسط ادمین اضافه شد.",
                        "success",
                    )

                db.commit()
                utils.update_team_stats(db, team_id)
                return redirect(url_for("admin.admin_edit_team", team_id=team_id))

    form_context = utils.get_form_context()
    return render_template(
        constants.admin_html_names_data["admin_add_member"], team=team, **form_context
    )


@admin_blueprint.route("/Admin/EditTeam/<int:team_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_team(team_id):
    """Edit a team's details"""
    with database.get_db_session() as db:
        team = (
            db.query(models.Team)
            .options(
                subqueryload(models.Team.members),
                joinedload(models.Team.league_one),
                joinedload(models.Team.league_two),
            )
            .filter(models.Team.team_id == team_id)
            .first()
        )
        if not team:
            abort(404)

        if request.method == "POST":
            try:
                new_team_name = bleach.clean(request.form.get("team_name", "").strip())
                league_one_id = request.form.get("league_one_id")
                league_two_id = request.form.get("league_two_id")
                education_level = request.form.get("education_level", "").strip()

                is_valid, error_message = utils.is_valid_team_name(new_team_name)
                if not is_valid:
                    flash(error_message, "error")
                else:
                    existing_team = (
                        db.query(models.Team)
                        .filter(
                            func.lower(models.Team.team_name) == func.lower(new_team_name),
                            models.Team.team_id != team_id,
                        )
                        .first()
                    )
                    if existing_team:
                        flash("تیمی با این نام از قبل وجود دارد.", "error")
                    else:
                        if education_level and education_level not in constants.allowed_education:
                            flash("مقطع تحصیلی انتخاب شده معتبر نیست.", "error")
                            return redirect(
                                url_for("admin.admin_edit_team", team_id=team_id)
                            )

                        if education_level and education_level != (
                            team.education_level or ""
                        ):
                            level_info = constants.education_levels.get(
                                education_level
                            )
                            age_range = (
                                level_info.get("ages") if level_info else None
                            )
                            if age_range:
                                min_age, max_age = age_range
                                violating_member = next(
                                    (
                                        member
                                        for member in team.members
                                        if member.status == models.EntityStatus.ACTIVE and member.role == models.MemberRole.MEMBER and not (
                                            min_age <= utils.calculate_age(member.birth_date) <= max_age
                                        )
                                    ),
                                    None,
                                )
                                if violating_member:
                                    flash(
                                        f"عضو «{violating_member.name}» با مقطع «{education_level}» سازگار نیست.",
                                        "error",
                                    )
                                    return redirect(
                                        url_for(
                                            "admin.admin_edit_team",
                                            team_id=team_id,
                                        )
                                    )

                            setattr(team, "team_name", new_team_name)
                            setattr(
                                team,
                                "league_one_id",
                                int(league_one_id) if league_one_id else None,
                            )
                            setattr(
                                team,
                                "league_two_id",
                                int(league_two_id) if league_two_id else None,
                            )
                            team.education_level = education_level or None
                            db.commit()
                            utils.update_team_stats(db, team_id)
                            flash("جزئیات تیم با موفقیت ذخیره شد", "success")

            except (exc.SQLAlchemyError, ValueError) as error:
                db.rollback()
                current_app.logger.error(
                    "error in AdminEditTeam for Team %s: %s", team_id, error
                )
                flash("خطایی در هنگام ویرایش تیم رخ داد.", "error")

            return redirect(url_for("admin.admin_edit_team", team_id=team_id))

        members = (
            db.query(models.Member)
            .options(
                joinedload(models.Member.city).joinedload(models.City.province)
            )
            .filter(models.Member.team_id == team_id)
            .all()
        )
        form_context = utils.get_form_context()

    return render_template(
        constants.admin_html_names_data["admin_edit_team"],
        team=team,
        members=members,
        education_levels=constants.education_levels,
        **form_context,
    )


@admin_blueprint.route(
    "/Admin/Team/<int:team_id>/EditMember/<int:member_id>", methods=["POST"]
)
@admin_required
def admin_edit_member(team_id, member_id):
    """Edit a team member's details."""
    with database.get_db_session() as db:
        updated_member_data, error = utils.create_member_from_form_data(
            db, request.form, team_id=team_id, member_id=member_id
        )
        if error:
            flash(error, "error")
        else:
            if not updated_member_data:
                return redirect(url_for("admin.admin_edit_team", team_id=team_id))

            if updated_member_data["role"] == models.MemberRole.LEADER:
                if database.has_existing_leader(db, team_id, member_id):
                    flash("خطا: این تیم از قبل یک سرپرست دارد.", "error")
                    return redirect(url_for("admin.admin_edit_team", team_id=team_id))

            team = (
                db.query(models.Team)
                .filter(models.Team.team_id == team_id)
                .first()
            )
            education_level = getattr(team, "education_level", None) if team else None

            is_valid_age, age_error = utils.validate_member_age(
                updated_member_data["birth_date"],
                updated_member_data["role"],
                education_level,
            )
            if not is_valid_age:
                flash(age_error or "سن عضو با مقطع تحصیلی انتخاب شده سازگار نیست.", "error")
                return redirect(url_for("admin.admin_edit_team", team_id=team_id))

            member_to_update = (
                db.query(models.Member)
                .filter(models.Member.member_id == member_id)
                .first()
            )
            if member_to_update:
                member_to_update.name = updated_member_data["name"]
                member_to_update.birth_date = updated_member_data["birth_date"]
                member_to_update.national_id = updated_member_data["national_id"]
                member_to_update.role = updated_member_data["role"]
                member_to_update.city_id = updated_member_data["city_id"]

                db.commit()
                utils.update_team_stats(db, team_id)
                flash("اطلاعات عضو با موفقیت ویرایش شد.", "success")
            else:
                flash("عضو مورد نظر برای ویرایش یافت نشد.", "error")

    return redirect(url_for("admin.admin_edit_team", team_id=team_id))


@admin_blueprint.route("/Admin/ManageClients")
@admin_required
def admin_clients_list():
    "List and manage clients with pagination"
    page = request.args.get("page", 1, type=int)
    per_page = 10
    with database.get_db_session() as db:
        clients = (
            db.query(models.Client)
            .filter(models.Client.status == models.EntityStatus.ACTIVE)
            .order_by(models.Client.registration_date.desc())
            .limit(per_page)
            .offset((page - 1) * per_page)
            .all()
        )
        total_active = (
            db.query(count(models.Client.client_id))
            .filter(models.Client.status == models.EntityStatus.ACTIVE)
            .scalar()
        ) or 0

    total_pages = math.ceil(total_active / per_page) if total_active else 0

    return render_template(
        constants.admin_html_names_data["admin_clients_list"],
        Clients=clients,
        CurrentPage=page,
        TotalPagesCount=total_pages,
    )


@admin_blueprint.route("/Admin/AddClient", methods=["POST"])
@admin_required
def admin_add_client():
    "add a new client to the database"
    email = (
        request.form.get("email") or request.form.get("Email") or ""
    ).strip().lower()
    phone = (
        request.form.get("phone_number") or request.form.get("PhoneNumber") or ""
    ).strip()
    password = request.form.get("password") or request.form.get("Password") or ""

    if not all(
        [
            utils.is_valid_email(email),
            utils.is_valid_iranian_phone(phone),
            password,
        ]
    ):
        flash("لطفا تمام فیلدها را با مقادیر معتبر پر کنید.", "error")
        return redirect(url_for("admin.admin_clients_list"))

    with database.get_db_session() as db:
        try:
            if (
                db.query(models.Client)
                .filter(
                    (models.Client.email == email) | (models.Client.phone_number == phone)
                )
                .first()
            ):
                flash("کاربری با این ایمیل یا شماره تلفن از قبل وجود دارد.", "error")
                return redirect(url_for("admin.admin_clients_list"))

            db.add(
                models.Client(
                    phone_number=phone,
                    email=email,
                    password=bcrypt.hashpw(
                        password.encode("utf-8"), bcrypt.gensalt()
                    ).decode("utf-8"),
                    registration_date=datetime.datetime.now(datetime.timezone.utc),
                    is_phone_verified=True,
                )
            )
            db.commit()
            flash("کاربر جدید با موفقیت اضافه شد.", "success")
        except exc.IntegrityError:
            db.rollback()
            flash("کاربری با این ایمیل یا شماره تلفن از قبل وجود دارد.", "error")
        except exc.SQLAlchemyError as error:
            db.rollback()
            current_app.logger.error("Error creating client: %s", error)
            flash("خطایی در ایجاد کاربر رخ داد.", "error")

    return redirect(url_for("admin.admin_clients_list"))


@admin_blueprint.route("/Admin/EditClient/<int:client_id>", methods=["POST"])
@admin_required
def admin_edit_client(client_id):
    "Edit a client's details"
    with database.get_db_session() as db:
        try:
            clean_data, errors = database.validate_client_update(
                db,
                client_id,
                request.form,
                utils.is_valid_password,
                utils.is_valid_email,
                utils.is_valid_iranian_phone,
                persiantools.digits.fa_to_en,
            )

            if errors:
                for err in errors:
                    flash(err, "error")
            else:
                if clean_data:
                    database.update_client_details(db, client_id, clean_data)
                    flash("اطلاعات کاربر با موفقیت ویرایش شد.", "success")
                else:
                    flash("هیچ تغییری برای ذخیره وجود نداشت.", "info")

        except (exc.SQLAlchemyError, ValueError) as error:
            db.rollback()
            current_app.logger.error("error editing Client %s: %s", client_id, error)
            flash("خطایی در هنگام ویرایش اطلاعات کاربر رخ داد.", "error")

    return redirect(url_for("admin.admin_manage_client", client_id=client_id))


@admin_blueprint.route("/Admin/DeleteClient/<int:client_id>", methods=["POST"])
@admin_required
def admin_delete_client(client_id):
    "Deactivate a client and all their teams"
    with database.get_db_session() as db:
        client = (
            db.query(models.Client).filter(models.Client.client_id == client_id).first()
        )
        if client:
            client.status = models.EntityStatus.INACTIVE

            for team in (
                db.query(models.Team)
                .filter(
                    models.Team.client_id == client_id,
                    models.Team.status == models.EntityStatus.ACTIVE,
                )
                .all()
            ):
                team.status = models.EntityStatus.INACTIVE

            db.commit()
            flash("کاربر و تمام تیم‌های مرتبط با او با موفقیت غیرفعال شدند.", "success")
        else:
            flash("کاربر یافت نشد.", "error")
    return redirect(url_for("admin.admin_clients_list"))


@admin_blueprint.route("/AdminDashboard")
@admin_required
def admin_dashboard():
    """admin dashboard with statistics and pending payments"""
    with database.get_db_session() as db:
        total_clients = (
            db.query(models.Client)
            .filter(models.Client.status == models.EntityStatus.ACTIVE)
            .count()
        )
        total_teams = (
            db.query(models.Team)
            .filter(models.Team.status == models.EntityStatus.ACTIVE)
            .count()
        )
        approved_teams = (
            db.query(models.Payment.team_id)
            .filter(models.Payment.status == models.PaymentStatus.APPROVED)
            .distinct()
            .count()
        )
        total_members = (
            db.query(models.Member)
            .filter(models.Member.status == models.EntityStatus.ACTIVE)
            .count()
        )
        total_leaders = (
            db.query(models.Member)
            .filter(
                models.Member.status == models.EntityStatus.ACTIVE,
                models.Member.role == models.MemberRole.LEADER,
            )
            .count()
        )
        total_coaches = (
            db.query(models.Member)
            .filter(
                models.Member.status == models.EntityStatus.ACTIVE,
                models.Member.role == models.MemberRole.COACH,
            )
            .count()
        )

        new_clients_this_week = (
            db.query(models.Client)
            .filter(
                models.Client.status == models.EntityStatus.ACTIVE,
                models.Client.registration_date >= datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7),
            )
            .count()
        )

        stats = {
            "total_clients": total_clients,
            "total_teams": total_teams,
            "approved_teams": approved_teams,
            "total_members": total_members,
            "total_leaders": total_leaders,
            "total_coaches": total_coaches,
            "new_clients_this_week": new_clients_this_week,
        }

        pending_payments_rows = (
            db.query(
                models.Payment,
                models.Team.team_name,
                models.Team.team_id,
                models.Client.email,
                models.Client.phone_number.label("client_phone_number"),
            )
            .join(models.Team, models.Payment.team_id == models.Team.team_id)
            .join(models.Client, models.Payment.client_id == models.Client.client_id)
            .filter(models.Payment.status == models.PaymentStatus.PENDING)
            .order_by(models.Payment.upload_date.asc())
            .all()
        )

        pending_payments = [
            {
                "payment_id": payment.payment_id,
                "team_id": team_id,
                "team_name": team_name,
                "client_email": client_email,
                "client_phone": client_phone_number,
                "amount": payment.amount,
                "members_paid_for": payment.members_paid_for,
                "upload_date": payment.upload_date,
                "receipt_filename": payment.receipt_filename,
            }
            for (
                payment,
                team_name,
                team_id,
                client_email,
                client_phone_number,
            ) in pending_payments_rows
        ]

    return render_template(
        constants.admin_html_names_data["admin_dashboard"],
        stats=stats,
        pending_payments=pending_payments,
        pending_payments_count=len(pending_payments),
        admin_greeting_name=session.get("admin_display_name", "مدیر محترم"),
    )


@admin_blueprint.route(
    "/Admin/ManagePayment/<int:payment_id>/<action>", methods=["POST"]
)
@admin_required
def admin_manage_payment(payment_id, action):
    "Approve or reject a pending payment"
    if action not in ["approve", "reject"]:
        abort(400)

    with database.get_db_session() as db_session:
        try:
            payment = (
                db_session.query(models.Payment)
                .filter(
                    models.Payment.payment_id == payment_id,
                    models.Payment.status == models.PaymentStatus.PENDING,
                )
                .first()
            )

            if not payment:
                flash("این پرداخت قبلاً پردازش شده یا یافت نشد.", "warning")
                return redirect(url_for("admin.admin_dashboard"))

            if action == "approve":
                payment.status = models.PaymentStatus.APPROVED
                db_session.query(models.Member).filter(
                    models.Member.team_id == payment.team_id,
                    models.Member.status != models.EntityStatus.ACTIVE,
                ).update(
                    {"status": models.EntityStatus.ACTIVE}, synchronize_session=False
                )
                team = db_session.query(models.Team).get(payment.team_id)
                if team:
                    members_paid = payment.members_paid_for or 0
                    current_unpaid = team.unpaid_members_count or 0
                    team.unpaid_members_count = max(0, current_unpaid - members_paid)

                database.log_action(
                    db_session,
                    payment.client_id,
                    f"admin approved payment ID {payment_id} for Team ID {payment.team_id}.",
                    is_admin_action=True,
                )
                flash("پرداخت با موفقیت تایید شد و اعضای تیم فعال شدند.", "success")

            elif action == "reject":
                payment.status = models.PaymentStatus.REJECTED
                database.log_action(
                    db_session,
                    payment.client_id,
                    f"admin rejected payment ID {payment_id} for Team ID {payment.team_id}.",
                    is_admin_action=True,
                )
                flash("پرداخت رد شد.", "warning")

            db_session.commit()
        except exc.SQLAlchemyError as error:
            db_session.rollback()
            current_app.logger.error(
                "error processing Payment %s: %s", payment_id, error
            )
            flash("خطایی در پردازش پرداخت رخ داد. عملیات لغو شد.", "error")

    return redirect(url_for("admin.admin_dashboard"))
