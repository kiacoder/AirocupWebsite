
from functools import wraps
from flask import session, redirect, url_for, flash, abort
from flask_wtf.csrf import CSRFError
from extensions import csrf_protector

def admin_required(decorated_route):
    "@wraps decorator to ensure admin access is required for a route"
    @wraps(decorated_route)
    def decorated_function(*args, **kwargs):
        "Checks if admin is logged in; redirects to admin login if not"
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.admin_login"))
        return decorated_route(*args, **kwargs)

    return decorated_function


def admin_action_required(decorated_route):
    "@wraps decorator to ensure admin action is required for a route"
    @wraps(decorated_route)
    def decorated_function(*args, **kwargs):
        "Checks if admin is logged in and protects against CSRF"
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.admin_login"))
        try:
            csrf_protector.protect()
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
            return redirect(url_for("client.login_client"))
        return f(*args, **kwargs)

    return decorated_function


def login_required(decorated_route):
    "@wraps decorator to ensure user login is required for a route"
    @wraps(decorated_route)
    def decorated_function(*args, **kwargs):
        "Checks if user is logged in; redirects to login if not"
        if "client_id" not in session:
            flash("برای مشاهده این صفحه باید وارد شوید.", "Warning")
            return redirect(url_for("client.login_client", next=request.url))
        if "client_idForResolution" in session:
            flash(
                "ابتدا باید اطلاعات حساب کاربری خود را تکمیل و اصلاح نمایید.", "Warning"
            )
            return redirect(url_for("client.resolve_data_issues"))
        return decorated_route(*args, **kwargs)

    return decorated_function
