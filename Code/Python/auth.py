from functools import wraps
from flask import request, session, flash, redirect, url_for, abort
from flask_wtf.csrf import CSRFError
from . import config


def login_required(decorated_route):
    "Decorator to ensure that a user is logged in and not in data resolution process"
    @wraps(decorated_route)
    def decorated_function(*args, **kwargs):
        if "client_id" not in session:
            flash("برای مشاهده این صفحه باید وارد شوید.", "Warning")
            return redirect(url_for("client.login_client", next=request.url))
        if "client_idForResolution" in session:
            flash("ابتدا باید اطلاعات حساب کاربری خود را تکمیل و اصلاح نمایید.", "Warning")
            return redirect(url_for("client.resolve_data_issues"))
        return decorated_route(*args, **kwargs)
    return decorated_function


def resolution_required(f):
    "Decorator to ensure that the user is in the data resolution process"
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "client_idForResolution" not in session:
            flash("شما در وضعیت اصلاح اطلاعات قرار ندارید.", "Info")
            return redirect(url_for("client.login_client", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(decorated_route):
    "Decorator to ensure that an admin is logged in"
    @wraps(decorated_route)
    def decorated_function(*args, **kwargs):
        if not session.get("AdminLoggedIn"):
            return redirect(url_for("AdminLogin"))
        return decorated_route(*args, **kwargs)
    return decorated_function


def admin_action_required(decorated_route):
    "Decorator to ensure that an admin is logged in and CSRF protection is applied for admin actions"
    @wraps(decorated_route)
    def decorated_function(*args, **kwargs):
        if not session.get("AdminLoggedIn"):
            return redirect(url_for("AdminLogin"))
        try:
            from .app import csrf_protector
            csrf_protector.protect()
        except CSRFError:
            abort(400, "توکن امنیتی نامعتبر است (CSRF).")
        return decorated_route(*args, **kwargs)
    return decorated_function





# def login_required(decorated_route):
#     "Decorator to ensure user login is required for a route"

#     @wraps(decorated_route)
#     def decorated_function(*args, **kwargs):
#         """Checks if user is logged in; redirects to login if not."""
#         if "client_id" not in session:
#             flash("برای مشاهده این صفحه باید وارد شوید.", "Warning")
#             return redirect(url_for("client.login_client", next=request.url))

#         if "client_idForResolution" in session:
#             flash(
#                 "ابتدا باید اطلاعات حساب کاربری خود را تکمیل و اصلاح نمایید.",
#                 "Warning",
#             )
#             return redirect(url_for("client.resolve_data_issues"))

#         return decorated_route(*args, **kwargs)

#     return decorated_function

# def resolution_required(f):
#     """Decorator to ensure user is in data resolution state."""

#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         if "client_idForResolution" not in session:
#             flash("شما در وضعیت اصلاح اطلاعات قرار ندارید.", "Info")
#             return redirect(url_for("client.login_client", next=request.url))
#         return f(*args, **kwargs)

#     return decorated_function

# def admin_required(decorated_route):
#     """Decorator to ensure admin access is required for a route."""

#     @wraps(decorated_route)
#     def decorated_function(*args, **kwargs):
#         """Checks if admin is logged in; redirects to admin login if not."""
#         if not session.get("AdminLoggedIn"):
#             return redirect(url_for("AdminLogin"))
#         return decorated_route(*args, **kwargs)

#     return decorated_function

# def admin_action_required(decorated_route):
#     """Decorator to ensure admin action is required for a route."""

#     @wraps(decorated_route)
#     def decorated_function(*args, **kwargs):
#         """Checks if admin is logged in and protects against CSRF."""
#         if not session.get("AdminLoggedIn"):
#             return redirect(url_for("AdminLogin"))

#         try:
#             csrf_protector.protect()
#         except CSRFError:
#             abort(400, "توکن امنیتی نامعتبر است (CSRF).")

#         return decorated_route(*args, **kwargs)

#     return decorated_function


