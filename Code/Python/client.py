"Client-side routes and logic for the web application"

import os
import random
import string
import uuid
import datetime
import secrets
from threading import Thread
import bcrypt
import jdatetime
from persiantools.digits import fa_to_en
from sqlalchemy import exc, func, select
from sqlalchemy.orm import subqueryload
import bleach
from werkzeug.utils import secure_filename
from werkzeug.security import safe_join
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

from . import config
from . import database
from . import constants
from . import models
from . import utils
from . import auth
from .extensions import csrf_protector, limiter
from .auth import login_required, resolution_required

client_blueprint = Blueprint("client", __name__)

@client_blueprint.route("/signup", methods=["GET", "POST"])
def signup():
    "Render and handle the client sign-up page"
    if request.method == "POST":
        csrf_protector.protect()

        phone = fa_to_en(request.form.get("phone_number", "").strip())
        email = fa_to_en(request.form.get("Email", "").strip().lower())
        password = request.form.get("Password", "")
        education_level = request.form.get("EducationLevel", "").strip()

        form_values = {
            "phone_number": phone,
            "Email": email,
            "EducationLevel": education_level,
        }

        response = None

        if education_level not in constants.allowed_education:
            flash("مقطع تحصیلی انتخاب‌شده نامعتبر است.", "error")
            response = render_template(
                constants.client_html_names_data["SignUp"], **form_values
            )
        elif password != request.form.get("ConfirmPassword", ""):
            flash("رمز عبور و تکرار آن یکسان نیستند.", "error")
            response = render_template(
                constants.client_html_names_data["SignUp"], **form_values
            )
        else:
            is_valid, error_message = utils.is_valid_password(password)
            if not is_valid:
                flash(error_message or "خطای نامشخص در رمز عبور.", "error")
                response = render_template(
                    constants.client_html_names_data["SignUp"], **form_values
                )
            elif not utils.is_valid_iranian_phone(phone) or not utils.is_valid_email(
                email
            ):
                flash("ایمیل یا شماره موبایل نامعتبر است.", "error")
                response = render_template(
                    constants.client_html_names_data["SignUp"], **form_values
                )

        if response is None:
            with database.get_db_session() as db:
                try:
                    hashed_password = bcrypt.hashpw(
                        password.encode("utf-8"), bcrypt.gensalt()
                    )
                    verification_code = "".join(random.choices(string.digits, k=6))
                    new_client = models.Client(
                        phone_number=phone,
                        Email=email,
                        Password=hashed_password.decode("utf-8"),
                        RegistrationDate=datetime.datetime.now(datetime.timezone.utc),
                        EducationLevel=education_level,
                        phone_verification_code=verification_code,
                        verification_code_timestamp=datetime.datetime.now(
                            datetime.timezone.utc
                        ),
                    )
                    db.add(new_client)
                    db.commit()

                    Thread(
                        target=utils.send_templated_sms_async,
                        args=(
                            current_app._get_current_object(),
                            new_client.client_id,
                            config.melli_payamak["template_id_verification"],
                            verification_code,
                            config.melli_payamak,
                        ),
                    ).start()

                    response = redirect(
                        url_for(
                            "client.verify_code",
                            action="phone_signup",
                            client_id=new_client.client_id,
                        )
                    )

                except exc.IntegrityError:
                    db.rollback()
                    flash(
                        "کاربری با این ایمیل یا شماره تلفن قبلا ثبت نام کرده است.",
                        "error",
                    )
                    response = render_template(
                        constants.client_html_names_data["SignUp"], **form_values
                    )
                except exc.SQLAlchemyError as error:
                    db.rollback()
                    current_app.logger.error("SignUp database error: %s", error)
                    flash(
                        "خطایی در پایگاه داده رخ داد. لطفا دوباره تلاش کنید.", "error"
                    )
                    response = render_template(
                        constants.client_html_names_data["SignUp"], **form_values
                    )
                except RuntimeError as error:
                    current_app.logger.exception("SignUp unexpected error: %s", error)
                    flash(
                        "خطایی در هنگام ثبت نام رخ داد. لطفا دوباره تلاش کنید.", "error"
                    )
                    response = render_template(
                        constants.client_html_names_data["SignUp"], **form_values
                    )

        return response

    return render_template(constants.client_html_names_data["SignUp"])


@client_blueprint.route("/ResolveIssues", methods=["GET"])
@auth.resolution_required
def resolve_data_issues():
    """Render the data resolution form for clients with incomplete/invalid data."""
    with database.get_db_session() as db:
        client = (
            db.query(models.Client)
            .options(
                subqueryload(models.Client.teams).subqueryload(models.Team.members)
            )
            .filter(models.Client.client_id == session.get("ClientIDForResolution"))
            .first()
        )

        if not client:
            session.clear()
            flash("خطا: اطلاعات کاربری برای اصلاح یافت نشد.", "error")
            return redirect(url_for("client.login_client"))

    return render_template(
        constants.client_html_names_data["Null"],
        client=client,
        Problems=session.get("ResolutionProblems", {}),
        **utils.get_form_context(),
    )


@client_blueprint.route("/SubmitResolution", methods=["POST"])
@auth.resolution_required
def submit_data_resolution():
    """Handle submission of data resolution form."""
    csrf_protector.protect()
    with database.get_db_session() as db:
        try:
            role_map = {Role.value: Role for Role in models.MemberRole}
            updated_member_ids = {
                int(k.split("_")[-1])
                for k in request.form
                if k.startswith("member_name_")
            }

            for member_id in updated_member_ids:
                member = (
                    db.query(models.Member)
                    .join(models.Team)
                    .filter(
                        models.Member.member_id == member_id,
                        models.Team.client_id == session.get("ClientIDForResolution"),
                    )
                    .first()
                )

                if member:
                    member.name = bleach.clean(
                        request.form.get(f"member_name_{member_id}", "").strip()
                    )
                    member.national_id = fa_to_en(
                        request.form.get(f"member_nationalid_{member_id}", "").strip()
                    )
                    member.role = role_map.get(
                        request.form.get(f"member_Role_{member_id}", "").strip(),
                        models.MemberRole.MEMBER,
                    )

                    city_id = (
                        db.query(models.City.city_id)
                        .join(models.Province)
                        .filter(
                            models.Province.name
                            == request.form.get(
                                f"member_Province_{member_id}", ""
                            ).strip(),
                            models.City.name
                            == request.form.get(f"member_City_{member_id}", "").strip(),
                        )
                        .scalar()
                    )
                    member.city_id = city_id

                    if (
                        request.form.get(f"member_birthyear_{member_id}")
                        and request.form.get(f"member_birthmonth_{member_id}")
                        and request.form.get(f"member_birthday_{member_id}")
                    ):
                        try:
                            year = int(
                                request.form.get(f"member_birthyear_{member_id}", "")
                            )
                            month = int(
                                request.form.get(f"member_birthmonth_{member_id}", "")
                            )
                            day = int(
                                request.form.get(f"member_birthday_{member_id}", "")
                            )
                            jalali_date = jdatetime.date(year, month, day)
                            member.birth_date = jalali_date.togregorian()
                        except (ValueError, TypeError):
                            flash(
                                f"تاریخ تولد نامعتبر برای عضو '{member.name}' نادیده گرفته شد.",
                                "Warning",
                            )

            db.commit()

            client_id_for_resolution = session.get("ClientIDForResolution")
            if not isinstance(client_id_for_resolution, int):
                current_app.logger.error(
                    "ClientIDForResolution is missing or not an integer in session."
                )
                flash("خطا: شناسه کاربری برای اصلاح اطلاعات نامعتبر است.", "error")
                return redirect(url_for("client.login_client"))

            needs_archiving, new_problems = utils.check_for_data_completion_issues(
                db, client_id_for_resolution
            )

            if not needs_archiving:
                client = (
                    db.query(models.Client)
                    .filter(models.Client.client_id == client_id_for_resolution)
                    .first()
                )
                if client:
                    client.status = models.EntityStatus.ACTIVE
                    for team in client.teams:
                        if team.status != models.EntityStatus.ACTIVE:
                            team.status = models.EntityStatus.ACTIVE
                        for member in team.members:
                            if member.status != models.EntityStatus.ACTIVE:
                                member.status = models.EntityStatus.ACTIVE
                    db.commit()

                    session.clear()
                    session["client_id"] = client_id_for_resolution
                    session.permanent = True
                    flash(
                        "اطلاعات شما با موفقیت تکمیل و حساب کاربری شما مجددا فعال شد!",
                        "success",
                    )
                    return redirect(url_for("client.dashboard"))
                else:
                    current_app.logger.error(
                        "Client not found for ID %s during resolution.",
                        client_id_for_resolution,
                    )
                    flash("خطا: اطلاعات کاربری برای اصلاح یافت نشد.", "error")
                    return redirect(url_for("client.login_client"))
            session["ResolutionProblems"] = new_problems
            flash(
                "برخی از مشکلات همچنان باقی است. لطفا موارد مشخص شده را اصلاح نمایید.",
                "error",
            )
            return redirect(url_for("client.resolve_data_issues"))

        except (exc.SQLAlchemyError, ValueError, TypeError) as error:
            db.rollback()
            current_app.logger.error(
                "error during Data resolution for client_id %s: %s",
                session.get("ClientIDForResolution"),
                error,
            )
            flash(
                "خطایی در هنگام ذخیره اطلاعات رخ داد. لطفا دوباره تلاش کنید.", "error"
            )
            return redirect(url_for("client.resolve_data_issues"))


