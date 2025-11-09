"Backend application for the Airocup website using Flask framework"

import os
import sys
import getpass
import traceback
import datetime
import logging
import bcrypt
import jdatetime
from persiantools.digits import en_to_fa
from sqlalchemy import exc, func
import bleach
from waitress import serve
from flask import (
    Flask,
    render_template,
    request,
    send_from_directory,
    session,
    jsonify,
    has_request_context,
)
from flask_socketio import emit, join_room
from jinja2 import TemplateError
from . import config
from . import database
from . import constants
from . import models
from . import admin
from . import client
from . import globals as globals_file
from .auth import admin_required
from .extensions import csrf_protector, limiter, socket_io

flask_app = Flask(
    __name__,
    static_folder=constants.Path.static_dir,
    template_folder=constants.Path.templates_dir,
    static_url_path="",
)
flask_app.secret_key = config.secret_key
csrf_protector.init_app(flask_app)
socket_io.init_app(flask_app)
limiter.init_app(flask_app)

flask_app.config.update(
    PERMANENT_SESSION_LIFETIME=config.permanent_session_lifetime,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    UPLOAD_FOLDER_RECEIPTS=constants.Path.receipts_dir,
    UPLOAD_FOLDER_DOCUMENTS=os.path.join(constants.Path.uploads_dir, "Documents"),
    UPLOAD_FOLDER_NEWS=constants.Path.news_dir,
    MAX_CONTENT_LENGTH=constants.AppConfig.max_document_size,
    ALLOWED_EXTENSIONS=list(constants.AppConfig.allowed_extensions),
)

flask_app.register_blueprint(admin.admin_blueprint)
flask_app.register_blueprint(client.client_blueprint)
flask_app.register_blueprint(globals_file.global_blueprint)

for path in [
    flask_app.config["UPLOAD_FOLDER_RECEIPTS"],
    flask_app.config["UPLOAD_FOLDER_DOCUMENTS"],
    flask_app.config["UPLOAD_FOLDER_NEWS"],
    os.path.dirname(constants.Path.database_dir),
]:
    os.makedirs(path, exist_ok=True)


@flask_app.template_filter("formatdate")
def format_date_filter(date_object):
    """Formats a datetime object to a Persian date string (YYYY-MM-DD)."""
    if not isinstance(date_object, datetime.datetime):
        return ""
    return jdatetime.datetime.fromgregorian(datetime=date_object).strftime("%Y-%m-%d")


@flask_app.template_filter("humanize_number")
def humanize_number_filter(num):
    """Formats a number with commas for thousands separators."""
    try:
        return f"{int(num):,}"
    except (ValueError, TypeError):
        return num


@flask_app.context_processor
def inject_global_variables():
    """Injects global variables into the template context."""
    airocup_data = {
        "DaysInMonth": constants.Date.days_in_month,
        "AllowedYears": constants.Date.get_allowed_years(),
        "PersianMonths": constants.Date.persian_months,
        "ForbiddenWords": list(constants.ForbiddenContent.custom_words),
        "client_id": session.get("client_id") if has_request_context() else None,
        "provinces_data": constants.provinces_data,
    }

    return {
        "Path": constants.Path,
        "AppConfig": {
            "MaxTeamPerClient": constants.AppConfig.max_team_per_client,
            "MaxMembersPerTeam": constants.AppConfig.max_members_per_team,
        },
        "Contact": constants.Contact,
        "Event": constants.Details,
        "HTMLnames": constants.global_html_names_data,
        "Location": constants.Details.address,
        "ContactPoints": constants.contact_points_data,
        "CooperationOpportunities": constants.cooperation_opportunities_data,
        "jdatetime": jdatetime,
        "AirocupData": airocup_data,
        "Payment": config.payment_config,
        "LeaguesList": constants.leagues_list,
        "CommitteeMembers": constants.committee_members_data,
        "TechnicalCommitteeMembers": constants.technical_committee_members,
        "HomepageSponsors": constants.homepage_sponsors_data,
    }


