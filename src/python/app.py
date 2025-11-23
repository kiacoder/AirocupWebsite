"Backend application for the airocup website using Flask framework"

import os
import sys
import getpass
import traceback
import datetime
import logging
import bcrypt
import jdatetime  # type:ignore
from persiantools.digits import en_to_fa  # type:ignore
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
    SESSION_COOKIE_HTTPONLY=config.session_cookie_httponly,
    SESSION_COOKIE_SECURE=config.session_cookie_secure,
    SESSION_COOKIE_SAMESITE=config.session_cookie_samesite,
    UPLOAD_FOLDER_RECEIPTS=constants.Path.receipts_dir,
    UPLOAD_FOLDER_DOCUMENTS=os.path.join(constants.Path.uploads_dir, "documents"),
    UPLOAD_FOLDER_NEWS=constants.Path.news_dir,
    MAX_CONTENT_LENGTH=constants.AppConfig.max_document_size,
    ALLOWED_EXTENSIONS=list(constants.AppConfig.allowed_extensions),
)

database.create_database()
database.ensure_schema_upgrades()
with database.get_db_session() as _db_bootstrap_session:
    database.populate_geography_data(_db_bootstrap_session)
    database.populate_leagues(_db_bootstrap_session)

flask_app.register_blueprint(admin.admin_blueprint)
flask_app.register_blueprint(client.client_blueprint)
flask_app.register_blueprint(globals_file.global_blueprint)

for path in [
    flask_app.config["UPLOAD_FOLDER_RECEIPTS"],
    flask_app.config["UPLOAD_FOLDER_DOCUMENTS"],
    flask_app.config["UPLOAD_FOLDER_NEWS"],
    constants.Path.guideline_dir,
    os.path.dirname(constants.Path.database_dir),
]:
    os.makedirs(path, exist_ok=True)


def _compute_static_version_token() -> str:
    """Return a cache-busting token derived from core static asset mtimes."""

    tracked_assets = [
        constants.Path.css_style,
        constants.Path.js_main,
        "js/socket.io.min.js",
        "js/chart.umd.min.js",
    ]

    mtimes = []
    for rel_path in tracked_assets:
        absolute_path = os.path.join(constants.Path.static_dir, rel_path)
        try:
            mtimes.append(int(os.path.getmtime(absolute_path)))
        except OSError:
            continue

    if mtimes:
        return str(max(mtimes))

    return str(int(datetime.datetime.now().timestamp()))


STATIC_VERSION_TOKEN = _compute_static_version_token()


@flask_app.template_filter("formatdate")
def format_date_filter(date_object):
    """Formats a datetime/date object to a Jalali date string (YYYY-MM-DD)."""
    if isinstance(date_object, datetime.datetime):
        jalali_value = jdatetime.datetime.fromgregorian(datetime=date_object)
    elif isinstance(date_object, datetime.date):
        jalali_value = jdatetime.date.fromgregorian(date=date_object)
    else:
        return ""

    return jalali_value.strftime("%Y-%m-%d")


@flask_app.template_filter("humanize_number")
def humanize_number_filter(num):
    """Formats a number with commas for thousands separators."""
    try:
        return f"{int(num):,}"
    except (ValueError, TypeError):
        return num


@flask_app.context_processor
def inject_global_variables():
    """Injects global variables into the template context"""
    airocup_data = {
        "allowed_years": constants.Date.get_allowed_years(),
        "persian_months": constants.Date.persian_months,
        "forbidden_words": list(constants.ForbiddenContent.custom_words),
        "client_id": session.get("client_id") if has_request_context() else None,
        "provinces_data": constants.provinces_data,
    }

    return {
        "path": constants.Path,
        "app_config": {
            "max_team_per_client": constants.AppConfig.max_team_per_client,
            "max_members_per_team": constants.AppConfig.max_members_per_team,
            "new_member_fee_per_league": config.payment_config.get(
                "new_member_fee_per_league"
            ),
        },
        "contact": constants.Contact,
        "leagues_list": constants.leagues_list,
        "education_levels": constants.education_levels,
        "event_details": constants.Details,
        "html_names": constants.global_html_names_data,
        "location": constants.Details.address,
        "contact_points": constants.contact_points_data,
        "cooperation_opportunities": constants.cooperation_opportunities_data,
        "jdatetime": jdatetime,
        "airocup_data": airocup_data,
        "payment": config.payment_config,
        "committee_members": constants.committee_members_data,
        "technical_committee_members": constants.technical_committee_members,
        "homepage_sponsors": constants.homepage_sponsors_data,
        "app_version": config.app_version,
        "static_version": STATIC_VERSION_TOKEN,
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
                constants.global_html_names_data["500_debug"],
                error=traceback.format_exc(),
            ),
            500,
        )
    return render_template(constants.global_html_names_data["500"]), 500


