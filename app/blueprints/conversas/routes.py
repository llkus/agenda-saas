from flask import Blueprint, abort, render_template
from flask_jwt_extended import get_current_user, jwt_required
from sqlalchemy import func

from app.extensions import db
from app.models import Cliente, Mensagem

conversas_bp = Blueprint("conversas", __name__, url_prefix="/painel/conversas")


@conversas_bp.route("/")
@jwt_required()
def listar():
    user = get_current_user()

    ultima_por_telefone = (
        db.session.query(Mensagem.telefone, func.max(Mensagem.criado_em).label("ultima"))
        .filter(Mensagem.tenant_id == user.tenant_id)
        .group_by(Mensagem.telefone)
        .subquery()
    )

    ultimas_mensagens = (
        db.session.query(Mensagem)
        .join(
            ultima_por_telefone,
            (Mensagem.telefone == ultima_por_telefone.c.telefone)
            & (Mensagem.criado_em == ultima_por_telefone.c.ultima),
        )
        .filter(Mensagem.tenant_id == user.tenant_id)
        .order_by(ultima_por_telefone.c.ultima.desc())
        .all()
    )

    return render_template("conversas/list.html", ultimas_mensagens=ultimas_mensagens)


@conversas_bp.route("/<telefone>")
@jwt_required()
def thread(telefone):
    user = get_current_user()

    mensagens = (
        Mensagem.query.filter_by(tenant_id=user.tenant_id, telefone=telefone)
        .order_by(Mensagem.criado_em.asc())
        .all()
    )
    if not mensagens:
        abort(404)

    cliente = Cliente.query.filter_by(tenant_id=user.tenant_id, telefone=telefone).first()

    return render_template(
        "conversas/thread.html", mensagens=mensagens, telefone=telefone, cliente=cliente
    )