@flask_app.template_filter("persian_digits")
def persian_digits_filter(content):
    "Converts English digits in the content to Persian digits"
    return en_to_fa(str(content))


@flask_app.template_filter("basename")
def basename_filter(path_string):
    "Returns the base name of a given path string"
    return os.path.basename(path_string)


@flask_app.errorhandler(400)
def handle_bad_request(error):
    """Handles 400 Bad Request errors."""
    flask_app.logger.warning(
        "Bad request (400) at %s from %s: %s",
        request.url,
        request.remote_addr,
        error,
    )
    return (
        render_template(
            constants.global_html_names_data["400"],
            error=str(error),
        ),
        400,
    )


@flask_app.errorhandler(403)
def handle_forbidden(error):
    """Handles 403 Forbidden errors."""
    flask_app.logger.warning(
        "Forbidden (403) access attempt at %s by %s: %s",
        request.url,
        request.remote_addr,
        error,
    )
    return render_template(constants.global_html_names_data["403"]), 403


@flask_app.errorhandler(500)
def handle_server_error(error):
    """Handles 500 Internal Server errors."""
    flask_app.logger.error(
        "Internal Server Error (500) on %s %s from %s:\n%s",
        request.method,
        request.url,
        request.remote_addr,
        traceback.format_exc(),
    )

    if flask_app.debug:
        return (
            render_template(
                constants.global_html_names_data["500 Debug"],
                error=traceback.format_exc(),
            ),
            500,
        )
    return render_template(constants.global_html_names_data["500"]), 500


@socket_io.on("join")
def on_join_message(data_dictionary):
    """Handles a user joining a chat room."""
    room_name = data_dictionary.get("Room")
    client_id = session.get("client_id")

    if session.get("AdminLoggedIn", False):
        join_room(room_name)
        flask_app.logger.info("Admin joined room %s", room_name)
    elif client_id and str(client_id) == str(room_name):
        join_room(str(client_id))
        flask_app.logger.info("Client %s joined their room", client_id)
    else:
        flask_app.logger.warning(
            "Unauthorized chat room join attempt by session %s for room %s",
            client_id,
            room_name,
        )
        return


@socket_io.on("send_message")
def handle_send_message(json_data):
    """Handles incoming chat messages and broadcasts them to the appropriate room."""
    try:
        if not isinstance(json_data, dict):
            return

        message = str(json_data.get("message") or "").strip()
        target_room = json_data.get("room")

        if not message or not target_room:
            return

        if session.get("AdminLoggedIn", False):
            sender_type = "admin"
        elif session.get("client_id") and str(session.get("client_id")) == str(
            target_room
        ):
            sender_type = "client"
        else:
            flask_app.logger.warning(
                "Unauthorized chat message attempt by session %s in room %s",
                session.get("client_id"),
                target_room,
            )
            return

        sanitized_message = bleach.clean(message)
        if len(sanitized_message) > 1000:
            sanitized_message = sanitized_message[:1000]

        with database.get_db_session() as db:
            database.save_chat_message(
                db, int(target_room), sanitized_message, sender_type
            )

        current_time = datetime.datetime.now(datetime.timezone.utc)
        emit(
            "new_message",
            {
                "message": sanitized_message,
                "timestamp": current_time.isoformat(),
                "sender": sender_type,
            },
            to=str(target_room),
        )

    except (ValueError, TypeError, exc.SQLAlchemyError) as error:
        flask_app.logger.error("Chat message error: %s", error)


@flask_app.route("/uploads/receipts/<filename>")
@admin_required
def uploaded_receipt_file(filename):
    "Serves uploaded receipt files to admin users"
    return send_from_directory(constants.Path.receipts_dir, filename)


@flask_app.template_filter("to_iso_format")
def to_iso_format_filter(date_object):
    "Converts a datetime object to ISO 8601 format"
    if not isinstance(date_object, datetime.datetime):
        return ""
    return date_object.isoformat()


