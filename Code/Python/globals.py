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
from jinja2 import TemplateNotFound
from . import constants
from . import database

global_blueprint = Blueprint("Global", __name__)

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
    return render_template(constants.global_html_names_data["Index"])


@global_blueprint.route("/About")
def about():
    "About page"
    return render_template(constants.global_html_names_data["About"])


@global_blueprint.route("/Cooperate")
def cooperate():
    "Cooperate page"
    return render_template(constants.global_html_names_data["Cooperate"])


@global_blueprint.route("/Leagues")
def leagues():
    "Leagues page"
    return render_template(constants.global_html_names_data["Leagues"])


@global_blueprint.route("/Sponsors")
def sponsors():
    "Sponsors page"
    return render_template(constants.global_html_names_data["Sponsors"])


@global_blueprint.route("/Contact")
def contact():
    "Contact page"
    return render_template(constants.global_html_names_data["Contact"])


@global_blueprint.route("/Committee")
def committee():
    "Committee page"
    return render_template(constants.global_html_names_data["Committee"])


@global_blueprint.route("/TechnicalCommittee")
def technical_committee():
    "Technical Committee page"
    return render_template(constants.global_html_names_data["TechnicalCommittee"])


@global_blueprint.route("/News")
def news():
    "News page"
    with database.get_db_session() as db:
        articles = database.get_all_articles(db)
    return render_template(constants.global_html_names_data["News"], Articles=articles)


@global_blueprint.route("/News/<int:ArticleID>")
def view_article(article_id):
    "View a specific news article"
    with database.get_db_session() as db:
        article = database.get_article_by_id(db, article_id)
    if not article:
        abort(404)

    if article.template_path:
        try:
            return render_template(f"News/{article.template_path}")
        except TemplateNotFound:
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
        constants.global_html_names_data["Gallery"],
        GalleryImages=gallery_images,
        GalleryVideos=constants.gallery_videos_data,
    )


@global_blueprint.route("/uploads/news/<filename>")
def uploaded_news_image(filename):
    "Serve uploaded news images securely"
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER_NEWS"],
        filename
    )


@global_blueprint.route("/Download/Rules")
def download_pdf():
    "Download the guideline PDF file"
    return send_from_directory(
        os.path.dirname(constants.Path.guideline_dir),
        os.path.basename(constants.Path.guideline_dir),
        as_attachment=True,
    )


@global_blueprint.route("/Logout")
def logout():
    "Log out the current user"
    session.clear()
    flash("شما از حساب کاربری خود خارج شدید.", "Info")
    return redirect(url_for("Global.index"))