@socket_io.on("join")
def on_join_message(data_dictionary):
    """Handles a user joining a chat room."""
    room_name = data_dictionary.get("room")
    client_id = session.get("client_id") or session.get("client_id_for_resolution")

    if session.get("admin_logged_in", False):
        join_room(room_name)
        flask_app.logger.info("admin joined room %s", room_name)
    elif client_id and str(client_id) == str(room_name):
        join_room(str(client_id))
        flask_app.logger.info("client %s joined their room", client_id)
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

        if session.get("admin_logged_in", False):
            sender_type = "admin"
        else:
            client_id = session.get("client_id") or session.get(
                "client_id_for_resolution"
            )
            if client_id and str(client_id) == str(target_room):
                sender_type = "client"
            else:
                flask_app.logger.warning(
                    "Unauthorized chat message attempt by session %s in room %s",
                    client_id,
                    target_room,
                )
                return

        sanitized_message = bleach.clean(message)
        if len(sanitized_message) > 1000:
            sanitized_message = sanitized_message[:1000]

        with database.get_db_session() as db:
            saved_message = database.save_chat_message(
                db, int(target_room), sanitized_message, sender_type
            )

        current_time = saved_message.timestamp
        emit(
            "new_message",
            {
                "message": sanitized_message,
                "timestamp": current_time.isoformat(),
                "message_id": getattr(saved_message, "message_id", None),
                "sender": sender_type,
            },
            to=str(target_room),
            include_self=False,
        )

    except (ValueError, TypeError, exc.SQLAlchemyError) as error:
        flask_app.logger.error("Chat message error: %s", error)


@flask_app.route("/uploads/receipts/<int:client_id>/<filename>")
@admin_required
def uploaded_receipt_file(client_id, filename):
    "Serves uploaded receipt files to admin users with client scoping"
    client_receipts_dir = os.path.join(constants.Path.receipts_dir, str(client_id))
    return send_from_directory(client_receipts_dir, filename)


@flask_app.template_filter("to_iso_format")
def to_iso_format_filter(date_object):
    "Converts a datetime object to ISO 8601 format"
    if not isinstance(date_object, datetime.datetime):
        return ""
    return date_object.isoformat()


def get_distribution_query(db, entity, join_chain, label="count", limit=10):
    """Generic helper to build distribution queries for city/province/etc"""

    query = db.query(
        entity.name.label("name"),
        func.count(models.Member.member_id).label(label),
    ).select_from(entity)

    for join_target, on_clause in join_chain:
        query = query.join(join_target, on_clause)

    query = (
        query.filter(models.Member.status == models.EntityStatus.ACTIVE)
        .group_by(entity.name)
        .order_by(func.count(models.Member.member_id).desc())
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
            [
                (models.Member, models.Member.city_id == models.City.city_id),
            ],
        )

    return jsonify(
        {
            "labels": [row.name for row in city_data],
            "data": [row.count for row in city_data],
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
                (models.City, models.City.province_id == models.Province.province_id),
                (models.Member, models.Member.city_id == models.City.city_id),
            ],
        )

    return jsonify(
        {
            "labels": [row.name for row in province_data],
            "data": [row.count for row in province_data],
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
    logger.info("🚀 airocup backend Server is launching...")
    logger.info("   - Version: %s", config.app_version)
    logger.info("   - Mode: %s", mode)
    logger.info("   - Database: Verified and connected successfully.")
    logger.info("   - Listening on: http://%s:%s", host, port)
    logger.info(border)


@flask_app.cli.command("init-db")
def initialize_database_command() -> None:
    """Creates the database tables and populates geography/league data."""
    database.create_database()

    with database.get_db_session() as db:
        database.populate_geography_data(db)
        database.populate_leagues(db)

    logger.info("Database initialized successfully.")


wsgi_app = flask_app


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "generate_hash":
        try:
            admin_password = getpass.getpass("رمز عبور ادمین مورد نظر را وارد کنید: ")
            if admin_password:
                logger.info("✅ هش ادمین شما با موفقیت ایجاد شد.")
                logger.info("خط زیر را کپی کرده و در فایل .env خود جای‌گذاری کنید:")
                logger.info("-" * 50)
                logger.info(
                    "admin_password_hash='%s'",
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

    if config.debug:
        socket_io.run(flask_app, host=host, port=port, debug=config.debug)
    else:
        serve(flask_app, host=host, port=port)
