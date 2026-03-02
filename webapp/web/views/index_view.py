from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

module = Blueprint("index", __name__)


@module.route("/")
@login_required
def index():
    return render_template("/index/index.html")
