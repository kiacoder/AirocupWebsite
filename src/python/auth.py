"Decorators for route authentication and authorization"

from functools import wraps
from flask import request, session, flash, redirect, url_for, abort
from flask_wtf.csrf import CSRFError  # type:ignore

from . import database, models
from .extensions import csrf_protector


def login_required(decorated_route):
    """Decorator to ensure that a user is logged in and not in the data resolution process."""

    @wraps(decorated_route)
    def decorated_function(*args, **kwargs):
        if "client_id" not in session:
            flash("برای مشاهده این صفحه باید وارد شوید.", "warning")
            return redirect(url_for("client.login_client", next=request.url))

        if not session.get("needs_contact_completion"):
            with database.get_db_session() as db:
                client = (
                    db.query(models.Client)
                    .filter(models.Client.client_id == session.get("client_id"))
                    .first()
                )

                if not client:
                    session.clear()
                    flash("برای ادامه باید دوباره وارد حساب خود شوید.", "warning")
                    return redirect(url_for("client.login_client", next=request.url))

                if not client.email or not client.phone_number:
                    session["needs_contact_completion"] = True
                    flash(
                        "برای ادامه، لطفا اطلاعات تماس حساب کاربری خود را تکمیل کنید.",
                        "warning",
                    )
                    if request.endpoint != "client.complete_profile":
                        return redirect(url_for("client.complete_profile"))

        if session.get("needs_contact_completion"):
            allowed_endpoints = {"client.complete_profile", "global.logout"}
            if request.endpoint not in allowed_endpoints:
                flash(
                    "برای ادامه، لطفا اطلاعات تماس حساب کاربری خود را تکمیل کنید.",
                    "warning",
                )
                return redirect(url_for("client.complete_profile"))

        if "client_id_for_resolution" in session:
            flash(
                "ابتدا باید اطلاعات حساب کاربری خود را تکمیل و اصلاح نمایید.", "warning"
            )
            return redirect(url_for("client.resolve_data_issues"))

        return decorated_route(*args, **kwargs)

    return decorated_function


def resolution_required(f):
    """Decorator to ensure that the user is in the data resolution process."""

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "client_id_for_resolution" not in session:
            flash("شما در وضعیت اصلاح اطلاعات قرار ندارید.", "info")
            return redirect(url_for("client.login_client", next=request.url))

        return f(*args, **kwargs)

    return decorated_function


def admin_required(decorated_route):
    """Decorator to ensure that an admin is logged in."""

    @wraps(decorated_route)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.admin_login"))

        return decorated_route(*args, **kwargs)

    return decorated_function


def admin_action_required(decorated_route):
    """Decorator to ensure an admin is logged in and CSRF protection is applied."""

    @wraps(decorated_route)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.admin_login"))

        try:

            csrf_protector.protect()
        except CSRFError:
            abort(400, "توکن امنیتی نامعتبر است (CSRF).")

        return decorated_route(*args, **kwargs)

    return decorated_function
