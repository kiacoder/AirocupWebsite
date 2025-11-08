"Global routes for the Airocup website"
import os
from flask import (
    abort as Abort,
    render_template as RenderTemplate,
    send_from_directory as SendFromDirectory,
    redirect as ReDirect,
    session,
    url_for as URLFor,
    flash as Flash,
    Blueprint,
    current_app,
)
from jinja2 import TemplateNotFound
from werkzeug.security import safe_join
from . import constants
from . import database

global_blueprint = Blueprint("Global", __name__)


@global_blueprint.route("/")
def index():
    "Index page"
    return RenderTemplate(constants.global_html_names_data["Index"])


@global_blueprint.route("/About")
def about():
    "About page"
    return RenderTemplate(constants.global_html_names_data["About"])


@global_blueprint.route("/Cooperate")
def cooperate():
    "Cooperate page"
    return RenderTemplate(constants.global_html_names_data["Cooperate"])


@global_blueprint.route("/Leagues")
def leagues():
    "Leagues page"
    return RenderTemplate(constants.global_html_names_data["Leagues"])


@global_blueprint.route("/Sponsors")
def sponsors():
    "Sponsors page"
    return RenderTemplate(constants.global_html_names_data["Sponsors"])


@global_blueprint.route("/Contact")
def contact():
    "Contact page"
    return RenderTemplate(constants.global_html_names_data["Contact"])


@global_blueprint.route("/Committee")
def committee():
    "Committee page"
    return RenderTemplate(constants.global_html_names_data["Committee"])


@global_blueprint.route("/TechnicalCommittee")
def technical_committee():
    "Technical Committee page"
    return RenderTemplate(constants.global_html_names_data["TechnicalCommittee"])


@global_blueprint.route("/News")
def news():
    "News page"
    with database.get_db_session() as db:
        articles = database.get_all_articles(db)
    return RenderTemplate(constants.global_html_names_data["News"], Articles=articles)


@global_blueprint.route("/News/<int:ArticleID>")
def view_article(article_id):
    "View a specific news article"
    with database.get_db_session() as db:
        article = database.get_article_by_id(db, article_id)
    if not article:
        Abort(404)

    if article.template_path:
        try:
            return RenderTemplate(f"News/{article.template_path}")
        except TemplateNotFound:
            current_app.logger.error(
                "Template %s not found for Article %s",
                article.template_path,
                article_id,
            )
            Abort(500, "Template file for this article could not be found.")
    return RenderTemplate(constants.global_html_names_data["article"], article=article)


@global_blueprint.route("/Gallery")
def gallery():
    "Gallery page"
    gallery_images = sorted(
        [
            f
            for f in os.listdir(constants.Path.gallery_dir)
            if os.path.isfile(os.path.join(constants.Path.gallery_dir, f))
        ]
    )
    return RenderTemplate(
        constants.global_html_names_data["Gallery"],
        GalleryImages=gallery_images,
        GalleryVideos=constants.gallery_videos_data,
    )


@global_blueprint.route("/uploads/news/<filename>")
def uploaded_news_image(filename):
    "Serve uploaded news images"
    file_path = safe_join(current_app.config["UPLOAD_FOLDER_NEWS"], filename)
    if file_path is None or not os.path.exists(file_path):
        Abort(404)
    return SendFromDirectory(current_app.config["UPLOAD_FOLDER_NEWS"], filename)


@global_blueprint.route("/Download/Rules")
def download_pdf():
    "Download the guideline PDF file"
    return SendFromDirectory(
        os.path.dirname(constants.Path.guideline_dir),
        os.path.basename(constants.Path.guideline_dir),
        as_attachment=True,
    )


@global_blueprint.route("/Logout")
def logout():
    "Log out the current user"
    session.clear()
    Flash("شما از حساب کاربری خود خارج شدید.", "Info")
    return ReDirect(URLFor("Global.index"))