@client_blueprint.route("/Login", methods=["GET", "POST"])
@limiter.limit("15 per minute")
def login_client():
    "Render and handle the client login page"
    next_url = request.args.get("next")
    if request.method == "POST":
        csrf_protector.protect()
        ip_address = request.remote_addr or "unknown"
        identifier = fa_to_en(request.form.get("identifier", "").strip())
        password = request.form.get("Password", "").encode("utf-8")
        next_url_from_form = request.form.get("next")

        with database.get_db_session() as db:
            client_check = database.get_client_by(
                db, "Email", identifier
            ) or database.get_client_by(db, "phone_number", identifier)

            if not client_check or not bcrypt.checkpw(
                password, client_check.password.encode("utf-8")
            ):
                database.log_login_attempt(db, identifier, ip_address, is_success=False)
                flash("ایمیل/شماره تلفن یا رمز عبور نامعتبر است.", "error")
                return redirect(
                    url_for("client.login_client", next=next_url_from_form or "")
                )

            if client_check.status != models.EntityStatus.ACTIVE:
                flash(
                    "حساب کاربری شما غیر فعال شده است. لطفا با مدیریت تماس بگیرید.",
                    "error",
                )
                return redirect(url_for("client.login_client"))

            database.log_login_attempt(db, identifier, ip_address, is_success=True)

            if client_check.is_phone_verified is not True:
                new_code = "".join(random.choices(string.digits, k=6))
                client_check.phone_verification_code = new_code
                client_check.verification_code_timestamp = datetime.datetime.now(
                    datetime.timezone.utc
                )
                db.commit()
                Thread(
                    target=utils.send_templated_sms_async,
                    args=(
                        current_app._get_current_object(),
                        client_check.client_id,
                        config.melli_payamak["TemplateID_Verification"],
                        new_code,
                        config.melli_payamak,
                    ),
                ).start()
                flash(
                    "حساب شما هنوز فعال نشده است. یک کد تایید جدید به شماره موبایل شما ارسال شد.",
                    "Warning",
                )
                return redirect(
                    url_for(
                        "client.verify_code",
                        action="phone_signup",
                        client_id=client_check.client_id,
                    )
                )
            needs_resolution, problems = utils.check_for_data_completion_issues(
                db, client_check.client_id
            )
            if needs_resolution:
                session.clear()
                session["ResolutionProblems"] = problems
                flash(
                    "حساب کاربری شما دارای اطلاعات ناقص یا نامعتبر است. "
                    "لطفا برای ادامه، اطلاعات خواست‌ه‌شده را تکمیل و اصلاح نمایید.",
                    "error",
                )
                return redirect(url_for("client.resolve_data_issues"))

            session.clear()
            session["client_id"] = client_check.client_id
            session.permanent = True
            flash("شما با موفقیت وارد شدید.", "success")
            return redirect(next_url_from_form or url_for("client.dashboard"))

    return render_template(
        constants.client_html_names_data["Login"], next_url=next_url or ""
    )


@client_blueprint.route("/MyHistory")
@auth.login_required
def my_history():
    "Render the payment history page for the logged-in client"
    with database.get_db_session() as db:

        return render_template(
            constants.client_html_names_data["MyHistory"],
            Payments=[
                {
                    "PaymentID": p.payment_id,
                    "TeamName": TeamName,
                    "Amount": p.amount,
                    "UploadDate": p.upload_date,
                    "Status": p.status,
                    "ReceiptFilename": p.receipt_filename,
                    "client_id": p.client_id,
                }
                for p, TeamName in (
                    db.query(models.Payment, models.Team.team_name)
                    .join(models.Team, models.Payment.team_id == models.Team.team_id)
                    .filter(models.Payment.client_id == session["client_id"])
                    .order_by(models.Payment.upload_date.desc())
                    .all()
                )
            ],
        )


@client_blueprint.route("/Team/<int:team_id>/Update", methods=["GET", "POST"])
@auth.login_required
def update_team(team_id):
    "Render and handle updates to a specific team's information"
    with database.get_db_session() as db:
        team = (
            db.query(models.Team)
            .filter(
                models.Team.team_id == team_id,
                models.Team.client_id == session["client_id"],
                models.Team.status == models.EntityStatus.ACTIVE,
            )
            .first()
        )

        if not team:
            abort(404, "تیم مورد نظر پیدا نشد یا شما دسترسی به این تیم را ندارید")

        if request.method == "POST":
            csrf_protector.protect()
            new_team_name = bleach.clean(request.form.get("TeamName", "").strip())
            is_valid, error_message = utils.is_valid_team_name(new_team_name)
            if not is_valid:
                flash(error_message, "error")
            else:
                try:
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
                        flash(
                            "تیمی با این نام از قبل وجود دارد. لطفا نام دیگری انتخاب کنید.",
                            "error",
                        )
                    else:
                        team.team_name = new_team_name
                        db.commit()
                        database.log_action(
                            db,
                            session["client_id"],
                            f"User updated Team name for Team ID {team_id} to '{new_team_name}'.",
                        )
                        flash("نام تیم با موفقیت به‌روزرسانی شد!", "success")
                except exc.IntegrityError:
                    db.rollback()
                    flash(
                        "خطای پایگاه داده: تیمی با این نام از قبل وجود دارد.",
                        "error",
                    )

            return redirect(url_for("client.update_team", team_id=team_id))

        is_paid = database.check_if_team_is_paid(db, team_id)
        documents = []
        if is_paid:
            documents = (
                db.query(models.TeamDocument)
                .filter(models.TeamDocument.team_id == team_id)
                .order_by(models.TeamDocument.upload_date.desc())
                .all()
            )

    return render_template(
        constants.client_html_names_data["UpdateTeam"],
        Team=team,
        IsPaid=is_paid,
        Documents=documents,
    )


