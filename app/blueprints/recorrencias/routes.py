from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import get_current_user, jwt_required

from app.extensions import db
from app.models import Cliente, Recorrencia, Servico
from app.utils.recorrencia import gerar_agendamentos, planejar_ocorrencias

recorrencias_bp = Blueprint("recorrencias", __name__, url_prefix="/painel/recorrencias")

DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


@recorrencias_bp.route("/")
@jwt_required()
def listar():
    user = get_current_user()
    recorrencias = (
        Recorrencia.query.filter_by(tenant_id=user.tenant_id).order_by(Recorrencia.created_at.desc()).all()
    )
    return render_template("recorrencias/list.html", recorrencias=recorrencias, dias_semana=DIAS_SEMANA)


@recorrencias_bp.route("/novo", methods=["GET", "POST"])
@jwt_required()
def novo():
    user = get_current_user()
    clientes = Cliente.query.filter_by(tenant_id=user.tenant_id).order_by(Cliente.nome).all()
    servicos = Servico.query.filter_by(tenant_id=user.tenant_id, ativo=True).order_by(Servico.nome).all()

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id", type=int)
        servico_id = request.form.get("servico_id", type=int)
        dia_semana = request.form.get("dia_semana", type=int)
        hora_str = request.form.get("hora", "")
        intervalo = request.form.get("intervalo_semanas", type=int) or 1

        cliente = Cliente.query.filter_by(id=cliente_id, tenant_id=user.tenant_id).first()
        servico = Servico.query.filter_by(id=servico_id, tenant_id=user.tenant_id, ativo=True).first()

        erros = []
        if not cliente:
            erros.append("Cliente inválido.")
        if not servico:
            erros.append("Serviço inválido.")
        if dia_semana is None or not (0 <= dia_semana <= 6):
            erros.append("Dia da semana inválido.")
        try:
            hora = datetime.strptime(hora_str, "%H:%M").time()
        except ValueError:
            hora = None
            erros.append("Horário inválido.")

        if erros:
            for erro in erros:
                flash(erro, "error")
            return render_template(
                "recorrencias/form.html", clientes=clientes, servicos=servicos, dias_semana=DIAS_SEMANA, form=request.form
            )

        recorrencia = Recorrencia(
            tenant_id=user.tenant_id,
            cliente_id=cliente.id,
            servico_id=servico.id,
            dia_semana=dia_semana,
            hora=hora,
            intervalo_semanas=intervalo,
        )
        db.session.add(recorrencia)
        db.session.commit()
        flash("Cliente fixo cadastrado.", "success")
        return redirect(url_for("recorrencias.listar"))

    return render_template(
        "recorrencias/form.html", clientes=clientes, servicos=servicos, dias_semana=DIAS_SEMANA, form={}
    )


@recorrencias_bp.route("/previa")
@jwt_required()
def previa():
    """Prévia via AJAX a partir dos campos do form (sem salvar nada ainda)."""
    user = get_current_user()
    cliente_id = request.args.get("cliente_id", type=int)
    servico_id = request.args.get("servico_id", type=int)
    dia_semana = request.args.get("dia_semana", type=int)
    hora_str = request.args.get("hora", "")
    intervalo = request.args.get("intervalo_semanas", type=int) or 1

    if cliente_id is None or servico_id is None or dia_semana is None:
        return jsonify([])
    try:
        hora = datetime.strptime(hora_str, "%H:%M").time()
    except ValueError:
        return jsonify([])

    rascunho = Recorrencia(
        tenant_id=user.tenant_id,
        cliente_id=cliente_id,
        servico_id=servico_id,
        dia_semana=dia_semana,
        hora=hora,
        intervalo_semanas=intervalo,
        gerado_ate=None,
    )
    ocorrencias = planejar_ocorrencias(rascunho, dias_a_frente=60)[:6]
    return jsonify(
        [
            {"data": oc.data.isoformat(), "cabe": oc.cabe, "impedimento": oc.impedimento}
            for oc in ocorrencias
        ]
    )


@recorrencias_bp.route("/<int:recorrencia_id>/gerar", methods=["POST"])
@jwt_required()
def gerar(recorrencia_id):
    user = get_current_user()
    recorrencia = Recorrencia.query.filter_by(id=recorrencia_id, tenant_id=user.tenant_id).first_or_404()

    if not recorrencia.ativo:
        flash("Essa regra está pausada. Reative antes de gerar.", "error")
        return redirect(url_for("recorrencias.listar"))

    criados = gerar_agendamentos(recorrencia, dias_a_frente=60)
    flash(f"{criados} agendamento(s) gerado(s) para os próximos 60 dias.", "success")
    return redirect(url_for("recorrencias.listar"))


@recorrencias_bp.route("/<int:recorrencia_id>/alternar", methods=["POST"])
@jwt_required()
def alternar(recorrencia_id):
    user = get_current_user()
    recorrencia = Recorrencia.query.filter_by(id=recorrencia_id, tenant_id=user.tenant_id).first_or_404()
    recorrencia.ativo = not recorrencia.ativo
    db.session.commit()
    flash("Regra pausada." if not recorrencia.ativo else "Regra reativada.", "success")
    return redirect(url_for("recorrencias.listar"))


@recorrencias_bp.route("/<int:recorrencia_id>/excluir", methods=["POST"])
@jwt_required()
def excluir(recorrencia_id):
    user = get_current_user()
    recorrencia = Recorrencia.query.filter_by(id=recorrencia_id, tenant_id=user.tenant_id).first_or_404()
    db.session.delete(recorrencia)
    db.session.commit()
    flash("Cliente fixo removido.", "success")
    return redirect(url_for("recorrencias.listar"))
