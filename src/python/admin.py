"""admin panel routes and functionalities for managing clients, teams, members, news, and chat"""

import os
import math
import uuid
import datetime
import shutil
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
from sqlalchemy import exc, func, select, or_, case, String
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


def _normalize_nullable_text(raw_value: str | None) -> str | None:
    """Return cleaned text value or ``None`` when input is empty/null."""

    if raw_value is None:
        return None

    cleaned = bleach.clean(raw_value).strip()
    if not cleaned or cleaned.lower() == "null":
        return None
    return cleaned


def _parse_nullable_int(raw_value: str | None) -> int | None:
    """Parse int from a nullable form field, returning ``None`` on blanks."""

    normalized = _normalize_nullable_text(raw_value)
    if normalized is None:
        return None

    try:
        return int(normalized)
    except (TypeError, ValueError):
        return None


def _summarize_expected_payment(
    team, payment, active_members_count, has_approved_payment
):
    """Return calculated payment expectations for admin review."""

    if active_members_count <= 0:
        return {
            "expected_amount": None,
            "members_count": 0,
            "per_member_fee": 0,
            "selected_leagues_count": 0,
            "discount_amount": 0,
            "league_two_cost": 0,
            "is_new_member_payment": False,
            "status_note": "هیچ عضو فعالی برای محاسبه وجود ندارد.",
        }

    if not team.league_one_id or not team.education_level:
        return {
            "expected_amount": None,
            "members_count": active_members_count,
            "per_member_fee": 0,
            "selected_leagues_count": 0,
            "discount_amount": 0,
            "league_two_cost": 0,
            "is_new_member_payment": False,
            "status_note": "لیگ یا مقطع تیم نامشخص است.",
        }

    selected_leagues_count = 1 + (1 if team.league_two_id is not None else 0)
    selected_leagues_count = max(1, selected_leagues_count)

    fee_per_person = config.payment_config.get("fee_per_person") or 0
    fee_team = config.payment_config.get("fee_team") or 0
    league_two_discount_percent = config.payment_config.get("league_two_discount") or 0
    new_member_fee_per_league = (
        config.payment_config.get("new_member_fee_per_league") or 0
    )

    members_basis = payment.members_paid_for or (
        team.unpaid_members_count if has_approved_payment else active_members_count
    )
    members_basis = max(0, members_basis)

    if has_approved_payment:
        per_member_fee = new_member_fee_per_league * selected_leagues_count
        expected_amount = members_basis * per_member_fee
        return {
            "expected_amount": int(expected_amount),
            "members_count": members_basis,
            "per_member_fee": int(per_member_fee),
            "selected_leagues_count": selected_leagues_count,
            "discount_amount": 0,
            "league_two_cost": 0,
            "is_new_member_payment": True,
            "status_note": None,
        }

    members_fee = members_basis * fee_per_person
    base_league_cost = fee_team + members_fee
    league_two_cost = 0
    discount_amount = 0

    if team.league_two_id is not None:
        league_two_cost = int(
            round(base_league_cost * (1 - league_two_discount_percent / 100))
        )
        discount_amount = max(0, base_league_cost - league_two_cost)

    expected_amount = base_league_cost + (league_two_cost or 0)

    return {
        "expected_amount": int(expected_amount),
        "members_count": members_basis,
        "per_member_fee": int(fee_per_person),
        "selected_leagues_count": selected_leagues_count,
        "discount_amount": int(discount_amount),
        "league_two_cost": int(league_two_cost),
        "is_new_member_payment": False,
        "status_note": None,
    }


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
                        "message_id": message.message_id,
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
    team_name = _normalize_nullable_text(request.form.get("team_name"))
    league_one_raw = request.form.get("LeagueOne")
    league_two_raw = request.form.get("LeagueTwo")
    education_level = _normalize_nullable_text(request.form.get("EducationLevel"))
    team_registration_raw = request.form.get("team_registration_date")

    team_registration_date, team_registration_error = database.parse_nullable_datetime(
        team_registration_raw
    )
    if team_registration_error:
        flash(team_registration_error, "error")
        return redirect(url_for("admin.admin_manage_client", client_id=client_id))

    if team_name:
        is_valid, error_message = utils.is_valid_team_name(team_name)
        if not is_valid:
            flash(error_message, "error")
            return redirect(url_for("admin.admin_manage_client", client_id=client_id))

    if education_level and education_level not in constants.allowed_education:
        flash("لطفاً مقطع تحصیلی معتبری انتخاب کنید.", "error")
        return redirect(url_for("admin.admin_manage_client", client_id=client_id))

    if league_two_raw and league_two_raw == league_one_raw:
        flash("نمی‌توانید یک لیگ را به عنوان لیگ اول و دوم انتخاب کنید.", "error")
        return redirect(url_for("admin.admin_manage_client", client_id=client_id))

    league_one_id = _parse_nullable_int(league_one_raw)
    league_two_id = _parse_nullable_int(league_two_raw)

    with database.get_db_session() as db:
        try:
            db.add(
                models.Team(
                    client_id=client_id,
                    team_name=team_name,
                    team_registration_date=(
                        team_registration_date
                        if team_registration_raw is not None
                        else datetime.datetime.now(datetime.timezone.utc)
                    ),
                    league_one_id=league_one_id,
                    league_two_id=league_two_id,
                    education_level=education_level,
                )
            )
            db.commit()
            flash(
                f"تیم «{team_name or 'نامشخص'}» با موفقیت برای این کاربر ساخته شد.",
                "success",
            )
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
                models.Client.email,
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
        )

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
                team
                and new_status == models.PaymentStatus.APPROVED
                and previous_status != models.PaymentStatus.APPROVED
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
                "error updating payment status for team %s: %s", team_id, error
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
                f"admin archived team '{team.team_name}' (id: {team_id}) as withdrawn.",
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
                "error in admin_delete_team for team %s: %s", team_id, error
            )
            flash("خطایی در هنگام آرشیو تیم رخ داد.", "error")

    if team:
        return redirect(url_for("admin.admin_manage_client", client_id=team.client_id))
    return redirect(url_for("admin.admin_manage_teams"))


