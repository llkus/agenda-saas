import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt")

    # Sessão do painel via JWT em cookie HttpOnly (não via header Authorization)
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 8  # 8 horas
    # CSRF do JWT em cookie fica desligado: usamos Flask-WTF CSRFProtect
    # (baseado na sessão Flask) nos forms do painel em vez do double-submit
    # do próprio JWT — mais simples pra forms Jinja server-rendered.
    JWT_COOKIE_CSRF_PROTECT = False

    EVOLUTION_API_URL = os.environ.get("EVOLUTION_API_URL", "")
    EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")
    EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE", "")