@client_blueprint.route("/Team/<int:team_id>/Delete", methods=["POST"])
@auth.login_required
def delete_team(team_id):
    "Archive a team and its members"
    csrf_protector.protect()
    with database.get_db_session() as db:
        try:
            team = (
                db.query(models.Team)
                .filter(
                    models.Team.team_id == team_id,
                    models.Team.client_id == session["client_id"],
                    models.Team.status == models.EntityStatus.ACTIVE,
                )
                .first()
            )

            if not team:
                flash("تیم مورد نظر یافت نشد یا شما اجازه حذف آن را ندارید.", "error")
                return redirect(url_for("client.dashboard"))

            if database.has_team_made_any_payment(db, team_id):
                flash(
                    "پس از ارسال رسید پرداخت، امکان آرشیو تیم توسط شما وجود ندارد.",
                    "error",
                )
                return redirect(url_for("client.dashboard"))

            team.status = models.EntityStatus.INACTIVE
            for member in team.members:
                member.status = models.EntityStatus.WITHDRAWN

            db.commit()
            flash(f"تیم «{team.team_name}» با موفقیت آرشیو شد.", "success")

        except exc.SQLAlchemyError as error:
            db.rollback()
            current_app.logger.error("error deleting Team %s: %s", team_id, error)
            flash("خطایی در هنگام آرشیو تیم رخ داد.", "error")

    return redirect(url_for("client.dashboard"))


@client_blueprint.route("/Team/<int:team_id>/members")
@auth.login_required
def manage_members(team_id):
    "Render the manage members page for a specific team"
    with database.get_db_session() as db:
        team = (
            db.query(models.Team)
            .filter(
                models.Team.team_id == team_id,
                models.Team.client_id == session["client_id"],
                models.Team.status == models.EntityStatus.ACTIVE,
            )
            .first()
        )

        if not team:
            abort(404, "تیم مورد نظر پیدا نشد یا شما دسترسی به این تیم را ندارید")

    return render_template(
        constants.client_html_names_data["members"],
        Team=team,
        members=(
            db.query(models.Member)
            .filter(
                models.Member.team_id == team_id,
                models.Member.status == models.EntityStatus.ACTIVE,
            )
            .all()
        ),
        IsPaid=database.check_if_team_is_paid(db, team_id),
        **utils.get_form_context(),
    )


@client_blueprint.route("/SupportChat")
@auth.login_required
def support_chat():
    "Render the support chat page for the logged-in client"
    client_user = utils.get_current_client()
    if not client_user:
        flash("خطا در بارگیری اطلاعات کاربری. لطفا دوباره وارد شوید.", "error")
        return redirect(url_for("client.login_client"))
    return render_template(
        constants.client_html_names_data["SupportChat"],
        User=client_user,
    )


@client_blueprint.route(
    "/Team/<int:team_id>/DeleteMember/<int:member_id>", methods=["POST"]
)
@auth.login_required
def delete_member(team_id, member_id):
    "Archive a member from a specific team."
    csrf_protector.protect()
    try:
        with database.get_db_session() as db:
            team = (
                db.query(models.Team)
                .filter(
                    models.Team.team_id == team_id,
                    models.Team.client_id == session["client_id"],
                    models.Team.status == models.EntityStatus.ACTIVE,
                )
                .first()
            )

            if not team:
                abort(404)

            if database.has_team_made_any_payment(db, team_id):
                flash("پس از ارسال رسید پرداخت، امکان حذف عضو وجود ندارد.", "error")
                return redirect(url_for("client.manage_members", team_id=team_id))

            member_to_delete = (
                db.query(models.Member)
                .filter(
                    models.Member.member_id == member_id,
                    models.Member.team_id == team_id,
                    models.Member.status == models.EntityStatus.ACTIVE,
                )
                .first()
            )

            if member_to_delete:
                member_name = member_to_delete.name
                member_to_delete.status = models.EntityStatus.WITHDRAWN

                database.log_action(
                    db,
                    session["client_id"],
                    f"User marked member '{member_name}' as withdrawn from Team ID {team_id}.",
                )

                db.commit()
                utils.update_team_stats(db, team_id)

                flash("عضو با موفقیت به عنوان منصرف شده علامت‌گذاری شد.", "success")
            else:
                flash("عضو مورد نظر یافت نشد.", "error")

    except exc.SQLAlchemyError as error:
        current_app.logger.error(
            "error archiving member %s from Team %s: %s", member_id, team_id, error
        )
        flash("خطایی در هنگام حذف عضو رخ داد.", "error")

    return redirect(url_for("client.manage_members", team_id=team_id))


@client_blueprint.route("/get_my_chat_history")
@auth.login_required
def get_my_chat_history():
    "Return the chat history for the logged-in client as JSON"
    client_id = session.get("client_id")
    if not isinstance(client_id, int):
        return jsonify({"messages": []})
    with database.get_db_session() as db:
        return jsonify(
            {
                "messages": [
                    {
                        "messageText": message.message_text,
                        "timestamp": message.timestamp.isoformat(),
                        "Sender": message.sender,
                    }
                    for message in database.get_chat_history_by_client_id(db, client_id)
                ]
            }
        )


@client_blueprint.route("/Team/<int:team_id>/UploadDocument", methods=["POST"])
@login_required
def upload_document(team_id):
    "Handle document upload for a specific team"
    csrf_protector.protect()

    with database.get_db_session() as db:
        team = (
            db.query(models.Team)
            .filter(
                models.Team.team_id == team_id,
                models.Team.status == models.EntityStatus.ACTIVE,
            )
            .first()
        )

        if not team:
            abort(404)

        if team.client_id != session.get("client_id") and not session.get(
            "AdminLoggedIn"
        ):
            abort(403)

        if not database.check_if_team_is_paid(db, team_id):
            flash("شما اجازه بارگذاری مستندات برای این تیم را ندارید.", "error")
            return redirect(url_for("client.update_team", team_id=team_id))

        if "File" not in request.files:
            flash("فایلی برای بارگذاری انتخاب نشده است.", "error")
            return redirect(url_for("client.update_team", team_id=team_id))
        temp = constants.AppConfig.max_document_size
        file = request.files["File"]
        if not file or not file.filename:
            flash("نام فایل نامعتبر است.", "error")
            return redirect(url_for("client.update_team", team_id=team_id))
        if request.content_length is None or request.content_length > temp:
            flash(
                f"حجم فایل سند نباید بیشتر از {temp / 1024 / 1024:.1f} مگابایت باشد.",
                "error",
            )
            return redirect(url_for("client.update_team", team_id=team_id))

        file.stream.seek(0)
        if not utils.is_file_allowed(file.stream):
            flash("نوع فایل مجاز نیست یا فایل خراب است.", "error")
            return redirect(url_for("client.update_team", team_id=team_id))
        file.stream.seek(0)

        original_filename = secure_filename(file.filename)
        extension = (
            original_filename.rsplit(".", 1)[1].lower()
            if "." in original_filename
            else ""
        )
        secure_name = f"{uuid.uuid4()}.{extension}"

        new_document = models.TeamDocument(
            team_id=team_id,
            client_id=session["client_id"],
            FileName=secure_name,
            FileType=extension,
            UploadDate=datetime.datetime.now(datetime.timezone.utc),
        )

        try:
            document_folder = os.path.join(
                current_app.config["UPLOAD_FOLDER_DOCUMENTS"], str(team_id)
            )
            os.makedirs(document_folder, exist_ok=True)
            file.save(os.path.join(document_folder, secure_name))
            db.add(new_document)
            db.commit()
            flash("مستندات با موفقیت بارگذاری شد.", "success")
        except (IOError, OSError, exc.SQLAlchemyError) as error:
            db.rollback()
            current_app.logger.error("Document save failed: %s", error)
            flash("خطایی در هنگام ذخیره فایل مستندات رخ داد.", "error")

    return redirect(url_for("client.update_team", team_id=team_id))


