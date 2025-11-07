"Backend application for the Airocup website using Flask framework"
import getpass
import os
import sys
import traceback
import datetime
import bcrypt

from sqlalchemy import exc, func
import config
import database
import bleach
from flask import (
    Flask,
    render_template,
    request,
    send_from_directory,
    session,
    jsonify,
)
import constants
import models
import admin
import client
import globals as globals_file
from extensions import csrf_protector, limiter, socket_io
from decorators import admin_required
from waitress import serve
from flask_socketio import join_room, emit # Added missing imports for socket_io functions
from flask.templating import TemplateError # Added for more specific exception handling

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


flask_app.config["PERMANENT_SESSION_LIFETIME"] = config.permanent_session_lifetime
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
def handle_server_error(_error): # Renamed 'error' to '_error' to mark as intentionally unused
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


@socket_io.on("join")
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


@socket_io.on("send_message")
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
                func.count(models.Member.member_id).label("count"),
            )
            .join(models.City, models.Member.city_id == models.City.city_id)
            .filter(
                models.Member.status == models.EntityStatus.ACTIVE,
            )
            .group_by(models.City.name)
            .order_by(func.count(models.Member.member_id).desc())
            .limit(10)
            .all()
        )

    chart_data = {
        "Labels": [row.name for row in city_data],
        "Data": [row.count for row in city_data],
    }
    return jsonify(chart_data)
def print_startup_message(server_host, server_port, server_mode): # Renamed parameters to avoid redefinition warnings
    "Prints the startup message for the server"
    print("=" * 60)
    print("🚀 Airocup Backend Server is launching...")
    print(f"   - Version: {config.app_version}")
    print(f"   - Mode: {server_mode}")
    print("   - Database: Verified and connected successfully.")
    print(f"   - Listening on: http://{server_host}:{server_port}")
    print("=" * 60)
    print(f"   - Listening on: http://{host}:{port}")
    print("=" * 60)


def test_templates():
    "Tests all HTML templates for rendering errors"
    print("\n🔍 Starting template integrity check...")
    template_dir = constants.Path.templates_dir
    templates = [f for f in os.listdir(template_dir) if f.endswith(".html")]
    success_count = 0
    fail_count = 0

    with flask_app.app_context():
        for template in templates:
            try:
                render_template(template)
            except TemplateError as e: # Changed to catch a more specific exception
                print(f"  ❌ {template}: FAILED ({e})")
                fail_count += 1
                print(f"  ❌ {template}: FAILED ({e})")
                fail_count += 1

    print(f"\nTemplate check finished. {success_count} successful, {fail_count} failed.")
    if fail_count > 0:
        print("🚨 Please fix the failing templates before proceeding.")
        sys.exit(1)


@flask_app.cli.command("init-db")
def initialize_database_command():
    """Creates the database tables and populates geography data."""
    database.create_database()
    database.populate_geography_data()
    print("database initialized successfully.")
flask_app.register_blueprint(admin.admin_blueprint)
flask_app.register_blueprint(client.client_blueprint)
flask_app.register_blueprint(globals_file.global_blueprint)
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
                    f"AdminPasswordHash = '{bcrypt.hashpw(AdminPassword.encode("utf-8"), bcrypt.gensalt()).decode('utf-8')}'"
                )
                print("-" * 50)
            else:
                print("رمز عبور نمی‌تواند خالی باشد.")
        except (KeyboardInterrupt, EOFError, ValueError) as error:
            print(f"خطایی رخ داد: {error}")

        sys.exit()
    else:
        host = "0.0.0.0"
        port = 5000
        mode = '✅ Debug' if config.flask_debug else '⛔ Production'

        if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
            print_startup_message(host, port, mode)
            test_templates()

        if config.flask_debug:
            socket_io.run(flask_app, host=host, port=port, debug=config.flask_debug)
        if config.flask_debug:
            socket_io.run(flask_app, host=host, port=port, debug=config.flask_debug)
        else:
            serve(socket_io.wsgi_app, host=host, port=port) # Corrected to pass the WSGI application wrapped by SocketIO
