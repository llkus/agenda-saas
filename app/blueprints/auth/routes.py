from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies

from app.extensions import limiter
from app.models import User
from app.utils.security import verificar_senha

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        user = User.query.filter_by(email=email).first()
        if user and verificar_senha(senha, user.senha_hash):
            resp = redirect(url_for("painel.index"))
            token = create_access_token(identity=user)
            set_access_cookies(resp, token)
            return resp

        flash("Email ou senha inválidos.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    resp = redirect(url_for("auth.login"))
    unset_jwt_cookies(resp)
    return resp
