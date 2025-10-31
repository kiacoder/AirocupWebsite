import getpass as GetPass
import os as OS
import sys as Sys
from functools import wraps as Wraps
import bcrypt as BCrypt
import jdatetime as JDateTime
from flask_socketio import SocketIO, emit as Emit, join_room as JoinRoom
from flask_wtf.csrf import CSRFProtect
from persiantools.digits import en_to_fa as EnToFa
import traceback as TraceBack
from sqlalchemy.orm import Session
from sqlalchemy import func
import Config
import Database
import bleach as Bleach
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address as GetRemoteAddress
import datetime as Datetime
from flask import (
    Flask,
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
import Constants
import Models
import Admin
import Client
import Global

FlaskApp = Flask(
    __name__,
    static_folder=Constants.Path.StaticDir,
    template_folder=Constants.Path.TemplatesDir,
    static_url_path="",
)

FlaskApp.secret_key = Config.SecretKey
CSRF_Protector = CSRFProtect(FlaskApp)
SocketIOInstance = SocketIO(FlaskApp)
limiter = Limiter(
    app=FlaskApp,
    key_func=GetRemoteAddress,
    default_limits=["200 per day", "50 per hour"],
)

FlaskApp.config["PERMANENT_SESSION_LIFETIME"] = Config.PermanentSessionLifeTime
FlaskApp.config["SESSION_COOKIE_HTTPONLY"] = True
FlaskApp.config["SESSION_COOKIE_SECURE"] = True
FlaskApp.config["UPLOAD_FOLDER_RECEIPTS"] = Constants.Path.ReceiptsDir
FlaskApp.config["MAX_CONTENT_LENGTH"] = Constants.AppConfig.MaxVideoSize
FlaskApp.config["ALLOWED_EXTENSIONS"] = list(Constants.AppConfig.AllowedExtensions)
FlaskApp.config["UPLOAD_FOLDER_DOCUMENTS"] = OS.path.join(
    Constants.Path.UploadsDir, "Documents"
)
FlaskApp.config["UPLOAD_FOLDER_NEWS"] = Constants.Path.NewsDir

OS.makedirs(FlaskApp.config["UPLOAD_FOLDER_RECEIPTS"], exist_ok=True)
OS.makedirs(FlaskApp.config["UPLOAD_FOLDER_NEWS"], exist_ok=True)
OS.makedirs(FlaskApp.config["UPLOAD_FOLDER_DOCUMENTS"], exist_ok=True)
OS.makedirs(OS.path.dirname(Constants.Path.DatabaseDir), exist_ok=True)


@FlaskApp.template_filter("persian_digits")
def PersianDigitsFilter(Content):
    return EnToFa(str(Content))


@FlaskApp.template_filter("basename")
def BasenameFilter(PathString):
    return OS.path.basename(PathString)


@FlaskApp.errorhandler(400)
def HandleBadRequest(Error):
    FlaskApp.logger.warning(
        f"Bad Request (400) at {Request.url} from {Request.remote_addr}: {Error}"
    )
    return RenderTemplate(Constants.GlobalHTMLNamesData["400"], error=str(Error)), 400


@FlaskApp.errorhandler(403)
def HandleForbidden(Error):
    FlaskApp.logger.warning(
        f"Forbidden (403) access attempt at {Request.url} by {Request.remote_addr}: {Error}"
    )
    return RenderTemplate(Constants.GlobalHTMLNamesData["403"]), 403


@FlaskApp.errorhandler(500)
def HandleServerError(Error):
    FlaskApp.logger.error(
        f"Internal Server Error (500) on {Request.method} {Request.url} from {Request.remote_addr}:\n{TraceBack.format_exc()}"
    )
    if FlaskApp.debug:
        return (
            RenderTemplate(
                Constants.GlobalHTMLNamesData["500 Debug"], error=TraceBack.format_exc()
            ),
            500,
        )
    return RenderTemplate(Constants.GlobalHTMLNamesData["500"]), 500


def AdminRequired(DecoratedRoute):
    @Wraps(DecoratedRoute)
    def DecoratedFunction(*args, **kwargs):
        if not Session.get("AdminLoggedIn"):
            return ReDirect(URLFor("AdminLogin"))
        return DecoratedRoute(*args, **kwargs)

    return DecoratedFunction


def AdminActionRequired(DecoratedRoute):
    @Wraps(DecoratedRoute)
    def DecoratedFunction(*args, **kwargs):
        if not Session.get("AdminLoggedIn"):
            return ReDirect(URLFor("AdminLogin"))
        try:
            CSRF_Protector.protect()
        except Exception:
            Abort(400, "توکن امنیتی نامعتبر است (CSRF).")
        return DecoratedRoute(*args, **kwargs)

    return DecoratedFunction


def ResolutionRequired(f):
    @Wraps(f)
    def decorated_function(*args, **kwargs):
        if "ClientIDForResolution" not in session:
            Flash("شما در وضعیت اصلاح اطلاعات قرار ندارید.", "Info")
            return ReDirect(URLFor("Login"))
        return f(*args, **kwargs)

    return decorated_function


@FlaskApp.template_filter("formatdate")
def FormatDateFilter(DateObject):
    if not isinstance(DateObject, Datetime.datetime):
        return ""
    return JDateTime.datetime.fromgregorian(datetime=DateObject).strftime("%Y-%m-%d")


@FlaskApp.template_filter("humanize_number")
def HumanizeNumberFilter(Num):
    try:
        return f"{int(Num):,}"
    except (ValueError, TypeError):
        return Num


@FlaskApp.context_processor
def InjectGlobalVariables():
    AirocupData = {
        "DaysInMonth": Constants.Date.DaysInMonth,
        "AllowedYears": Constants.Date.GetAllowedYears(),
        "PersianMonths": Constants.Date.PersianMonths,
        "ForbiddenWords": list(Constants.ForbiddenContent.WORDS),
        "ClientID": session.get("ClientID"),
        "Provinces": Constants.ProvincesData,
    }

    return {
        "Path": Constants.Path,
        "AppConfig": {
            "MaxTeamPerClient": Constants.AppConfig.MaxTeamPerClient,
            "MaxMembersPerTeam": Constants.AppConfig.MaxMembersPerTeam,
        },
        "Contact": Constants.Contact,
        "Event": Constants.Event,
        "HTMLNames": Constants.GlobalHTMLNamesData,
        "Location": Constants.Location,
        "ContactPoints": Constants.ContactPointsData,
        "CooperationOpportunities": Constants.CooperationOpportunitiesData,
        "JDateTime": JDateTime,
        "AirocupData": AirocupData,
        "Payment": Constants.PaymentConfig,
        "LeaguesList": Constants.LeaguesListData,
        "CommitteeMembers": Constants.CommitteeMembersData,
        "TechnicalCommitteeMembers": Constants.TechnicalCommitteeMembersData,
        "HomepageSponsors": Constants.HomepageSponsorsData,
    }


def LoginRequired(DecoratedRoute):
    @Wraps(DecoratedRoute)
    def DecoratedFunction(*args, **kwargs):
        if "ClientID" not in session:
            Flash("برای مشاهده این صفحه باید وارد شوید.", "Warning")
            return ReDirect(URLFor("Login", next=Request.url))
        if "ClientIDForResolution" in session:
            Flash(
                "ابتدا باید اطلاعات حساب کاربری خود را تکمیل و اصلاح نمایید.", "Warning"
            )
            return ReDirect(URLFor("ResolveDataIssues"))
        return DecoratedRoute(*args, **kwargs)

    return DecoratedFunction


@FlaskApp.route("/API/Admin/ProvinceDistribution")
@AdminRequired
def ApiProvinceDistribution():
    with Database.get_db_session() as db:
        Data = (
            db.query(
                Models.Province.Name.label("Name"),
                func.count(Models.Member.MemberID).label("Count"),
            )
            .join(Models.City, Models.Member.CityID == Models.City.CityID)
            .join(Models.Province, Models.City.ProvinceID == Models.Province.ProvinceID)
            .filter(Models.Member.Status == Models.EntityStatus.Active)
            .group_by(Models.Province.Name)
            .order_by(func.count(Models.Member.MemberID).desc())
            .limit(10)
            .all()
        )

    return Jsonify(
        {
            "Labels": [row.Name for row in Data],
            "Data": [row.Count for row in Data],
        }
    )


@SocketIOInstance.on("join")
def OnJoinMessage(DataDictionary):
    RoomName = DataDictionary.get("Room")
    ClientID = session.get("ClientID")

    if session.get("AdminLoggedIn", False):
        JoinRoom(RoomName)
    elif ClientID and str(ClientID) == str(RoomName):
        JoinRoom(str(ClientID))
    else:
        FlaskApp.logger.warning(
            f"Unauthorized chat room join attempt by session {ClientID} for room {RoomName}"
        )
        return


@SocketIOInstance.on("send_message")
def HandleSendMessage(JsonData):
    try:
        if not isinstance(JsonData, dict):
            return

        Message = str(JsonData.get("message") or "").strip()
        Room = JsonData.get("room")

        if not Message or not Room:
            return

        if session.get("AdminLoggedIn", False):
            SenderType = "Admin"
        elif session.get("ClientID") and str(session.get("ClientID")) == str(Room):
            SenderType = "Client"
        else:
            FlaskApp.logger.warning(
                f"Unauthorized chat message attempt by session {session.get("ClientID")} in room {Room}"
            )
            return

        SanitizedMessage = Bleach.clean(Message)
        if len(SanitizedMessage) > 1000:
            SanitizedMessage = SanitizedMessage[:1000]

        with Database.get_db_session() as DbSession:
            Database.SaveChatMessage(DbSession, int(Room), SanitizedMessage, SenderType)

        CurrentTime = Datetime.datetime.now(Datetime.timezone.utc)
        Emit(
            "new_message",
            {
                "message": SanitizedMessage,
                "timestamp": CurrentTime.isoformat(),
                "sender": SenderType,
            },
            room=str(Room),
        )

    except Exception as Error:
        FlaskApp.logger.error(f"Chat message error: {Error}")


@FlaskApp.route("/uploads/receipts/<filename>")
@AdminRequired
def UploadedReceiptFile(filename):
    return SendFromDirectory(Constants.Path.ReceiptsDir, filename)


@FlaskApp.template_filter("to_iso_format")
def ToISOFormatFilter(DateObject):
    if not isinstance(DateObject, Datetime.datetime):
        return ""
    return DateObject.isoformat()


@FlaskApp.route("/API/AdminCityDistribution")
@AdminRequired
def ApiCityDistribution():
    with Database.get_db_session() as db:
        CityData = (
            db.query(
                Models.City.Name,
                func.count(Models.Member.MemberID).label("Count"),
            )
            .join(Models.City, Models.Member.CityID == Models.City.CityID)
            .filter(
                Models.Member.Status == Models.EntityStatus.Active,
            )
            .group_by(Models.City.Name)
            .order_by(func.count(Models.Member.MemberID).desc())
            .limit(10)
            .all()
        )

    ChartData = {
        "Labels": [row.Name for row in CityData],  # name is white
        "Data": [row.Count for row in CityData],  # Count is white
    }
    return Jsonify(ChartData)


def PrintStartupMessage(Host, Port):
    print("=" * 60)
    print(f"🚀 Airocup Backend Server is launching...")
    print(f"   - Version: {Config.Version}")
    print(f"   - Mode: {'✅ Debug' if Config.Debug else '⛔ Production'}")
    print(f"   - Database: Verified and connected successfully.")
    print(f"   - Listening on: http://{Host}:{Port}")
    print("=" * 60)


@FlaskApp.cli.command("init-db")
def InitializeDatabaseCommand():
    """Creates the database tables and populates geography data."""
    Database.CreateDatabase()
    Database.PopulateGeographyData()
    print("Database initialized successfully.")


FlaskApp.register_blueprint(Admin.AdminBlueprint)
FlaskApp.register_blueprint(Client.ClientBlueprint)
FlaskApp.register_blueprint(Global.GlobalBlueprint)

if __name__ == "__main__":
    if len(Sys.argv) > 1 and Sys.argv[1] == "generate_hash":
        try:
            AdminPassword = GetPass.getpass("رمز عبور ادمین مورد نظر را وارد کنید: ")
            if len(AdminPassword) > 0:
                print("\n✅ هش ادمین شما با موفقیت ایجاد شد.")
                print("خط زیر را کپی کرده و در فایل Config.py خود جای‌گذاری کنید:")
                print("-" * 50)
                print(
                    f"AdminPasswordHash = '{BCrypt.hashpw(AdminPassword.encode("utf-8"), BCrypt.gensalt()).decode('utf-8')}'"
                )
                print("-" * 50)
            else:
                print("رمز عبور نمی‌تواند خالی باشد.")
        except Exception as Error:
            print(f"خطایی رخ داد: {Error}")

        Sys.exit()
    else:
        if OS.environ.get("WERKZEUG_RUN_MAIN") != "true":
            PrintStartupMessage(Host="0.0.0.0", Port=5000)

        SocketIOInstance.run(FlaskApp, host="0.0.0.0", port=5000, debug=Config.Debug)
