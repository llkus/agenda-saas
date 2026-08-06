from datetime import date, datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_jwt_extended import get_current_user, jwt_required

from app.extensions import db
from app.models import Agendamento, Cliente, Servico, StatusAgendamento
from app.utils.agenda import horarios_disponiveis

agendamentos_bp = Blueprint("agendamentos", __name__, url_prefix="/painel/agendamentos")


def _parse_data(data_str, padrao=None):
    try:
        return datetime.strptime(data_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return padrao


@agendamentos_bp.route("/")
@jwt_required()
def listar():
    user = get_current_user()
    dia = _parse_data(request.args.get("data"), padrao=date.today())

    inicio_dia = datetime.combine(dia, datetime.min.time())
    fim_dia = datetime.combine(dia, datetime.max.time())

    agendamentos = (
        Agendamento.query.filter(
            Agendamento.tenant_id == user.tenant_id,
            Agendamento.data_hora_inicio >= inicio_dia,
            Agendamento.data_hora_inicio <= fim_dia,
        )
        .order_by(Agendamento.data_hora_inicio)
        .all()
    )
    return render_template(
        "agendamentos/list.html",
        agendamentos=agendamentos,
        dia=dia,
        dia_anterior=dia - timedelta(days=1),
        dia_seguinte=dia + timedelta(days=1),
        StatusAgendamento=StatusAgendamento,
    )


@agendamentos_bp.route("/horarios-disponiveis")
@jwt_required()
def horarios_disponiveis_endpoint():
    user = get_current_user()
    servico_id = request.args.get("servico_id", type=int)
    dia = _parse_data(request.args.get("data"))

    if not servico_id or not dia:
        return jsonify([])

    horarios = horarios_disponiveis(user.tenant_id, servico_id, dia)
    return jsonify([h.strftime("%H:%M") for h in horarios])


@agendamentos_bp.route("/novo", methods=["GET", "POST"])
@jwt_required()
def novo():
    user = get_current_user()
    clientes = Cliente.query.filter_by(tenant_id=user.tenant_id).order_by(Cliente.nome).all()
    servicos = Servico.query.filter_by(tenant_id=user.tenant_id, ativo=True).order_by(Servico.nome).all()

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id", type=int)
        servico_id = request.form.get("servico_id", type=int)
        data_str = request.form.get("data", "")
        horario_str = request.form.get("horario", "")

        erros = []
        cliente = Cliente.query.filter_by(id=cliente_id, tenant_id=user.tenant_id).first()
        servico = Servico.query.filter_by(id=servico_id, tenant_id=user.tenant_id, ativo=True).first()

        if not cliente:
            erros.append("Cliente inválido.")
        if not servico:
            erros.append("Serviço inválido.")

        dia = _parse_data(data_str)
        hora = None
        if not dia:
            erros.append("Data inválida.")
        try:
            hora = datetime.strptime(horario_str, "%H:%M").time()
        except ValueError:
            erros.append("Horário inválido.")

        if not erros:
            disponiveis = horarios_disponiveis(user.tenant_id, servico.id, dia)
            if hora not in disponiveis:
                erros.append("Esse horário não está mais disponível. Escolha outro.")

        if erros:
            for erro in erros:
                flash(erro, "error")
            return render_template(
                "agendamentos/form.html", clientes=clientes, servicos=servicos, form=request.form
            )

        inicio = datetime.combine(dia, hora)
        fim = inicio + timedelta(minutes=servico.duracao_min)

        agendamento = Agendamento(
            tenant_id=user.tenant_id,
            cliente_id=cliente.id,
            servico_id=servico.id,
            data_hora_inicio=inicio,
            data_hora_fim=fim,
            valor=servico.preco,
            status=StatusAgendamento.A_CONFIRMAR,
        )
        db.session.add(agendamento)
        db.session.commit()
        flash("Agendamento criado.", "success")
        return redirect(url_for("agendamentos.listar", data=dia.isoformat()))

    return render_template("agendamentos/form.html", clientes=clientes, servicos=servicos, form={})


@agendamentos_bp.route("/<int:agendamento_id>/status", methods=["POST"])
@jwt_required()
def alterar_status(agendamento_id):
    user = get_current_user()
    agendamento = Agendamento.query.filter_by(id=agendamento_id, tenant_id=user.tenant_id).first_or_404()
    dia_redirect = agendamento.data_hora_inicio.date().isoformat()

    try:
        agendamento.status = StatusAgendamento(request.form.get("status", ""))
    except ValueError:
        flash("Status inválido.", "error")
        return redirect(url_for("agendamentos.listar", data=dia_redirect))

    db.session.commit()
    flash("Status atualizado.", "success")
    return redirect(url_for("agendamentos.listar", data=dia_redirect))
