"Backend application for the Airocup website using Flask framework"
import getpass
import os
import sys
from functools import wraps
import traceback # type: ignore
import datetime # type: ignore
import bcrypt
import jdatetime # type: ignore
from flask_socketio import SocketIO, emit, join_room # type: ignore
from flask_wtf.csrf import CSRFProtect, CSRFError # type: ignore
from persiantools.digits import en_to_fa # type: ignore
from sqlalchemy import exc, func
import config
import database
import bleach
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import (
    Flask,
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
import constants
import models
import Code.Python.New.admin as admin
import client
import globals as globals_file

flask_app = Flask(
    __name__,
    static_folder=constants.Path.static_dir,
    template_folder=constants.Path.templates_dir,
    static_url_path="",
)

flask_app.secret_key = config.secret_key
CSRF_Protector = CSRFProtect(flask_app)
SocketIOInstance = SocketIO(flask_app)
limiter = Limiter(
    app=flask_app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
)

flask_app.config["PERMANENT_SESSION_LIFETIME"] = config.permanent_session_life_time
flask_app.config["SESSION_COOKIE_HTTPONLY"] = True
flask_app.config["SESSION_COOKIE_SECURE"] = True
flask_app.config["UPLOAD_FOLDER_RECEIPTS"] = constants.Path.receipts_dir
flask_app.config["MAX_CONTENT_LENGTH"] = constants.AppConfig.max_document_size
flask_app.config["ALLOWED_EXTENSIONS"] = list(constants.AppConfig.allowed_extensions)
flask_app.config["UPLOAD_FOLDER_DOCUMENTS"] = os.path.join(
    constants.Path.uploads_dir, "Documents"
)
flask_app.config["UPLOAD_FOLDER_NEWS"] = constants.Path.news_dir

os.makedirs(flask_app.config["UPLOAD_FOLDER_RECEIPTS"], exist_ok=True)
os.makedirs(flask_app.config["UPLOAD_FOLDER_NEWS"], exist_ok=True)
os.makedirs(flask_app.config["UPLOAD_FOLDER_DOCUMENTS"], exist_ok=True)
os.makedirs(os.path.dirname(constants.Path.database_dir), exist_ok=True)


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
    "Handles 400 Bad Request errors"
    flask_app.logger.warning(
        "Bad request (400) at %s from %s: %s", request.url, request.remote_addr, error
    )
    return render_template(constants.global_html_names_data["400"], error=str(error)), 400


@flask_app.errorhandler(403)
def handle_forbidden(error):
    "Handles 403 Forbidden errors"
    flask_app.logger.warning(
        "Forbidden (403) access attempt at %s by %s: %s",
        request.url,
        request.remote_addr,
        error,
    )
    return render_template(constants.global_html_names_data["403"]), 403


@flask_app.errorhandler(500)
def handle_server_error(_error): # needs fix for error, do we need it?
    "Handles 500 Internal Server errors"
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
                constants.global_html_names_data["500 Debug"], error=traceback.format_exc()
            ),
            500,
        )
    return render_template(constants.global_html_names_data["500"]), 500


def admin_required(decorated_route):
    "@wraps decorator to ensure admin access is required for a route"
    @wraps(decorated_route)
    def decorated_function(*args, **kwargs):
        "Checks if admin is logged in; redirects to admin login if not"
        if not session.get("AdminLoggedIn"):
            return redirect(url_for("AdminLogin"))
        return decorated_route(*args, **kwargs)

    return decorated_function


def admin_action_required(decorated_route):
    "@wraps decorator to ensure admin action is required for a route"
    @wraps(decorated_route)
    def decorated_function(*args, **kwargs):
        "Checks if admin is logged in and protects against CSRF"
        if not session.get("AdminLoggedIn"):
            return redirect(url_for("AdminLogin"))
        try:
            CSRF_Protector.protect()
        except CSRFError:
            abort(400, "توکن امنیتی نامعتبر است (CSRF).")
        return decorated_route(*args, **kwargs)

    return decorated_function


def resolution_required(f):
    "Decorator to ensure user is in data resolution state"
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "client_idForResolution" not in session:
            flash("شما در وضعیت اصلاح اطلاعات قرار ندارید.", "Info")
            return redirect(url_for("Login"))
        return f(*args, **kwargs)

    return decorated_function


@flask_app.template_filter("formatdate")
def format_date_filter(date_object):
    "Formats a datetime object to a Persian date string (YYYY-MM-DD)"
    if not isinstance(date_object, datetime.datetime):
        return ""
    return jdatetime.datetime.fromgregorian(datetime=date_object).strftime("%Y-%m-%d")


@flask_app.template_filter("humanize_number")
def humanize_number_filter(num):
    "Formats a number with commas for thousands separators"
    try:
        return f"{int(num):,}"
    except (ValueError, TypeError):
        return num