@admin_blueprint.route("/Admin/RestoreTeam/<int:team_id>", methods=["POST"])
@admin_required
def admin_restore_team(team_id):
    """Restore an archived or inactive team and its members."""
    with database.get_db_session() as db:
        team = db.query(models.Team).filter(models.Team.team_id == team_id).first()
        if not team:
            flash("تیم یافت نشد.", "error")
            return redirect(url_for("admin.admin_manage_teams"))

        team.status = models.EntityStatus.ACTIVE
        db.query(models.Member).filter(models.Member.team_id == team_id).update(
            {"status": models.EntityStatus.ACTIVE}, synchronize_session=False
        )
        db.commit()
        flash("تیم از آرشیو خارج شد و دوباره فعال است.", "success")

    return redirect(url_for("admin.admin_manage_client", client_id=team.client_id))


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
            f"admin marked member '{member.name}' as resigned from team id {team_id}.",
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
            link_string = request.form.get("link", "").strip()
            image_file = request.files.get("image")
            html_file = request.files.get("html_file")

            if link_string and not link_string.startswith(("http://", "https://")):
                link_string = f"https://{link_string}"

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
                link=link_string or None,
                publish_date=datetime.datetime.now(datetime.timezone.utc),
                template_path=template_path,
            )

            if html_file and html_file.filename:
                html_file.stream.seek(0)
                if not html_file.filename.lower().endswith(".html"):
                    flash("فقط فایل HTML مجاز است.", "error")
                    return redirect(url_for("admin.admin_manage_news"))
                safe_name = f"{uuid.uuid4()}.html"
                os.makedirs(constants.Path.news_html_dir, exist_ok=True)
                html_path = os.path.join(constants.Path.news_html_dir, safe_name)
                html_file.save(html_path)
                new_article.template_path = f"news/htmls/{safe_name}"

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
                link_val = request.form.get("link", "").strip()
                if link_val and not link_val.startswith(("http://", "https://")):
                    link_val = f"https://{link_val}"
                article.link = link_val or None
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
                html_file = request.files.get("html_file")
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

                if html_file and html_file.filename:
                    html_file.stream.seek(0)
                    if not html_file.filename.lower().endswith(".html"):
                        flash("فقط فایل HTML مجاز است.", "error")
                        return redirect(
                            url_for("admin.admin_edit_news", article_id=article_id)
                        )
                    safe_name = f"{uuid.uuid4()}.html"
                    os.makedirs(constants.Path.news_html_dir, exist_ok=True)
                    html_path = os.path.join(constants.Path.news_html_dir, safe_name)
                    html_file.save(html_path)
                    article.template_path = f"news/htmls/{safe_name}"

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