def get_distribution_query(db, entity, join_chain, label="count", limit=10):
    """Generic helper to build distribution queries for City/Province/etc."""
    query = (
        db.query(
            entity.name.label("name"),
            func.count(models.Member.member_id).label(
                label
            ),  # pylint: disable=not-callable
        )
        .join(*join_chain)
        .filter(models.Member.status == models.EntityStatus.ACTIVE)
        .group_by(entity.name)
        .order_by(
            func.count(models.Member.member_id).desc()
        )  # pylint: disable=not-callables
        .limit(limit)
    )
    return query.all()


@flask_app.route("/API/AdminCityDistribution")
@admin_required
def api_city_distribution():
    """Returns JSON data for city distribution of active members."""
    with database.get_db_session() as db:
        city_data = get_distribution_query(
            db,
            models.City,
            [models.City, models.Member.city_id == models.City.city_id],
        )

    return jsonify(
        {
            "Labels": [row.name for row in city_data],
            "Data": [row.count for row in city_data],
        }
    )


@flask_app.route("/API/admin/ProvinceDistribution")
@admin_required
def api_province_distribution():
    """Returns JSON data for province distribution of active members."""
    with database.get_db_session() as db:
        province_data = get_distribution_query(
            db,
            models.Province,
            [
                (models.City, models.Member.city_id == models.City.city_id),
                (
                    models.Province,
                    models.City.province_id == models.Province.province_id,
                ),
            ],
        )

    return jsonify(
        {
            "Labels": [row.name for row in province_data],
            "Data": [row.count for row in province_data],
        }
    )


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def print_startup_message(host: str, port: int, mode: str) -> None:
    """Logs the startup message for the server."""
    border = "=" * 60
    logger.info(border)
    logger.info("🚀 Airocup Backend Server is launching...")
    logger.info("   - Version: %s", config.app_version)
    logger.info("   - Mode: %s", mode)
    logger.info("   - Database: Verified and connected successfully.")
    logger.info("   - Listening on: http://%s:%s", host, port)
    logger.info(border)


def test_templates() -> None:
    """Tests all templates for rendering errors"""
    logger.info("🔍 Starting template integrity check...")
    template_dir = constants.Path.templates_dir
    templates = [f for f in os.listdir(template_dir) if f.endswith(".html")]
    success_count, fail_count = 0, 0

    with flask_app.app_context():
        for template in templates:
            try:
                with flask_app.test_request_context("/"):
                    render_template(template)
                logger.info("✅ %s: OK", template)
                success_count += 1
            except TemplateError as e:
                logger.error("❌ %s: FAILED (%s)", template, e)
                fail_count += 1

    logger.info("Template check finished. %d successful, %d failed.", success_count, fail_count)
    if fail_count > 0:
        logger.critical("🚨 Please fix the failing templates before proceeding.")
        sys.exit(1)


@flask_app.cli.command("init-db")
def initialize_database_command() -> None:
    """Creates the database tables and populates geography data."""
    database.create_database()
    database.populate_geography_data()
    logger.info("Database initialized successfully.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "generate_hash":
        try:
            admin_password = getpass.getpass("رمز عبور ادمین مورد نظر را وارد کنید: ")
            if admin_password:
                logger.info("✅ هش ادمین شما با موفقیت ایجاد شد.")
                logger.info("خط زیر را کپی کرده و در فایل config.py خود جای‌گذاری کنید:")
                logger.info("-" * 50)
                logger.info(
                    "AdminPasswordHash = '%s'",
                    bcrypt.hashpw(
                        admin_password.encode("utf-8"), bcrypt.gensalt()
                    ).decode("utf-8"),
                )
                logger.info("-" * 50)
            else:
                logger.warning("رمز عبور نمی‌تواند خالی باشد.")
        except (KeyboardInterrupt, EOFError, ValueError) as error:
            logger.error("خطایی رخ داد: %s", error)
        sys.exit()

    host, port = "0.0.0.0", 5000
    MODE = "✅ Debug" if config.debug else "⛔ Production"

    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        print_startup_message(host, port, MODE)
        test_templates()

    if config.debug:
        socket_io.run(flask_app, host=host, port=port, debug=config.debug)
    else:
        serve(socket_io.wsgi_app, host=host, port=port)
