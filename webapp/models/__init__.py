from flask_mongoengine import MongoEngine
from flask import Flask

db = MongoEngine()


def init_db(app: Flask):
    db.init_app(app)
