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