@client_blueprint.route("/UploadDocuments/<int:team_id>/<filename>")
@auth.login_required
def get_document(team_id, filename):
    "Return the requested document for a specific team"
    with database.get_db_session() as db:
        team = (
            db.query(models.Team.client_id)
            .filter(models.Team.team_id == team_id)
            .first()
        )

        if not team or (
            team.client_id != session.get("client_id")
            and not session.get("AdminLoggedIn")
        ):
            abort(403)

    filepath = safe_join(
        os.path.join(constants.Path.uploads_dir, "Documents", str(team_id)), filename
    )
    if filepath is None or not os.path.exists(filepath):
        abort(404)

    return send_from_directory(
        os.path.join(constants.Path.uploads_dir, "Documents", str(team_id)),
        filename,
        as_attachment=True,
    )


@client_blueprint.route("/Team/<int:team_id>/AddMember", methods=["POST"])
@auth.login_required
def add_member(team_id):
    "Handle adding a new member to a specific team"
    csrf_protector.protect()
    try:
        with database.get_db_session() as db:
            team = (
                db.query(models.Team)
                .filter(
                    models.Team.team_id == team_id,
                    models.Team.client_id == session["client_id"],
                    models.Team.status == models.EntityStatus.ACTIVE,
                )
                .first()
            )

            if not team:
                abort(404)

            current_member_count = (
                db.query(models.Member)
                .filter(
                    models.Member.team_id == team_id,
                    models.Member.status == models.EntityStatus.ACTIVE,
                )
                .count()
            )

            if current_member_count >= constants.AppConfig.max_members_per_team:
                flash("خطا: شما به حداکثر تعداد اعضای تیم رسیده‌اید.", "error")
                return redirect(url_for("client.manage_members", team_id=team_id))

            success, message = utils.internal_add_member(db, team_id, request.form)

            if success:
                member_name = message
                database.log_action(
                    db,
                    session["client_id"],
                    f"Added new member '{member_name}' to Team ID {team_id}.",
                )

                if database.check_if_team_is_paid(db, team_id):
                    team.unpaid_members_count = (team.unpaid_members_count or 0) + 1
                    flash(
                        "عضو جدید با موفقیت اضافه شد. لطفاً برای فعال‌سازی، "
                        "هزینه عضو جدید را پرداخت نمایید.",
                        "Warning",
                    )
                else:
                    flash("عضو با موفقیت اضافه شد!", "success")

                db.commit()
                utils.update_team_stats(db, team_id)
            else:
                flash(message, "error")

    except (exc.SQLAlchemyError, ValueError, TypeError) as error:
        current_app.logger.error("error adding member to Team %s: %s", team_id, error)
        flash("خطایی در هنگام افزودن عضو رخ داد.", "error")

    return redirect(url_for("client.manage_members", team_id=team_id))


@client_blueprint.route(
    "/Team/<int:team_id>/EditMember/<int:member_id>", methods=["GET", "POST"]
)
@auth.login_required
def edit_member(team_id, member_id):
    """Render and handle editing a member's information in a specific team."""
    template_name = constants.client_html_names_data["EditMember"]

    with database.get_db_session() as db:
        team = (
            db.query(models.Team)
            .filter(
                models.Team.team_id == team_id,
                models.Team.client_id == session["client_id"],
                models.Team.status == models.EntityStatus.ACTIVE,
            )
            .first()
        )

        if not team:
            abort(404, "تیم مورد نظر پیدا نشد یا شما دسترسی به این تیم را ندارید")

        member = (
            db.query(models.Member)
            .filter(
                models.Member.member_id == member_id,
                models.Member.team_id == team_id,
                models.Member.status == models.EntityStatus.ACTIVE,
            )
            .first()
        )

        if not member:
            flash("عضو مورد نظر یافت نشد.", "error")
            return redirect(url_for("client.manage_members", team_id=team_id))

        if request.method == "POST":
            auth.csrf_protector.protect()

            new_name = bleach.clean(request.form.get("Name", "").strip())
            new_role_value = request.form.get("Role", "").strip()
            new_national_id = fa_to_en(request.form.get("NationalID", "").strip())
            new_city_name = request.form.get("City", "").strip()
            new_province_name = request.form.get("Province", "").strip()

            role_map = {Role.value: Role for Role in models.MemberRole}
            new_role = role_map.get(new_role_value)

            if (
                not new_name
                or not new_national_id
                or not new_city_name
                or not new_province_name
            ):
                flash("نام، کد ملی، استان و شهر الزامی هستند.", "error")
                return render_template(
                    template_name,
                    Team=team,
                    member=member,
                    FormData=request.form,
                    **utils.get_form_context(),
                )

            if new_role == models.MemberRole.LEADER:
                if database.has_existing_leader(
                    db, team_id, member_id_to_exclude=member_id
                ):
                    flash("خطا: این تیم از قبل یک سرپرست دارد.", "error")
                    return redirect(
                        url_for(
                            "client.edit_member", team_id=team_id, member_id=member_id
                        )
                    )

            try:
                new_city_id = (
                    db.query(models.City.city_id)
                    .join(models.Province)
                    .filter(
                        models.Province.name == new_province_name,
                        models.City.name == new_city_name,
                    )
                    .scalar()
                )

                if not new_city_id:
                    flash("استان یا شهر انتخاب شده معتبر نیست.", "error")
                else:
                    member.name = new_name
                    if new_role is None:
                        flash("نقش انتخاب شده نامعتبر است.", "error")
                        return render_template(
                            template_name,
                            Team=team,
                            member=member,
                            FormData=request.form,
                            **utils.get_form_context(),
                        )
                    member.role = new_role
                    member.national_id = new_national_id
                    member.city_id = new_city_id
                    db.commit()

                    utils.update_team_stats(db, team_id)
                    database.log_action(
                        db,
                        session["client_id"],
                        f"Edited member '{new_name}' (ID: {member_id}) in Team ID {team_id}.",
                    )

                    flash("اطلاعات عضو با موفقیت به‌روزرسانی شد.", "success")
                    return redirect(url_for("client.manage_members", team_id=team_id))

            except (exc.SQLAlchemyError, ValueError, TypeError) as error:
                db.rollback()
                current_app.logger.error(
                    "error updating member %s: %s", member_id, error
                )
                flash("خطایی در هنگام به‌روزرسانی اطلاعات عضو رخ داد.", "error")

            return render_template(
                template_name,
                Team=team,
                member=member,
                FormData=request.form,
                **utils.get_form_context(),
            )

    return render_template(
        template_name, Team=team, member=member, **utils.get_form_context()
    )


