from flask import Blueprint, render_template
from flask_jwt_extended import jwt_required, get_current_user

painel_bp = Blueprint("painel", __name__, url_prefix="/painel")


@painel_bp.route("/")
@jwt_required()
def index():
    # Stub temporário só para validar a Etapa 3 (auth). O dashboard real
    # entra na Etapa 9.
    user = get_current_user()
    return render_template("painel/index.html", user=user)
