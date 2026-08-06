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
    # CSRF do JWT em cookie fica desligado por enquanto: painel é forms Jinja
    # server-rendered, não SPA. Revisar na etapa de polimento (adicionar
    # Flask-WTF CSRFProtect nos forms em vez do double-submit do JWT).
    JWT_COOKIE_CSRF_PROTECT = False