@client_blueprint.route("/ReceiptUploads/<int:client_id>/<filename>")
@auth.login_required
def get_receipt(client_id, filename):
    "Return the requested receipt for a specific client"
    if client_id != session.get("client_id") and not session.get("AdminLoggedIn"):
        abort(403)
    return send_from_directory(
        os.path.join(current_app.config["UPLOAD_FOLDER_RECEIPTS"], str(client_id)),
        filename,
    )


@client_blueprint.route("/CreateTeam", methods=["GET", "POST"])
@auth.login_required
def create_team():
    "Render and handle the create team page"
    with database.get_db_session() as db:
        teams_count = (
            db.query(models.Team)
            .filter(
                models.Team.client_id == session["client_id"],
                models.Team.status == models.EntityStatus.ACTIVE,
            )
            .count()
        )
        if teams_count >= constants.AppConfig.max_team_per_client:
            flash("شما به حداکثر تعداد تیم مجاز رسیده‌اید.", "error")
            return redirect(url_for("client.dashboard"))

        if request.method == "POST":
            csrf_protector.protect()
            team_name = bleach.clean(request.form.get("TeamName", "").strip())
            form_context = utils.get_form_context()

            is_valid, error_message = utils.is_valid_team_name(team_name)
            if not is_valid:
                flash(error_message, "error")
                return render_template(
                    constants.client_html_names_data["CreateTeam"],
                    FormData=request.form,
                    **form_context,
                )

            first_member_data, error = utils.create_member_from_form_data(
                db, request.form
            )
            if error:
                flash(error, "error")
                return render_template(
                    constants.client_html_names_data["CreateTeam"],
                    FormData=request.form,
                    **form_context,
                )

            try:
                assert first_member_data is not None
                reg_date = datetime.datetime.now(datetime.timezone.utc)
                new_team = models.Team(
                    client_id=session["client_id"],
                    TeamName=team_name,
                    TeamRegistrationDate=reg_date,
                )
                db.add(new_team)
                db.flush()

                new_member = models.Member(
                    team_id=new_team.team_id, **first_member_data
                )
                db.add(new_member)
                db.commit()

                utils.update_team_stats(db, new_team.team_id)

                flash(f"تیم «{team_name}» با موفقیت ساخته شد!", "success")
                return redirect(url_for("client.dashboard"))
            except exc.IntegrityError:
                db.rollback()
                flash(
                    "تیمی با این نام از قبل وجود دارد. لطفا نام دیگری انتخاب کنید.",
                    "error",
                )
                return render_template(
                    constants.client_html_names_data["CreateTeam"],
                    FormData=request.form,
                    **form_context,
                )

    form_context = utils.get_form_context()
    return render_template(
        constants.client_html_names_data["CreateTeam"], **form_context
    )


@client_blueprint.route("/Team/<int:team_id>/SelectLeague", methods=["GET", "POST"])
@auth.login_required
def select_league(team_id):
    "Render and handle the league selection page for a specific team"
    with database.get_db_session() as db:
        team = (
            db.query(models.Team)
            .filter(
                models.Team.team_id == team_id,
                models.Team.client_id == session["client_id"],
                models.Team.status == models.EntityStatus.ACTIVE,
            )
            .first()
        )

        if not team:
            abort(404, "تیم پیدا نشد")

        if database.has_team_made_any_payment(db, team_id):
            flash(
                "از آنجایی که برای این تیم رسید پرداخت ارسال شده امکان تغییر لیگ‌ها وجود ندارد",
                "Warning",
            )
            return redirect(url_for("client.dashboard"))

        if request.method == "POST":
            csrf_protector.protect()
            league_one_id = request.form.get("LeagueOne")
            league_two_id = request.form.get("LeagueTwo")

            if not league_one_id:
                flash("لطفاً لیگ اول (اجباری) را انتخاب کنید.", "error")
                return redirect(url_for("client.select_league", team_id=team_id))

            if league_two_id and league_one_id == league_two_id:
                flash("شما نمی‌توانید یک لیگ را دو بار انتخاب کنید.", "error")
                return redirect(url_for("client.select_league", team_id=team_id))

            team.league_one_id = int(league_one_id) if league_one_id else None

            db.commit()
            flash("لیگ‌های تیم با موفقیت به‌روزرسانی شد.", "success")
            return redirect(url_for("client.dashboard"))

    return render_template(
        constants.client_html_names_data["SelectLeague"],
        Team=team,
        Leagues=constants.leagues_list,
    )