@flask_app.context_processor
def inject_global_variables():
    "Injects global variables into the template context"
    airocup_data = {
        "DaysInMonth": constants.Date.days_in_month,
        "AllowedYears": constants.Date.get_allowed_years(),
        "PersianMonths": constants.Date.persian_months,
        "ForbiddenWords": list(constants.ForbiddenContent.custom_words),
        "client_id": session.get("client_id"),
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


def login_required(decorated_route):
    "@wraps decorator to ensure user login is required for a route"
    @wraps(decorated_route)
    def decorated_function(*args, **kwargs):
        "Checks if user is logged in; redirects to login if not"
        if "client_id" not in session:
            flash("برای مشاهده این صفحه باید وارد شوید.", "Warning")
            return redirect(url_for("Login", next=request.url))
        if "client_idForResolution" in session:
            flash(
                "ابتدا باید اطلاعات حساب کاربری خود را تکمیل و اصلاح نمایید.", "Warning"
            )
            return redirect(url_for("ResolveDataIssues"))
        return decorated_route(*args, **kwargs)

    return decorated_function


@flask_app.route("/API/admin/ProvinceDistribution")
@admin_required
def api_province_distribution():
    "Returns JSON data for province distribution of active members"
    with database.get_db_session() as db:
        data = (
            db.query(
                models.Province.name.label("name"),
                func.count(models.Member.member_id).label("Count"),
            )
            .join(models.City, models.Member.city_id == models.City.city_id)
            .join(models.Province, models.City.province_id == models.Province.province_id)
            .filter(models.Member.status == models.EntityStatus.ACTIVE)
            .group_by(models.Province.name)
            .order_by(func.count(models.Member.member_id).desc())
            .limit(10)
            .all()
        )

    return jsonify(
        {
            "Labels": [row.name for row in data],
            "Data": [row.count for row in data],
        }
    )


@SocketIOInstance.on("join")
def on_join_message(data_dictionary):
    "Handles a user joining a chat room"
    room_name = data_dictionary.get("Room")
    client_id = session.get("client_id")

    if session.get("AdminLoggedIn", False):
        join_room(room_name)
    elif client_id and str(client_id) == str(room_name):
        join_room(str(client_id))
    else:
        flask_app.logger.warning(
            "Unauthorized chat room join attempt by session %s for room %s",
            client_id,
            room_name,
        )
        return


@SocketIOInstance.on("send_message")
def handle_send_message(json_data):
    "Handles incoming chat messages and broadcasts them to the appropriate room"
    try:
        if not isinstance(json_data, dict):
            return

        message = str(json_data.get("message") or "").strip()
        target_room = json_data.get("room")

        if not message or not target_room:
            return

        if session.get("AdminLoggedIn", False):
            sender_type = "admin"
        elif session.get("client_id") and str(session.get("client_id")) == str(target_room):
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
            database.save_chat_message(db, int(target_room), sanitized_message, sender_type)

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


@flask_app.route("/API/AdminCityDistribution")
@admin_required
def api_city_distribution():
    "Returns JSON data for city distribution of active members"
    with database.get_db_session() as db:
        city_data = (
            db.query(
                models.City.name,
                func.count(models.Member.member_id).label("Count"), # pylint: disable=no-member
            )
            .join(models.City, models.Member.city_id == models.City.city_id)
            .filter(
                models.Member.status == models.EntityStatus.ACTIVE,
            )
            .group_by(models.City.name)
            .order_by(func.count(models.Member.member_id).desc()) # pylint: disable=no-member
            .limit(10)
            .all()
        )

    chart_data = {
        "Labels": [row.name for row in city_data],  # name is white
        "Data": [row.count for row in city_data],  # Count is is yellow and corrected 
    }
    return jsonify(chart_data)


def print_startup_message(host, port):
    "Prints the startup message for the server"
    print("=" * 60)
    print("🚀 Airocup Backend Server is launching...")
    print(f"   - Version: {config.version}")
    print(f"   - Mode: {'✅ Debug' if config.debug else '⛔ Production'}")
    print("   - database: Verified and connected successfully.")
    print(f"   - Listening on: http://{host}:{port}")
    print("=" * 60)


@flask_app.cli.command("init-db")
def initialize_database_command():
    """Creates the database tables and populates geography data."""
    database.create_database()
    database.populate_geography_data()
    print("database initialized successfully.")


flask_app.register_blueprint(admin.admin_blueprint)
flask_app.register_blueprint(client.client_blueprint)
flask_app.register_blueprint(globals_file.global_blueprint)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "generate_hash":
        try:
            AdminPassword = getpass.getpass("رمز عبور ادمین مورد نظر را وارد کنید: ")
            if len(AdminPassword) > 0:
                print("\n✅ هش ادمین شما با موفقیت ایجاد شد.")
                print("خط زیر را کپی کرده و در فایل config.py خود جای‌گذاری کنید:")
                print("-" * 50)
                print(
                    f"AdminPasswordHash = '{
                        bcrypt.hashpw(
                            AdminPassword.encode("utf-8"), bcrypt.gensalt()
                        ).decode('utf-8')
                    }'"
                )
                print("-" * 50)
            else:
                print("رمز عبور نمی‌تواند خالی باشد.")
        except (KeyboardInterrupt, EOFError, ValueError) as error:
            print(f"خطایی رخ داد: {error}")

        sys.exit()
    else:
        if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            print_startup_message(host="0.0.0.0", port=5000)

        SocketIOInstance.run(flask_app, host="0.0.0.0", port=5000, debug=config.debug)
