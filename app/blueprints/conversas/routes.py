from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import get_current_user, jwt_required
from sqlalchemy import func

from app.extensions import db
from app.models import Cliente, ConversaEstado, Mensagem, ModoConversa, RemetenteMensagem
from app.utils.evolution import enviar_mensagem, status_conexao

conversas_bp = Blueprint("conversas", __name__, url_prefix="/painel/conversas")


def _estado(tenant_id: int, telefone: str) -> ConversaEstado:
    estado = ConversaEstado.query.filter_by(tenant_id=tenant_id, telefone=telefone).first()
    if not estado:
        estado = ConversaEstado(tenant_id=tenant_id, telefone=telefone, modo=ModoConversa.BOT)
        db.session.add(estado)
        db.session.commit()
    return estado


@conversas_bp.route("/")
@jwt_required()
def listar():
    if status_conexao().get("state") != "open":
        return render_template("conversas/conectar.html")

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

    estados = {
        e.telefone: e.modo
        for e in ConversaEstado.query.filter_by(tenant_id=user.tenant_id).all()
    }

    return render_template(
        "conversas/list.html", ultimas_mensagens=ultimas_mensagens, estados=estados, ModoConversa=ModoConversa
    )


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
    estado = _estado(user.tenant_id, telefone)

    return render_template(
        "conversas/thread.html",
        mensagens=mensagens,
        telefone=telefone,
        cliente=cliente,
        estado=estado,
        ModoConversa=ModoConversa,
    )


@conversas_bp.route("/<telefone>/enviar", methods=["POST"])
@jwt_required()
def enviar(telefone):
    user = get_current_user()
    texto = (request.form.get("texto") or "").strip()

    if not texto:
        flash("Escreva uma mensagem.", "error")
        return redirect(url_for("conversas.thread", telefone=telefone))

    cliente = Cliente.query.filter_by(tenant_id=user.tenant_id, telefone=telefone).first()

    enviado = enviar_mensagem(telefone, texto)
    if not enviado:
        flash("Não foi possível enviar pelo WhatsApp agora, mas a mensagem foi registrada.", "error")

    db.session.add(
        Mensagem(
            tenant_id=user.tenant_id,
            cliente_id=cliente.id if cliente else None,
            telefone=telefone,
            remetente=RemetenteMensagem.EQUIPE,
            texto=texto,
        )
    )

    estado = _estado(user.tenant_id, telefone)
    estado.modo = ModoConversa.HUMANO
    db.session.commit()

    return redirect(url_for("conversas.thread", telefone=telefone))


@conversas_bp.route("/<telefone>/modo", methods=["POST"])
@jwt_required()
def alternar_modo(telefone):
    user = get_current_user()
    novo_modo = request.form.get("modo", "")

    try:
        modo = ModoConversa(novo_modo)
    except ValueError:
        flash("Modo inválido.", "error")
        return redirect(url_for("conversas.thread", telefone=telefone))

    estado = _estado(user.tenant_id, telefone)
    estado.modo = modo
    db.session.commit()

    flash("Robô voltou a responder." if modo == ModoConversa.BOT else "Conversa assumida pela equipe.", "success")
    return redirect(url_for("conversas.thread", telefone=telefone))