@client_blueprint.route("/Verify", methods=["GET", "POST"])
def verify_code():
    """Render and handle the verification page."""
    if request.method == "POST":
        csrf_protector.protect()
        action = request.form.get("action")
        response_redirect_url = None
        flash_message = None
        flash_category = None

        if action == "phone_signup":
            client_id = request.form.get("client_id")
            with database.get_db_session() as db:
                client = (
                    db.query(models.Client)
                    .filter(models.Client.client_id == client_id)
                    .first()
                )
                if client and client.phone_verification_code == request.form.get(
                    "code"
                ):
                    if (
                        client.verification_code_timestamp is not None
                        and (
                            datetime.datetime.now(datetime.timezone.utc)
                            - client.verification_code_timestamp
                        ).total_seconds()
                        > 900
                    ):
                        flash_message = (
                            "کد تایید منقضی شده است. لطفا دوباره درخواست دهید."
                        )
                        flash_category = "error"
                        response_redirect_url = url_for(
                            "client.verify_code",
                            action="phone_signup",
                            client_id=client_id,
                        )
                    else:
                        client.is_phone_verified = True
                        client.phone_verification_code = ""
                        db.commit()
                        flash_message = "شماره موبایل شما با موفقیت تایید شد! اکنون می‌توانید وارد شوید."
                        flash_category = "success"
                        response_redirect_url = url_for("client.login_client")
                else:
                    flash_message = "کد وارد شده صحیح نمی باشد."
                    flash_category = "error"
                    response_redirect_url = url_for(
                        "client.verify_code", action="phone_signup", client_id=client_id
                    )

        elif action == "password_reset":
            identifier = request.form.get("identifier")
            identifier_type = request.form.get("identifier_type")
            with database.get_db_session() as db:
                reset_record = (
                    db.query(models.PasswordReset)
                    .filter(
                        models.PasswordReset.identifier == identifier,
                        models.PasswordReset.identifier_type == identifier_type,
                        models.PasswordReset.code == request.form.get("code"),
                    )
                    .first()
                )
                if reset_record:
                    if (
                        reset_record.timestamp is not None
                        and (
                            datetime.datetime.now(datetime.timezone.utc)
                            - reset_record.timestamp
                        ).total_seconds()
                        > 900
                    ):
                        db.delete(reset_record)
                        db.commit()
                        flash_message = "کد منقضی شده است. لطفا دوباره درخواست دهید."
                        flash_category = "error"
                        response_redirect_url = url_for("client.forgot_password")
                    else:
                        new_token = secrets.token_urlsafe(32)
                        reset_record.code = new_token
                        reset_record.timestamp = datetime.datetime.now(
                            datetime.timezone.utc
                        )
                        db.commit()
                        response_redirect_url = url_for(
                            "client.reset_password", token=new_token
                        )
                else:
                    flash_message = "کد وارد شده صحیح نمی باشد."
                    flash_category = "error"
                    response_redirect_url = url_for(
                        "client.verify_code",
                        action="password_reset",
                        identifier=identifier,
                        identifier_type=identifier_type,
                    )
        else:
            flash_message = "عملیات نامعتبر است."
            flash_category = "error"
            response_redirect_url = url_for("client.login_client")

        if flash_message and flash_category:
            flash(flash_message, flash_category)
        return (
            redirect(response_redirect_url)
            if response_redirect_url
            else redirect(url_for("client.login_client"))
        )
    action = request.args.get("action")
    context = {"action": action, "Cooldown": 0}
    redirect_to_login = False

    if action == "phone_signup":
        client_id = request.args.get("client_id")
        if not client_id:
            flash("شناسه کاربر نامعتبر است.", "error")
            redirect_to_login = True
        else:
            with database.get_db_session() as db:
                client = (
                    db.query(models.Client)
                    .filter(models.Client.client_id == client_id)
                    .first()
                )
                if client and client.verification_code_timestamp is not None:
                    seconds_passed = (
                        datetime.datetime.now(datetime.timezone.utc)
                        - client.verification_code_timestamp
                    ).total_seconds()
                    if seconds_passed < 180:
                        context["Cooldown"] = 180 - int(seconds_passed)
            context["client_id"] = client_id

    elif action == "password_reset":
        identifier = request.args.get("identifier")
        identifier_type = request.args.get("identifier_type")
        if not identifier or not identifier_type:
            flash("اطلاعات مورد نیاز برای تایید کد موجود نیست.", "error")
            redirect_to_login = True
        else:
            with database.get_db_session() as db:
                reset_record = (
                    db.query(models.PasswordReset)
                    .filter(models.PasswordReset.identifier == identifier)
                    .first()
                )
                if not reset_record:
                    flash("درخواست بازیابی یافت نشد یا منقضی شده است.", "error")
                    redirect_to_login = True
                elif reset_record.timestamp is not None:
                    seconds_passed = (
                        datetime.datetime.now(datetime.timezone.utc)
                        - reset_record.timestamp
                    ).total_seconds()
                    if seconds_passed < 180:
                        context["Cooldown"] = 180 - int(seconds_passed)
            context["identifier"] = identifier
            context["identifier_type"] = identifier_type

    else:
        flash("صفحه مورد نظر یافت نشد.", "error")
        redirect_to_login = True

    if redirect_to_login:
        return redirect(url_for("client.login_client"))
    return render_template(constants.client_html_names_data["Verify"], **context)


@client_blueprint.route("/ResendCode", methods=["POST"])
@limiter.limit("5 per 15 minutes")
def resend_code():
    "Handle resending verification or password reset codes."
    request_data = request.get_json() or {}
    action = request_data.get("action")

    response_data = {"success": False, "message": "عملیات نامعتبر است."}
    status_code = 400

    if not action:
        response_data["message"] = "عملیات نامعتبر است."
        status_code = 400
    elif action == "phone_signup":
        client_id = request_data.get("client_id")
        if not client_id:
            response_data["message"] = "شناسه کاربر نامعتبر است."
            status_code = 400
        else:
            with database.get_db_session() as db:
                client = (
                    db.query(models.Client)
                    .filter(models.Client.client_id == client_id)
                    .first()
                )
                if not client:
                    response_data["message"] = "کاربر یافت نشد."
                    status_code = 404
                elif (
                    client.verification_code_timestamp is not None
                    and (
                        datetime.datetime.now(datetime.timezone.utc)
                        - client.verification_code_timestamp
                    ).total_seconds()
                    < 180
                ):
                    response_data["message"] = "لطفا ۳ دقیقه صبر کنید."
                    status_code = 429
                else:
                    new_code = "".join(random.choices(string.digits, k=6))
                    client.phone_verification_code = new_code
                    client.verification_code_timestamp = datetime.datetime.now(
                        datetime.timezone.utc
                    )
                    db.commit()

                    Thread(
                        target=utils.send_templated_sms_async,
                        args=(
                            current_app._get_current_object(),
                            client.client_id,
                            config.melli_payamak["template_id_phone_verification"],
                            new_code,
                            config.melli_payamak,
                        ),
                    ).start()
                    response_data = {"success": True, "message": "کد جدید ارسال شد."}
                    status_code = 200

    elif action == "password_reset":
        identifier = request_data.get("identifier")
        identifier_type = request_data.get("identifier_type")
        if not identifier or not identifier_type:
            response_data["message"] = "اطلاعات ناقص است."
            status_code = 400
        else:
            with database.get_db_session() as db:
                reset_record = (
                    db.query(models.PasswordReset)
                    .filter(models.PasswordReset.identifier == identifier)
                    .first()
                )
                if (
                    reset_record
                    and reset_record.timestamp is not None
                    and (
                        datetime.datetime.now(datetime.timezone.utc)
                        - reset_record.timestamp
                    ).total_seconds()
                    < 180
                ):
                    response_data["message"] = "لطفا ۳ دقیقه صبر کنید."
                    status_code = 429
                else:
                    client = database.get_client_by(db, identifier_type, identifier)
                    if not client:
                        response_data["message"] = "کاربر یافت نشد."
                        status_code = 404
                    else:
                        new_code = "".join(random.choices(string.digits, k=6))
                        if reset_record:
                            reset_record.code = new_code
                            reset_record.timestamp = datetime.datetime.now(
                                datetime.timezone.utc
                            )
                        else:
                            new_reset_record = models.PasswordReset(
                                identifier=identifier,
                                identifier_type=identifier_type,
                                code=new_code,
                                timestamp=datetime.datetime.now(datetime.timezone.utc),
                            )
                            db.add(new_reset_record)
                        db.commit()

                        if identifier_type == "Email":
                            subject = "کد بازیابی رمز عبور آیروکاپ"
                            body = f"کد بازیابی رمز عبور شما: {new_code}"
                            Thread(
                                target=utils.send_async_email,
                                args=(
                                    current_app._get_current_object(),
                                    client.client_id,
                                    subject,
                                    body,
                                    config.mail_configuration,
                                ),
                            ).start()
                        elif identifier_type == "phone_number":
                            Thread(
                                target=utils.send_templated_sms_async,
                                args=(
                                    current_app._get_current_object(),
                                    client.client_id,
                                    config.melli_payamak["template_id_password_reset"],
                                    new_code,
                                    config.melli_payamak,
                                ),
                            ).start()
                        response_data = {
                            "success": True,
                            "message": "کد جدید ارسال شد.",
                        }
                        status_code = 200
    else:
        response_data["message"] = "عملیات ناشناخته است."
        status_code = 400

    return jsonify(response_data), status_code