@admin_blueprint.route("/Admin/DeleteNews/<int:article_id>", methods=["POST"])
@admin_required
def admin_delete_news(article_id):
    """Delete a news article and its assets."""

    with database.get_db_session() as db:
        article = (
            db.query(models.News).filter(models.News.news_id == article_id).first()
        )

        if not article:
            flash("خبر مورد نظر یافت نشد.", "error")
            return redirect(url_for("admin.admin_manage_news"))

        try:
            # Remove uploaded image if present
            if article.image_path:
                image_path = os.path.join(
                    current_app.config["UPLOAD_FOLDER_NEWS"], article.image_path
                )
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except OSError:
                        current_app.logger.exception(
                            "failed to remove news image %s", image_path
                        )

            # Remove uploaded HTML template if it lives under the managed news html dir
            if article.template_path and article.template_path.startswith("news/htmls/"):
                html_path = os.path.join(constants.Path.static_dir, article.template_path)
                if os.path.exists(html_path):
                    try:
                        os.remove(html_path)
                    except OSError:
                        current_app.logger.exception(
                            "failed to remove news html template %s", html_path
                        )

            db.delete(article)
            db.commit()
            flash("خبر با موفقیت حذف شد.", "success")
        except exc.SQLAlchemyError as error:
            db.rollback()
            current_app.logger.error("error deleting news %s: %s", article_id, error)
            flash("خطا در حذف خبر.", "error")

    return redirect(url_for("admin.admin_manage_news"))


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
            .options(
                joinedload(models.Team.league_one),
                joinedload(models.Team.league_two),
            )
            .outerjoin(
                models.Member,
                (models.Team.team_id == models.Member.team_id)
                & (models.Member.status == models.EntityStatus.ACTIVE),
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
            setattr(
                team, "last_payment_status", _coerce_payment_status(last_payment_status)
            )
            teams_with_status.append(team)

        archived_teams = (
            db.query(
                models.Team,
                count(models.Member.member_id).label("total_members"),
                latest_payment_subquery,
            )
            .options(
                joinedload(models.Team.league_one),
                joinedload(models.Team.league_two),
            )
            .outerjoin(
                models.Member,
                (models.Team.team_id == models.Member.team_id)
                & (models.Member.status == models.EntityStatus.ACTIVE),
            )
            .filter(
                models.Team.client_id == client_id,
                models.Team.status != models.EntityStatus.ACTIVE,
            )
            .group_by(models.Team.team_id)
            .order_by(models.Team.team_registration_date.desc())
            .all()
        )

        archived_teams_with_status = []
        for team, member_count, last_payment_status in archived_teams:
            setattr(team, "total_members", member_count)
            setattr(
                team, "last_payment_status", _coerce_payment_status(last_payment_status)
            )
            archived_teams_with_status.append(team)

        payments_history = [
            SimpleNamespace(
                payment_id=row.payment_id,
                amount=row.amount,
                status=row.status,
                members_paid_for=row.members_paid_for,
                upload_date=row.upload_date,
                receipt_filename=row.receipt_filename,
                team_name=team_name,
                client_id=row.client_id,
            )
            for row, team_name in (
                db.query(models.Payment, models.Team.team_name)
                .join(models.Team, models.Payment.team_id == models.Team.team_id)
                .filter(models.Payment.client_id == client_id)
                .order_by(models.Payment.upload_date.desc())
                .all()
            )
        ]

        documents = (
            db.query(models.TeamDocument)
            .options(joinedload(models.TeamDocument.team))
            .filter(models.TeamDocument.client_id == client_id)
            .order_by(models.TeamDocument.upload_date.desc())
            .all()
        )

    return render_template(
        constants.admin_html_names_data["admin_manage_client"],
        client=client,
        teams=teams_with_status,
        archived_teams=archived_teams_with_status,
        payments_history=payments_history,
        documents=documents,
        education_levels=constants.education_levels,
        enums=models,
    )


@admin_blueprint.route("/Admin/PendingDocuments")
@admin_required
def admin_pending_documents():
    """List all pending documents."""
    with database.get_db_session() as db:
        documents = (
            db.query(models.TeamDocument)
            .options(
                joinedload(models.TeamDocument.team),
                joinedload(models.TeamDocument.client),
            )
            .filter(models.TeamDocument.status == models.DocumentStatus.PENDING)
            .order_by(models.TeamDocument.upload_date.asc())
            .all()
        )

    return render_template(
        constants.admin_html_names_data["admin_pending_documents"],
        documents=documents,
    )


@admin_blueprint.route(
    "/Admin/ManageDocument/<int:document_id>/<action>", methods=["POST"]
)
@admin_required
def admin_manage_document(document_id, action):
    """Approve or reject a document."""
    if action not in ["approve", "reject"]:
        abort(400)

    with database.get_db_session() as db:
        document = (
            db.query(models.TeamDocument)
            .filter(models.TeamDocument.document_id == document_id)
            .first()
        )
        if not document:
            flash("مستند مورد نظر یافت نشد.", "error")
            return redirect(request.referrer or url_for("admin.admin_dashboard"))

        if action == "approve":
            document.status = models.DocumentStatus.APPROVED
            flash("مستند تایید شد.", "success")
        elif action == "reject":
            document.status = models.DocumentStatus.REJECTED
            flash("مستند رد شد.", "warning")

        db.commit()

        return redirect(
            url_for("admin.admin_manage_client", client_id=document.client_id)
        )


@admin_blueprint.route("/Admin/ManageTeams")
@admin_required
def admin_manage_teams():
    "List and manage all teams with archive and sort controls"

    status_filter = request.args.get("status", "active")
    sort = request.args.get("sort", "recent")
    payment_status = (request.args.get("payment_status", "") or "").strip()
    keyword = (request.args.get("q", "") or "").strip()
    league_id = _parse_nullable_int(request.args.get("league_id"))
    education_filter = _normalize_nullable_text(
        request.args.get("education_level")
    )

    with database.get_db_session() as db:
        last_payment_subquery = (
            select(models.Payment.status)
            .where(models.Payment.team_id == models.Team.team_id)
            .order_by(models.Payment.upload_date.desc())
            .limit(1)
            .scalar_subquery()
        )

        member_count_label = count(models.Member.member_id).label("member_count")
        leader_count_label = func.sum(
            case((models.Member.role == models.MemberRole.LEADER, 1), else_=0)
        ).label("leader_count")

        teams_query = (
            db.query(
                models.Team,
                models.Client.email.label("client_email"),
                member_count_label,
                last_payment_subquery.label("last_payment_status"),
                leader_count_label,
            )
            .join(models.Client, models.Team.client_id == models.Client.client_id)
            .outerjoin(
                models.Member,
                (models.Team.team_id == models.Member.team_id)
                & (models.Member.status == models.EntityStatus.ACTIVE),
            )
            .options(
                joinedload(models.Team.league_one), joinedload(models.Team.league_two)
            )
            .group_by(models.Team.team_id, models.Client.email)
        )

        incomplete_only = request.args.get("incomplete") == "1"

        if status_filter == "archived":
            teams_query = teams_query.filter(
                models.Team.status != models.EntityStatus.ACTIVE
            )
        elif status_filter != "all":
            teams_query = teams_query.filter(
                models.Team.status == models.EntityStatus.ACTIVE
            )

        if keyword:
            keyword_like = f"%{keyword}%"
            teams_query = teams_query.filter(
                or_(
                    models.Team.team_name.ilike(keyword_like),
                    models.Client.email.ilike(keyword_like),
                    models.Client.phone_number.ilike(keyword_like),
                    func.cast(models.Team.team_id, String).ilike(keyword_like),
                )
            )

        if league_id:
            teams_query = teams_query.filter(
                or_(
                    models.Team.league_one_id == league_id,
                    models.Team.league_two_id == league_id,
                )
            )

        if education_filter:
            teams_query = teams_query.filter(
                models.Team.education_level == education_filter
            )

        if incomplete_only:
            teams_query = teams_query.having(
                or_(leader_count_label == 0, models.Team.team_name == None)
            )

        if payment_status:
            try:
                status_enum = getattr(models.PaymentStatus, payment_status)
                teams_query = teams_query.having(last_payment_subquery == status_enum)
            except AttributeError:
                pass

        if sort == "name_asc":
            teams_query = teams_query.order_by(func.lower(models.Team.team_name))
        elif sort == "name_desc":
            teams_query = teams_query.order_by(func.lower(models.Team.team_name).desc())
        elif sort == "members_desc":
            teams_query = teams_query.order_by(member_count_label.desc())
        elif sort == "oldest":
            teams_query = teams_query.order_by(models.Team.team_registration_date.asc())
        else:
            teams_query = teams_query.order_by(
                models.Team.team_registration_date.desc()
            )

        team_rows = teams_query.all()

        all_teams = []
        for (
            team,
            client_email,
            member_count,
            last_payment_status,
            leader_count,
        ) in team_rows:
            setattr(
                team, "last_payment_status", _coerce_payment_status(last_payment_status)
            )
            all_teams.append(
                SimpleNamespace(
                    team_id=team.team_id,
                    team_name=team.team_name,
                    client_email=client_email,
                    member_count=member_count,
                    status=team.status,
                    last_payment_status=team.last_payment_status,
                    league_one=team.league_one,
                    league_two=team.league_two,
                    education_level=team.education_level,
                    team_registration_date=team.team_registration_date,
                    has_leader=bool(leader_count),
                    is_name_missing=not bool(team.team_name),
                )
            )

    return render_template(
        constants.admin_html_names_data["admin_manage_teams"],
        teams=all_teams,
        status_filter=status_filter,
        payment_filter=payment_status,
        sort_option=sort,
        league_filter=league_id,
        education_filter=education_filter,
        keyword=keyword,
        incomplete_filter=incomplete_only,
        enums=models,
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
                new_team_name = _normalize_nullable_text(request.form.get("team_name"))
                league_one_id = _parse_nullable_int(request.form.get("league_one_id"))
                league_two_id = _parse_nullable_int(request.form.get("league_two_id"))
                education_level = _normalize_nullable_text(request.form.get("education_level"))
                registration_raw = request.form.get("team_registration_date")

                registration_date, registration_error = database.parse_nullable_datetime(
                    registration_raw
                )
                if registration_error:
                    flash(registration_error, "error")
                    return redirect(url_for("admin.admin_edit_team", team_id=team_id))

                if new_team_name:
                    is_valid, error_message = utils.is_valid_team_name(new_team_name)
                    if not is_valid:
                        flash(error_message, "error")
                        return redirect(url_for("admin.admin_edit_team", team_id=team_id))

                    existing_team = (
                        db.query(models.Team)
                        .filter(
                            func.lower(models.Team.team_name)
                            == func.lower(new_team_name),
                            models.Team.team_id != team_id,
                        )
                        .first()
                    )
                    if existing_team:
                        flash("تیمی با این نام از قبل وجود دارد.", "error")
                        return redirect(url_for("admin.admin_edit_team", team_id=team_id))

                if (
                    education_level
                    and education_level not in constants.allowed_education
                ):
                    flash("مقطع تحصیلی انتخاب شده معتبر نیست.", "error")
                    return redirect(url_for("admin.admin_edit_team", team_id=team_id))

                if education_level and education_level != (team.education_level or ""):
                    level_info = constants.education_levels.get(education_level)
                    age_range = level_info.get("ages") if level_info else None
                    if age_range:
                        min_age, max_age = age_range
                        violating_member = None
                        for member in team.members:
                            if (
                                member.status == models.EntityStatus.ACTIVE
                                and member.role == models.MemberRole.MEMBER
                            ):
                                age = utils.calculate_age(member.birth_date)
                                if age is not None:
                                    is_below = min_age is not None and age < min_age
                                    is_above = max_age is not None and age > max_age
                                    if is_below or is_above:
                                        violating_member = member
                                        break
                        
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
                setattr(team, "league_one_id", league_one_id)
                setattr(team, "league_two_id", league_two_id)
                team.education_level = education_level or None
                if registration_raw is not None:
                    team.team_registration_date = registration_date
                db.commit()
                utils.update_team_stats(db, team_id)
                flash("جزئیات تیم با موفقیت ذخیره شد", "success")

            except (exc.SQLAlchemyError, ValueError) as error:
                db.rollback()
                current_app.logger.error(
                    "error in admin_edit_team for team %s: %s", team_id, error
                )
                flash("خطایی در هنگام ویرایش تیم رخ داد.", "error")

            return redirect(url_for("admin.admin_edit_team", team_id=team_id))

        members = (
            db.query(models.Member)
            .options(joinedload(models.Member.city).joinedload(models.City.province))
            .filter(
                models.Member.team_id == team_id,
                models.Member.status == models.EntityStatus.ACTIVE,
            )
            .all()
        )
        form_context = utils.get_form_context()

        payments = (
            db.query(models.Payment)
            .filter(models.Payment.team_id == team_id)
            .order_by(models.Payment.upload_date.desc())
            .all()
        )

        last_payment = payments[0] if payments else None

        # Calculate Payable Amount
        active_members_count = sum(1 for m in members if m.status == models.EntityStatus.ACTIVE)
        has_approved_payment = database.check_if_team_is_paid(db, team_id)
        
        fee_per_person = config.payment_config.get("fee_per_person") or 0
        fee_team = config.payment_config.get("fee_team") or 0
        league_two_discount = config.payment_config.get("league_two_discount") or 0
        new_member_fee_per_league = config.payment_config.get("new_member_fee_per_league") or 0

        payable_amount = 0
        if has_approved_payment:
            # Team has paid initially, so they only pay for new (unpaid) members
            if team.unpaid_members_count > 0:
                num_leagues = 1 + (1 if team.league_two_id else 0)
                payable_amount = team.unpaid_members_count * new_member_fee_per_league * num_leagues
        else:
            # Initial payment calculation
            members_fee = active_members_count * fee_per_person
            base_cost = fee_team + members_fee
            
            league_two_cost = 0
            if team.league_two_id:
                league_two_cost = int(round(base_cost * (1 - league_two_discount / 100)))
            
            payable_amount = base_cost + league_two_cost

    return render_template(
        constants.admin_html_names_data["admin_edit_team"],
        team=team,
        members=members,
        payments=payments,
        education_levels=constants.education_levels,
        last_payment=last_payment,
        payable_amount=payable_amount,
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

            team = db.query(models.Team).filter(models.Team.team_id == team_id).first()
            education_level = getattr(team, "education_level", None) if team else None

            is_valid_age, age_error = utils.validate_member_age(
                updated_member_data["birth_date"],
                updated_member_data["role"],
                education_level,
            )
            if not is_valid_age:
                flash(
                    age_error or "سن عضو با مقطع تحصیلی انتخاب شده سازگار نیست.",
                    "error",
                )
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
                member_to_update.phone_number = updated_member_data["phone_number"]
                member_to_update.gender = updated_member_data["gender"]
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
    "List and manage clients with pagination and archiving controls"

    page = request.args.get("page", 1, type=int)
    per_page = 10
    status_filter = request.args.get("status", "active")
    keyword = (request.args.get("q", "") or "").strip()

    with database.get_db_session() as db:
        clients_query = db.query(models.Client)

        if status_filter == "archived":
            clients_query = clients_query.filter(
                models.Client.status != models.EntityStatus.ACTIVE
            )
        elif status_filter != "all":
            clients_query = clients_query.filter(
                models.Client.status == models.EntityStatus.ACTIVE
            )

        if keyword:
            clients_query = clients_query.filter(
                or_(
                    models.Client.email.ilike(f"%{keyword}%"),
                    models.Client.phone_number.ilike(f"%{keyword}%"),
                )
            )

        total_filtered = (clients_query.count()) or 0

        clients = (
            clients_query.order_by(models.Client.registration_date.desc())
            .limit(per_page)
            .offset((page - 1) * per_page)
            .all()
        )

    total_pages = math.ceil(total_filtered / per_page) if total_filtered else 0

    return render_template(
        constants.admin_html_names_data["admin_clients_list"],
        Clients=clients,
        CurrentPage=page,
        TotalPagesCount=total_pages,
        FilterStatus=status_filter,
        Keyword=keyword,
        enums=models,
    )


@admin_blueprint.route("/Admin/AddClient", methods=["POST"])
@admin_required
def admin_add_client():
    "add a new client to the database"
    email_raw = bleach.clean(
        (request.form.get("email") or request.form.get("Email") or "").strip().lower()
    )
    email = email_raw or None
    phone = persiantools.digits.fa_to_en(
        (request.form.get("phone_number") or request.form.get("PhoneNumber") or "")
    ).strip()
    password = request.form.get("password") or request.form.get("Password") or ""
    registration_raw = request.form.get("registration_date")

    registration_date_value = None
    if registration_raw is not None:
        registration_date_value, date_error = database.parse_nullable_datetime(
            registration_raw
        )
        if date_error:
            flash(date_error, "error")
            return redirect(url_for("admin.admin_clients_list"))

    validation_errors = []

    if email and not utils.is_valid_email(email):
        validation_errors.append("ایمیل وارد شده معتبر نیست.")

    if not utils.is_valid_iranian_phone(phone):
        validation_errors.append(
            "شماره همراه معتبر نیست (لطفا با ارقام انگلیسی و فرمت 09XXXXXXXXX وارد کنید)."
        )

    if not password:
        validation_errors.append("رمز عبور موقت را وارد کنید.")

    if validation_errors:
        flash(" ".join(validation_errors), "error")
        return redirect(url_for("admin.admin_clients_list"))

    with database.get_db_session() as db:
        try:
            existing_phone = (
                db.query(models.Client)
                .filter(models.Client.phone_number == phone)
                .first()
            )
            if existing_phone:
                flash("کاربری با این شماره تلفن از قبل وجود دارد.", "error")
                return redirect(url_for("admin.admin_clients_list"))

            if email:
                existing_email = (
                    db.query(models.Client)
                    .filter(func.lower(models.Client.email) == func.lower(email))
                    .first()
                )
                if existing_email:
                    flash("کاربری با این ایمیل از قبل وجود دارد.", "error")
                    return redirect(url_for("admin.admin_clients_list"))

            db.add(
                models.Client(
                    phone_number=phone,
                    email=email,
                    password=bcrypt.hashpw(
                        password.encode("utf-8"), bcrypt.gensalt()
                    ).decode("utf-8"),
                    registration_date=registration_date_value,
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
            current_app.logger.error("error editing client %s: %s", client_id, error)
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

            db.query(models.Member).filter(
                models.Member.team_id.in_(
                    db.query(models.Team.team_id).filter(
                        models.Team.client_id == client_id
                    )
                )
            ).update(
                {"status": models.EntityStatus.INACTIVE}, synchronize_session=False
            )

            db.commit()
            flash("کاربر و تمام تیم‌های مرتبط با او با موفقیت غیرفعال شدند.", "success")
        else:
            flash("کاربر یافت نشد.", "error")
    return redirect(url_for("admin.admin_clients_list"))


@admin_blueprint.route("/Admin/RestoreClient/<int:client_id>", methods=["POST"])
@admin_required
def admin_restore_client(client_id):
    """Restore a previously archived client and their teams."""
    with database.get_db_session() as db:
        client = (
            db.query(models.Client).filter(models.Client.client_id == client_id).first()
        )
        if not client:
            flash("کاربر یافت نشد.", "error")
            return redirect(url_for("admin.admin_clients_list"))

        client.status = models.EntityStatus.ACTIVE
        db.query(models.Team).filter(models.Team.client_id == client_id).update(
            {"status": models.EntityStatus.ACTIVE}, synchronize_session=False
        )
        db.query(models.Member).filter(
            models.Member.team_id.in_(
                db.query(models.Team.team_id).filter(models.Team.client_id == client_id)
            )
        ).update({"status": models.EntityStatus.ACTIVE}, synchronize_session=False)
        db.commit()
        flash("کاربر و تیم‌های او دوباره فعال شدند.", "success")

    return redirect(url_for("admin.admin_manage_client", client_id=client_id))


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
                models.Client.registration_date
                >= datetime.datetime.now(datetime.timezone.utc)
                - datetime.timedelta(days=7),
            )
            .count()
        )

        total_income = (
            db.query(func.sum(models.Payment.amount))
            .filter(models.Payment.status == models.PaymentStatus.APPROVED)
            .scalar()
        ) or 0

        stats = {
            "total_clients": total_clients,
            "total_teams": total_teams,
            "approved_teams": approved_teams,
            "total_members": total_members,
            "total_leaders": total_leaders,
            "total_coaches": total_coaches,
            "new_clients_this_week": new_clients_this_week,
            "total_income": total_income,
        }

        # --- New Statistics ---
        # 1. League Popularity
        league_counts = {}
        active_teams = (
            db.query(models.Team)
            .options(joinedload(models.Team.league_one), joinedload(models.Team.league_two))
            .filter(models.Team.status == models.EntityStatus.ACTIVE)
            .all()
        )
        for team in active_teams:
            if team.league_one:
                league_counts[team.league_one.name] = league_counts.get(team.league_one.name, 0) + 1
            if team.league_two:
                league_counts[team.league_two.name] = league_counts.get(team.league_two.name, 0) + 1
        
        league_stats = [
            {"name": k, "count": v} 
            for k, v in sorted(league_counts.items(), key=lambda item: item[1], reverse=True)
        ]

        # 2. Gender Stats
        gender_data = (
            db.query(models.Member.gender, func.count(models.Member.member_id))
            .filter(models.Member.status == models.EntityStatus.ACTIVE)
            .group_by(models.Member.gender)
            .all()
        )
        gender_stats = {
            "male": 0,
            "female": 0,
            "unknown": 0
        }
        for gender_enum, count_val in gender_data:
            if gender_enum == models.Gender.MALE:
                gender_stats["male"] = count_val
            elif gender_enum == models.Gender.FEMALE:
                gender_stats["female"] = count_val
            else:
                gender_stats["unknown"] += count_val
        
        total_gender_count = sum(gender_stats.values()) or 1
        gender_stats["male_percent"] = round((gender_stats["male"] / total_gender_count) * 100, 1)
        gender_stats["female_percent"] = round((gender_stats["female"] / total_gender_count) * 100, 1)

        # New: Average Age by Gender
        gender_age_data = (
            db.query(models.Member.gender, models.Member.birth_date)
            .filter(models.Member.status == models.EntityStatus.ACTIVE,
                    models.Member.birth_date.isnot(None))
            .all()
        )

        male_ages = []
        female_ages = []
        for gender, birth_date in gender_age_data:
            age = utils.calculate_age(birth_date)
            if gender == models.Gender.MALE:
                male_ages.append(age)
            elif gender == models.Gender.FEMALE:
                female_ages.append(age)
        
        gender_stats["average_male_age"] = round(sum(male_ages) / len(male_ages)) if male_ages else 0
        gender_stats["average_female_age"] = round(sum(female_ages) / len(female_ages)) if female_ages else 0

        # 3. Server Stats
        server_stats = {}
        try:
            total_disk, used_disk, free_disk = shutil.disk_usage("/")
            server_stats["disk_percent"] = round((used_disk / total_disk) * 100, 1)
            server_stats["disk_free_gb"] = round(free_disk / (1024**3), 1)
        except Exception:
            server_stats["disk_percent"] = 0
            server_stats["disk_free_gb"] = 0

        # 4. Top Viewed News
        top_news = (
            db.query(models.News)
            .order_by(models.News.views.desc())
            .limit(5)
            .all()
        )

        active_member_counts = (
            db.query(
                models.Member.team_id,
                func.count(models.Member.member_id).label("count"),
            )
            .filter(models.Member.status == models.EntityStatus.ACTIVE)
            .group_by(models.Member.team_id)
            .all()
        )
        active_member_map = {row.team_id: row.count for row in active_member_counts}

        pending_payments_rows = (
            db.query(
                models.Payment,
                models.Team,
                models.Client.email,
                models.Client.phone_number.label("client_phone_number"),
            )
            .join(models.Team, models.Payment.team_id == models.Team.team_id)
            .join(models.Client, models.Payment.client_id == models.Client.client_id)
            .options(
                joinedload(models.Team.league_one), joinedload(models.Team.league_two)
            )
            .filter(models.Payment.status == models.PaymentStatus.PENDING)
            .order_by(models.Payment.upload_date.asc())
            .all()
        )

        pending_payments = []
        for payment, team, client_email, client_phone_number in pending_payments_rows:
            active_members = active_member_map.get(team.team_id, 0)
            has_approved_payment = database.check_if_team_is_paid(db, team.team_id)
            expected_payment = _summarize_expected_payment(
                team,
                payment,
                active_members,
                has_approved_payment,
            )

            pending_payments.append(
                {
                    "payment_id": payment.payment_id,
                    "client_id": payment.client_id,
                    "team_id": team.team_id,
                    "team_name": team.team_name or "نام تیم نامشخص",
                    "league_one_name": getattr(team.league_one, "name", None),
                    "league_two_name": getattr(team.league_two, "name", None),
                    "education_level": team.education_level or "—",
                    "client_email": client_email or "ایمیل نامشخص",
                    "client_phone": client_phone_number,
                    "amount": payment.amount,
                    "members_paid_for": payment.members_paid_for,
                    "upload_date": payment.upload_date,
                    "paid_at": payment.paid_at,
                    "tracking_number": payment.tracking_number,
                    "payer_name": payment.payer_name,
                    "payer_phone": payment.payer_phone,
                    "receipt_filename": payment.receipt_filename,
                    "expected_payment": expected_payment,
                    "active_members": active_members,
                    "unpaid_members": team.unpaid_members_count,
                }
            )

    return render_template(
        constants.admin_html_names_data["admin_dashboard"],
        stats=stats,
        league_stats=league_stats,
        gender_stats=gender_stats,
        server_stats=server_stats,
        top_news=top_news,
        pending_payments=pending_payments,
        pending_payments_count=len(pending_payments),
        admin_greeting_name=session.get("admin_display_name", "مدیر محترم"),
    )


@admin_blueprint.route("/Admin/DownloadDatabase")
@admin_required
def admin_download_db():
    """Download the current SQLite database file."""
    try:
        db_path = constants.Path.database
        if not os.path.exists(db_path):
            flash("فایل دیتابیس یافت نشد.", "error")
            return redirect(url_for("admin.admin_dashboard"))
        
        return send_from_directory(
            os.path.dirname(db_path),
            os.path.basename(db_path),
            as_attachment=True,
            download_name=f"airocup_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.db"
        )
    except Exception as e:
        current_app.logger.error(f"Error downloading DB: {e}")
        flash("خطا در دانلود دیتابیس.", "error")
        return redirect(url_for("admin.admin_dashboard"))


@admin_blueprint.route("/Admin/Search")
@admin_required
def admin_search():
    """Unified search page for clients, teams, and payments."""
    query = (request.args.get("q", "") or "").strip()
    payment_status = (request.args.get("payment_status", "") or "").strip()
    client_status = request.args.get("client_status", "all")
    team_status = request.args.get("team_status", "all")
    client_sort = request.args.get("client_sort", "recent")
    team_sort = request.args.get("team_sort", "recent")
    payment_sort = request.args.get("payment_sort", "recent")
    league_id_1 = _parse_nullable_int(request.args.get("league_id"))
    league_id_2 = _parse_nullable_int(request.args.get("league_id_2"))
    education_filter = _normalize_nullable_text(
        request.args.get("education_level")
    )
    has_document_filter = request.args.get("has_document")

    with database.get_db_session() as db:
        clients = []
        teams = []
        payments = []

        client_query = db.query(models.Client)
        client_keyword = f"%{query}%" if query else "%"
        client_query = client_query.filter(
            or_(
                models.Client.email.ilike(client_keyword),
                models.Client.phone_number.ilike(client_keyword),
            )
        )
        if client_status == "archived":
            client_query = client_query.filter(
                models.Client.status != models.EntityStatus.ACTIVE
            )
        elif client_status != "all":
            client_query = client_query.filter(
                models.Client.status == models.EntityStatus.ACTIVE
            )

        if client_sort == "email":
            client_query = client_query.order_by(func.lower(models.Client.email))
        elif client_sort == "oldest":
            client_query = client_query.order_by(
                models.Client.registration_date.asc()
            )
        else:
            client_query = client_query.order_by(
                models.Client.registration_date.desc()
            )
        clients = client_query.limit(150).all()

        team_query = db.query(models.Team).join(models.Client).options(
            joinedload(models.Team.client),
            joinedload(models.Team.league_one),
            joinedload(models.Team.league_two),
            joinedload(models.Team.documents),
        )
        if query:
            keyword_like = f"%{query}%"
            team_query = team_query.filter(
                or_(
                    models.Team.team_name.ilike(keyword_like),
                    models.Client.email.ilike(keyword_like),
                    models.Client.phone_number.ilike(keyword_like),
                    func.cast(models.Team.team_id, String).ilike(keyword_like),
                )
            )
        if team_status == "archived":
            team_query = team_query.filter(
                models.Team.status != models.EntityStatus.ACTIVE
            )
        elif team_status != "all":
            team_query = team_query.filter(
                models.Team.status == models.EntityStatus.ACTIVE
            )

        if league_id_1:
            team_query = team_query.filter(
                or_(
                    models.Team.league_one_id == league_id_1,
                    models.Team.league_two_id == league_id_1,
                )
            )
            
        if league_id_2:
            team_query = team_query.filter(
                or_(
                    models.Team.league_one_id == league_id_2,
                    models.Team.league_two_id == league_id_2,
                )
            )

        if education_filter:
            team_query = team_query.filter(
                models.Team.education_level == education_filter
            )

        if has_document_filter == "yes":
            team_query = team_query.filter(models.Team.documents.any())
        elif has_document_filter == "no":
            team_query = team_query.filter(~models.Team.documents.any())

        if team_sort == "name":
            team_query = team_query.order_by(func.lower(models.Team.team_name))
        elif team_sort == "oldest":
            team_query = team_query.order_by(
                models.Team.team_registration_date.asc()
            )
        else:
            team_query = team_query.order_by(
                models.Team.team_registration_date.desc()
            )
        teams = team_query.limit(300).all()

        payment_query = db.query(models.Payment)
        if payment_status:
            try:
                status_enum = getattr(models.PaymentStatus, payment_status)
                payment_query = payment_query.filter(
                    models.Payment.status == status_enum
                )
            except AttributeError:
                payment_query = payment_query.filter(False)

        if query:
            keyword_like = f"%{query}%"
            payment_query = payment_query.filter(
                or_(
                    func.cast(models.Payment.payment_id, String).ilike(keyword_like),
                    func.cast(models.Payment.team_id, String).ilike(keyword_like),
                    models.Payment.payer_name.ilike(keyword_like),
                    models.Payment.payer_phone.ilike(keyword_like),
                    models.Payment.tracking_number.ilike(keyword_like),
                )
            )

        if payment_sort == "amount":
            payment_query = payment_query.order_by(models.Payment.amount.desc())
        else:
            payment_query = payment_query.order_by(models.Payment.upload_date.desc())
        payments = payment_query.limit(100).all()

        members = []
        if query:
            member_query = (
                db.query(models.Member)
                .options(
                    joinedload(models.Member.team).joinedload(models.Team.client),
                    joinedload(models.Member.city).joinedload(models.City.province),
                )
            )
            keyword_like = f"%{query}%"
            member_query = member_query.filter(
                or_(
                    models.Member.name.ilike(keyword_like),
                    models.Member.national_id.ilike(keyword_like),
                    models.Member.phone_number.ilike(keyword_like),
                )
            )
            if team_status == "archived":
                member_query = member_query.filter(
                    models.Member.status != models.EntityStatus.ACTIVE
                )
            elif team_status != "all":
                member_query = member_query.filter(
                    models.Member.status == models.EntityStatus.ACTIVE
                )
                
            members = member_query.limit(300).all()

        return render_template(
            constants.admin_html_names_data["admin_search"],
            query=query,
            payment_status=payment_status,
            client_status=client_status,
            team_status=team_status,
            client_sort=client_sort,
            team_sort=team_sort,
            payment_sort=payment_sort,
            league_filter_1=league_id_1,
            league_filter_2=league_id_2,
            education_filter=education_filter,
            has_document_filter=has_document_filter,
            clients=clients,
            teams=teams,
            payments=payments,
            members=members,
            enums=models,
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
                    f"admin approved payment id {payment_id} for team id {payment.team_id}.",
                    is_admin_action=True,
                )
                flash("پرداخت با موفقیت تایید شد و اعضای تیم فعال شدند.", "success")

            elif action == "reject":
                payment.status = models.PaymentStatus.REJECTED
                database.log_action(
                    db_session,
                    payment.client_id,
                    f"admin rejected payment id {payment_id} for team id {payment.team_id}.",
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


@admin_blueprint.route("/Admin/Logs")
@admin_required
def admin_logs():
    """Display recent action logs for visibility and auditing."""
    with database.get_db_session() as db:
        logs = (
            db.query(models.HistoryLog)
            .order_by(models.HistoryLog.timestamp.desc())
            .limit(200)
            .all()
        )

        return render_template(
            constants.admin_html_names_data["admin_logs"],
            logs=logs,
        )
