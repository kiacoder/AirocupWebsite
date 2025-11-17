"Global routes and views"

import os
from flask import (
    abort,
    render_template,
    send_from_directory,
    redirect,
    session,
    url_for,
    flash,
    Blueprint,
    current_app,
)
from . import constants
from . import database

global_blueprint = Blueprint("global", __name__)

gallery_images = sorted(
    [
        f
        for f in os.listdir(constants.Path.gallery_dir)
        if os.path.isfile(os.path.join(constants.Path.gallery_dir, f))
    ]
)


@global_blueprint.route("/")
def index():
    "Index page"
    return render_template(constants.global_html_names_data["index"])


@global_blueprint.route("/About")
def about():
    "About page"
    return render_template(constants.global_html_names_data["about"])


@global_blueprint.route("/Cooperate")
def cooperate():
    "Cooperate page"
    return render_template(constants.global_html_names_data["cooperate"])


@global_blueprint.route("/Leagues")
def leagues():
    "Leagues page"
    return render_template(constants.global_html_names_data["leagues"])


@global_blueprint.route("/Sponsors")
def sponsors():
    "Sponsors page"
    return render_template(constants.global_html_names_data["sponsors"])


@global_blueprint.route("/Contact")
def contact():
    "Contact page"
    return render_template(constants.global_html_names_data["contact"])


@global_blueprint.route("/Committee")
def committee():
    "Committee page"
    return render_template(constants.global_html_names_data["committee"])


@global_blueprint.route("/TechnicalCommittee")
def technical_committee():
    "Technical Committee page"
    return render_template(constants.global_html_names_data["technical_committee"])


@global_blueprint.route("/News")
def news():
    "News page"
    with database.get_db_session() as db:
        articles = database.get_all_articles(db)
    return render_template(constants.global_html_names_data["news"], articles=articles)


@global_blueprint.route("/News/<int:article_id>")
def view_article(article_id):
    "View a specific news article"
    with database.get_db_session() as db:
        article = database.get_article_by_id(db, article_id)
    if not article:
        abort(404)

    if article.template_path:
        file_name = os.path.basename(article.template_path)
        html_path = os.path.join(constants.Path.news_html_dir, file_name)
        if os.path.exists(html_path):
            return send_from_directory(
                constants.Path.news_html_dir, file_name, mimetype="text/html"
            )
        current_app.logger.error(
            "Template %s not found for Article %s",
            article.template_path,
            article_id,
        )
        abort(500, "Template file for this article could not be found.")
    return render_template(constants.global_html_names_data["article"], article=article)


@global_blueprint.route("/Gallery")
def gallery():
    "Gallery page"
    return render_template(
        constants.global_html_names_data["gallery"],
        gallery_images=gallery_images,
        gallery_videos=constants.gallery_videos_data,
    )


@global_blueprint.route("/uploads/news/<filename>")
def uploaded_news_image(filename):
    "Serve uploaded news images securely"
    return send_from_directory(current_app.config["UPLOAD_FOLDER_NEWS"], filename)


@global_blueprint.route("/Download/Rules")
def download_pdf():
    "Download the guideline PDF file"
    guideline_file = constants.Path.guideline_file

    if not os.path.exists(guideline_file):
        current_app.logger.warning(
            "Requested guideline PDF is missing at %s", guideline_file
        )
        flash(
            "فایل راهنمای لیگ‌ها در حال حاضر در دسترس نیست. لطفاً بعداً دوباره تلاش کنید.",
            "warning",
        )
        return redirect(url_for("global.leagues"))

    return send_from_directory(
        constants.Path.guideline_dir,
        os.path.basename(guideline_file),
        as_attachment=True,
        download_name="Airocup-Leagues-Guideline.pdf",
        mimetype="application/pdf",
    )


@global_blueprint.route("/Logout")
def logout():
    "Log out the current user"
    session.clear()
    flash("شما از حساب کاربری خود خارج شدید.", "info")
    return redirect(url_for("global.index"))