@client_blueprint.route("/ForgotPassword", methods=["GET", "POST"])
@limiter.limit("5 per 15 minutes")
def forgot_password():
    "Render and handle the forgot password page"
    if request.method == "POST":
        csrf_protector.protect()
        identifier = fa_to_en(request.form.get("identifier", "").strip())
        identifier_type = (
            "Email"
            if utils.is_valid_email(identifier)
            else "phone_number" if utils.is_valid_iranian_phone(identifier) else None
        )

        success_message = (
            "اگر کاربری با این مشخصات در سیستم وجود داشته باشد، "
            "کد بازیابی برایتان ارسال خواهد شد."
        )

        if not identifier_type:
            flash("لطفا یک ایمیل یا شماره موبایل معتبر وارد کنید.", "error")
            return redirect(url_for("client.forgot_password"))

        with database.get_db_session() as db:
            client_check = database.get_client_by(db, identifier_type, identifier)

            if client_check:
                reset_code = "".join(random.choices(string.digits, k=6))
                timestamp = datetime.datetime.now(datetime.timezone.utc)

                reset_record = (
                    db.query(models.PasswordReset)
                    .filter(models.PasswordReset.identifier == identifier)
                    .first()
                )
                if reset_record:
                    reset_record.code = reset_code
                    reset_record.timestamp = timestamp
                else:
                    new_reset_record = models.PasswordReset(
                        identifier=identifier,
                        identifier_type=identifier_type,
                        code=reset_code,
                        timestamp=timestamp,
                    )
                    db.add(new_reset_record)
                db.commit()

                if identifier_type == "email":
                    subject = "بازیابی رمز عبور آیروکاپ"
                    body = f"کد بازیابی رمز عبور شما در آیروکاپ: {reset_code}"
                    Thread(
                        target=utils.send_async_email,
                        args=(
                            current_app._get_current_object(),
                            client_check.client_id,
                            subject,
                            body,
                            config.mail_configuration,
                        ),
                    ).start()

                elif identifier_type == "phone_number":
                    Thread(
                        target=utils.send_templated_sms_async,
                        args=(
                            current_app._get_current_object(),
                            client_check.client_id,
                            config.melli_payamak["template_id_password_reset"],
                            reset_code,
                            config.melli_payamak,
                        ),
                    ).start()

            flash(success_message, "info")
            return redirect(
                url_for(
                    "client.verify_code",
                    action="password_reset",
                    identifier=identifier,
                    identifier_type=identifier_type,
                )
            )

    return render_template(constants.client_html_names_data["ForgotPassword"])


