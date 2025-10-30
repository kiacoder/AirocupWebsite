import os as OS
from flask import (
    abort as Abort,
    render_template as RenderTemplate,
    send_from_directory as SendFromDirectory,
    redirect as ReDirect,
    session,
    url_for as URLFor,
    flash as Flash,
    Blueprint,
)
from jinja2 import TemplateNotFound
from werkzeug.utils import safe_join as SafeJoin
import Constants
import Database
import App

GlobalBlueprint = Blueprint("Global", __name__)


@GlobalBlueprint.route("/")
def Index():
    return RenderTemplate(Constants.GlobalHTMLNamesData["Index"])


@GlobalBlueprint.route("/About")
def About():
    return RenderTemplate(Constants.GlobalHTMLNamesData["About"])


@GlobalBlueprint.route("/Cooperate")
def Cooperate():
    return RenderTemplate(Constants.GlobalHTMLNamesData["Cooperate"])


@GlobalBlueprint.route("/Leagues")
def Leagues():
    return RenderTemplate(Constants.GlobalHTMLNamesData["Leagues"])


@GlobalBlueprint.route("/Sponsors")
def Sponsors():
    return RenderTemplate(Constants.GlobalHTMLNamesData["Sponsors"])


@GlobalBlueprint.route("/Contact")
def Contact():
    return RenderTemplate(Constants.GlobalHTMLNamesData["Contact"])


@GlobalBlueprint.route("/Committee")
def Committee():
    return RenderTemplate(Constants.GlobalHTMLNamesData["Committee"])


@GlobalBlueprint.route("/TechnicalCommittee")
def TechnicalCommittee():
    return RenderTemplate(Constants.GlobalHTMLNamesData["TechnicalCommittee"])


@GlobalBlueprint.route("/News")
def News():
    with Database.GetDBSession() as DbSession:
        Articles = Database.GetAllArticles(DbSession)
    return RenderTemplate(Constants.GlobalHTMLNamesData["News"], Articles=Articles)


@GlobalBlueprint.route("/News/<int:ArticleID>")
def ViewArticle(ArticleID):
    with Database.GetDBSession() as DbSession:
        Article = Database.GetArticleByID(DbSession, ArticleID)
    if not Article:
        Abort(404)

    if Article.TemplatePath:
        try:
            return RenderTemplate(f"News/{Article.TemplatePath}")
        except TemplateNotFound:
            App.FlaskApp.logger.error(
                f"Template '{Article.TemplatePath}' not found for Article {ArticleID}."
            )
            Abort(500, "Template file for this article could not be found.")
    return RenderTemplate(Constants.GlobalHTMLNamesData["Article"], Article=Article)


@GlobalBlueprint.route("/Gallery")
def Gallery():
    GalleryImages = sorted(
        [
            f
            for f in OS.listdir(Constants.Path.GalleryDir)
            if OS.path.isfile(OS.path.join(Constants.Path.GalleryDir, f))
        ]
    )
    return RenderTemplate(
        Constants.GlobalHTMLNamesData["Gallery"],
        GalleryImages=GalleryImages,
        GalleryVideos=Constants.GalleryVideosData,
    )


@GlobalBlueprint.route("/uploads/news/<filename>")
def UploadedNewsImage(filename):
    FilePath = SafeJoin(App.FlaskApp.config["UPLOAD_FOLDER_NEWS"], filename)
    if FilePath is None or not OS.path.exists(FilePath):
        Abort(404)
    return SendFromDirectory(App.FlaskApp.config["UPLOAD_FOLDER_NEWS"], filename)


@GlobalBlueprint.route("/Download/Rules")
def DownloadPDF():
    return SendFromDirectory(
        OS.path.dirname(Constants.Path.GuideLineDir),
        OS.path.basename(Constants.Path.GuideLineDir),
        as_attachment=True,
    )


@GlobalBlueprint.route("/Logout")
def Logout():
    session.clear()
    Flash("شما از حساب کاربری خود خارج شدید.", "Info")
    return ReDirect(URLFor("Global.Index"))
