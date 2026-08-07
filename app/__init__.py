from flask import Flask
from flask_jwt_extended import get_current_user

from app.config import Config
from app.extensions import db, migrate, jwt, csrf, limiter


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.config["SECRET_KEY"] or not app.config["JWT_SECRET_KEY"]:
        raise RuntimeError(
            "SECRET_KEY / JWT_SECRET_KEY não definidas. Gere com: "
            "python3 -c \"import secrets; print(secrets.token_hex(32))\" e coloque no .env"
        )

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from app import models  # noqa: F401  (registra os models no metadata do SQLAlchemy)
    from app.models import User

    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return str(user.id)

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        return db.session.get(User, int(jwt_data["sub"]))

    from app.blueprints.auth import auth_bp
    from app.blueprints.painel import painel_bp
    from app.blueprints.servicos import servicos_bp
    from app.blueprints.clientes import clientes_bp
    from app.blueprints.disponibilidade import disponibilidade_bp
    from app.blueprints.agendamentos import agendamentos_bp
    from app.blueprints.api import api_bp
    from app.blueprints.whatsapp import whatsapp_bp
    from app.blueprints.conversas import conversas_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(painel_bp)
    app.register_blueprint(servicos_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(disponibilidade_bp)
    app.register_blueprint(agendamentos_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(conversas_bp)
    # API é autenticada por X-API-Key (sem cookie de sessão), então CSRF não se aplica
    csrf.exempt(api_bp)

    from app.cli import register_commands

    register_commands(app)

    @app.context_processor
    def inject_sidebar_user():
        try:
            return {"sidebar_user": get_current_user()}
        except Exception:
            return {"sidebar_user": None}

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.route("/")
    def hello():
        return {"status": "ok", "service": "agenda-saas"}

    return app