@client_blueprint.route("/ResendPasswordCode", methods=["POST"])
@limiter.limit("5 per 15 minutes")
def resend_password_code():
    "Handle resending password reset codes."
    request_data = request.get_json() or {}
    identifier = request_data.get("identifier")
    identifier_type = request_data.get("identifier_type")

    if not identifier or not identifier_type:
        return jsonify({"success": False, "message": "اطلاعات ناقص است."}), 400

    with database.get_db_session() as db:
        reset_record = (
            db.query(models.PasswordReset)
            .filter(models.PasswordReset.identifier == identifier)
            .first()
        )

        if reset_record and reset_record.timestamp is not None:
            if (
                datetime.datetime.now(datetime.timezone.utc) - reset_record.timestamp
            ).total_seconds() < 180:
                return (
                    jsonify({"success": False, "message": "لطفا ۳ دقیقه صبر کنید."}),
                    429,
                )

        client = database.get_client_by(db, identifier_type, identifier)
        if not client:
            return jsonify({"success": False, "message": "کاربر یافت نشد."}), 404

        new_code = "".join(random.choices(string.digits, k=6))

        if reset_record:
            reset_record.code = new_code
            reset_record.timestamp = datetime.datetime.now(datetime.timezone.utc)
        else:
            new_reset_record = models.PasswordReset(
                identifier=identifier,
                identifier_type=identifier_type,
                code=new_code,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            db.add(new_reset_record)

        db.commit()

        if identifier_type == "Email":
            subject = "بازیابی رمز عبور آیروکاپ"
            body = f"کد بازیابی رمز عبور شما در آیروکاپ: {new_code}"
            Thread(
                target=utils.send_async_email,
                args=(
                    current_app._get_current_object(),
                    client.client_id,
                    subject,
                    body,
                    config.mail_configuration,
                ),
            ).start()
        elif identifier_type == "phone_number":
            Thread(
                target=utils.send_templated_sms_async,
                args=(
                    current_app._get_current_object(),
                    client.client_id,
                    config.melli_payamak["template_id_password_reset"],
                    new_code,
                    config.melli_payamak,
                ),
            ).start()

    return jsonify({"success": True, "message": "کد جدید ارسال شد."})


@client_blueprint.route("/ResendVerificationCode", methods=["POST"])
@limiter.limit("5 per 15 minutes")
def resend_verification_code():
    "Handle resending verification codes"
    request_data = request.get_json() or {}
    client_id = request_data.get("client_id")

    if not client_id:
        return jsonify({"success": False, "message": "خطای کلاینت."}), 400

    with database.get_db_session() as db:
        client = (
            db.query(models.Client).filter(models.Client.client_id == client_id).first()
        )
        if not client:
            return jsonify({"success": False, "message": "کاربر یافت نشد."}), 404
        if client.verification_code_timestamp is not None:
            if (
                datetime.datetime.now(datetime.timezone.utc)
                - client.verification_code_timestamp
            ).total_seconds() < 180:
                return (
                    jsonify({"success": False, "message": "لطفا ۳ دقیقه صبر کنید."}),
                    429,
                )

        new_code = "".join(random.choices(string.digits, k=6))
        client.phone_verification_code = new_code
        client.verification_code_timestamp = datetime.datetime.now(
            datetime.timezone.utc
        )
        db.commit()

    Thread(
        target=utils.send_templated_sms_async,
        args=(
            current_app._get_current_object(),
            client_id,
            config.melli_payamak["template_id_verification"],
            new_code,
            config.melli_payamak,
        ),
    ).start()

    return jsonify({"success": True, "message": "کد جدید ارسال شد."})


@client_blueprint.route("/ResetPassword", methods=["GET", "POST"])
def reset_password():
    """Render and handle the reset password page."""
    token = request.args.get("token")
    if not token:
        flash("توکن بازیابی نامعتبر است یا وجود ندارد.", "error")
        return redirect(url_for("client.forgot_password"))

    if request.method == "POST":
        csrf_protector.protect()

        flash_message = None
        flash_category = None
        redirect_url = None

        new_password = request.form.get("new_password") or ""
        is_valid, error_message = utils.is_valid_password(new_password)
        if not is_valid:
            flash_message = error_message or "خطای نامشخص در رمز عبور."
            flash_category = "error"
            redirect_url = url_for("client.reset_password", token=token)
        else:
            with database.get_db_session() as db:
                valid_record = (
                    db.query(models.PasswordReset)
                    .filter(models.PasswordReset.code == token)
                    .first()
                )

                if not valid_record:
                    flash_message = "توکن بازیابی نامعتبر است یا قبلا استفاده شده است."
                    flash_category = "error"
                    redirect_url = url_for("client.forgot_password")
                elif (
                    datetime.datetime.now(datetime.timezone.utc)
                    - valid_record.timestamp
                ).total_seconds() > 900:
                    db.delete(valid_record)
                    db.commit()
                    flash_message = (
                        "توکن بازیابی منقضی شده است. لطفا دوباره درخواست دهید."
                    )
                    flash_category = "error"
                    redirect_url = url_for("client.forgot_password")
                    redirect_url = url_for("client.forgot_password")
                else:
                    client_to_update = database.get_client_by(
                        db, valid_record.identifier_type, valid_record.identifier
                    )
                    if client_to_update:
                        hashed_password = bcrypt.hashpw(
                            request.form.get("new_password").encode("utf-8"),
                            bcrypt.gensalt(),
                        )
                        client_to_update.password = hashed_password.decode("utf-8")
                        db.delete(valid_record)
                        db.commit()
                        flash_message = "رمز عبور شما با موفقیت تغییر یافت."
                        flash_category = "success"
                        redirect_url = url_for("client.login_client")
                    else:
                        db.delete(valid_record)
                        db.commit()
                        flash_message = "کاربر مرتبط با این توکن یافت نشد."
                        flash_category = "error"
                        redirect_url = url_for("client.forgot_password")

        if flash_message:
            flash(flash_message, flash_category)
        return (
            redirect(redirect_url)
            if redirect_url
            else redirect(url_for("client.forgot_password"))
        )

    return render_template(
        constants.client_html_names_data["ResetPassword"], token=token
    )


def _calculate_payment_details(db, team):
    """Calculates payment details for a team based on its status and members."""
    is_new_member_payment = database.check_if_team_is_paid(db, team.team_id)
    total_cost = 0
    members_to_pay_for = 0
    num_members = 0
    league_one_cost = 0
    league_two_cost = 0
    discount_amount = 0

    if is_new_member_payment:
        members_to_pay_for = (
            team.unpaid_members_count if team.unpaid_members_count is not None else 0
        )
        if members_to_pay_for == 0:
            return {}, "در حال حاضر عضو جدیدی برای پرداخت وجود ندارد.", "info", True
        total_cost = members_to_pay_for * config.payment_config["fee_per_person"]
    else:
        num_members = (
            db.query(models.Member)
            .filter(
                models.Member.team_id == team.team_id,
                models.Member.status == models.EntityStatus.ACTIVE,
            )
            .count()
        )
        members_to_pay_for = num_members
        members_fee = num_members * config.payment_config["fee_per_person"]
        league_one_cost = config.payment_config["fee_team"] + members_fee
        total_cost = league_one_cost

        if team.league_two_id is not None:
            discount_percent = config.payment_config["league_two_discount"] / 100
            discount_amount = members_fee * discount_percent
            league_two_cost = members_fee - discount_amount
            total_cost += league_two_cost

    context = {
        "IsNewMemberPayment": is_new_member_payment,
        "membersToPayFor": members_to_pay_for,
        "TotalFee": total_cost,
        "Nummembers": num_members,
        "LeagueOneCost": league_one_cost,
        "LeagueTwoCost": league_two_cost,
        "DiscountAmount": discount_amount,
    }
    return context, None, None, False


def _process_payment_submission(db, team, receipt_file, total_cost, members_to_pay_for):
    """Handles saving the receipt file and creating a payment record."""
    original_filename = secure_filename(receipt_file.filename)
    extension = (
        original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else ""
    )
    secure_name = f"{uuid.uuid4()}.{extension}"

    new_payment = models.Payment(
        team_id=team.team_id,
        client_id=session["client_id"],
        Amount=total_cost,
        membersPaidFor=members_to_pay_for,
        ReceiptFilename=secure_name,
        UploadDate=datetime.datetime.now(datetime.timezone.utc),
        Status=models.PaymentStatus.PENDING,
    )
    db.add(new_payment)

    try:
        user_receipts_folder = os.path.join(
            current_app.config["UPLOAD_FOLDER_RECEIPTS"],
            str(session["client_id"]),
        )
        os.makedirs(user_receipts_folder, exist_ok=True)
        receipt_file.save(os.path.join(user_receipts_folder, secure_name))
        db.commit()
        return True, "متشکریم! رسید شما با موفقیت بارگذاری و برای بررسی ارسال شد."
    except (IOError, OSError, exc.SQLAlchemyError) as error:
        db.rollback()
        current_app.logger.error("File save failed for payment: %s", error)
        return False, "خطایی در هنگام ذخیره فایل رسید رخ داد. لطفا دوباره تلاش کنید."


@client_blueprint.route("/Team/<int:team_id>/Payment", methods=["GET", "POST"])
@auth.login_required
def payment(team_id):
    "Render and handle the payment page for a team"
    with database.get_db_session() as db:
        team = (
            db.query(models.Team)
            .filter(
                models.Team.team_id == team_id,
                models.Team.client_id == session["client_id"],
                models.Team.status == models.EntityStatus.ACTIVE,
            )
            .first()
        )
        temp = constants.AppConfig.max_image_size
        if not team:
            abort(404, "تیم پیدا نشد")

        if request.method == "POST":
            auth.csrf_protector.protect()
            receipt_file = request.files.get("receipt")
            if not receipt_file or receipt_file.filename == "":
                flash("لطفا فایل رسید پرداخت را انتخاب کنید.", "error")
                return redirect(request.url)

            if request.content_length is None or request.content_length > temp:
                flash(
                    f"حجم فایل رسید نباید بیشتر از { temp / 1024 / 1024:.1f} مگابایت باشد.",
                    "error",
                )
                return redirect(request.url)

            receipt_file.stream.seek(0)
            if not utils.is_file_allowed(receipt_file.stream):
                flash("نوع فایل مجاز نیست یا فایل خراب است.", "error")
                return redirect(request.url)
            receipt_file.stream.seek(0)

            (
                payment_context,
                flash_msg,
                flash_cat,
                should_redirect_dash,
            ) = _calculate_payment_details(db, team)
            if should_redirect_dash:
                flash(flash_msg, flash_cat)
                return redirect(url_for("client.dashboard"))

            total_cost = payment_context["TotalFee"]
            members_to_pay_for = payment_context["membersToPayFor"]

            success, message = _process_payment_submission(
                db, team, receipt_file, total_cost, members_to_pay_for
            )

            flash(message, "success" if success else "error")
            return redirect(url_for("client.dashboard"))

        (
            payment_context,
            flash_msg,
            flash_cat,
            should_redirect_dash,
        ) = _calculate_payment_details(db, team)
        if should_redirect_dash:
            flash(flash_msg, flash_cat)
            return redirect(url_for("client.dashboard"))

        return render_template(
            constants.client_html_names_data["Payment"], Team=team, **payment_context
        )


@client_blueprint.route("/Dashboard")
@auth.login_required
def dashboard():
    "Render the client dashboard page"
    with database.get_db_session() as db:
        teams = (
            db.query(models.Team)
            .options(subqueryload(models.Team.members))
            .filter(
                models.Team.client_id == session.get("client_id"),
                models.Team.status == models.EntityStatus.ACTIVE,
            )
            .order_by(models.Team.team_registration_date.desc())
            .all()
        )

        team_ids = [Team.team_id for Team in teams]
        payment_statuses = {}

        if team_ids:
            subquery = (
                select(
                    models.Payment.team_id,
                    models.Payment.status,
                    func.row_number()
                    .over(
                        partition_by=models.Payment.team_id,
                        order_by=models.Payment.upload_date.desc(),
                    )
                    .label("row_number"),
                )
                .where(models.Payment.team_id.in_(team_ids))
                .subquery()
            )

            latest_payments = (
                db.query(subquery).filter(subquery.c.row_number == 1).all()
            )
            payment_statuses = {row.team_id: row.status for row in latest_payments}

        for team in teams:
            setattr(team, "last_payment_status", payment_statuses.get(team.team_id))

    return render_template(
        constants.client_html_names_data["Dashboard"],
        teams=teams,
        payment_info=config.payment_config["fee_per_person"],  # Todo
    )
