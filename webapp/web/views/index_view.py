from flask import Blueprint, render_template

module = Blueprint("index", __name__)


@module.route("/")
def index():
    return render_template("/index/index.html")
