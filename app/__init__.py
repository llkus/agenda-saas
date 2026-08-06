from flask import Flask

from app.config import Config
from app.extensions import db, migrate, jwt


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from app import models  # noqa: F401  (registra os models no metadata do SQLAlchemy)

    @app.route("/")
    def hello():
        return {"status": "ok", "service": "agenda-saas"}

    return app
