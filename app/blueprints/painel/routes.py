from datetime import date, datetime, timedelta

from flask import Blueprint, render_template
from flask_jwt_extended import get_current_user, jwt_required
from sqlalchemy import func

from app.extensions import db
from app.models import Agendamento, Cliente, Servico, StatusAgendamento

painel_bp = Blueprint("painel", __name__, url_prefix="/painel")


@painel_bp.route("/")
@jwt_required()
def index():
    user = get_current_user()
    tenant_id = user.tenant_id
    hoje = date.today()

    inicio_hoje = datetime.combine(hoje, datetime.min.time())
    fim_hoje = datetime.combine(hoje, datetime.max.time())

    agendamentos_hoje = (
        Agendamento.query.filter(
            Agendamento.tenant_id == tenant_id,
            Agendamento.data_hora_inicio >= inicio_hoje,
            Agendamento.data_hora_inicio <= fim_hoje,
            Agendamento.status != StatusAgendamento.CANCELADO,
        )
        .order_by(Agendamento.data_hora_inicio)
        .all()
    )

    inicio_mes = hoje.replace(day=1)
    if inicio_mes.month == 12:
        fim_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1) - timedelta(days=1)
    else:
        fim_mes = inicio_mes.replace(month=inicio_mes.month + 1) - timedelta(days=1)
    inicio_mes_dt = datetime.combine(inicio_mes, datetime.min.time())
    fim_mes_dt = datetime.combine(fim_mes, datetime.max.time())

    faturamento_mes = (
        db.session.query(func.coalesce(func.sum(Agendamento.valor), 0))
        .filter(
            Agendamento.tenant_id == tenant_id,
            Agendamento.status == StatusAgendamento.REALIZADO,
            Agendamento.data_hora_inicio >= inicio_mes_dt,
            Agendamento.data_hora_inicio <= fim_mes_dt,
        )
        .scalar()
    )

    fim_semana_dt = datetime.combine(hoje + timedelta(days=7), datetime.max.time())
    previsto_semana = (
        db.session.query(func.coalesce(func.sum(Agendamento.valor), 0))
        .filter(
            Agendamento.tenant_id == tenant_id,
            Agendamento.status.in_([StatusAgendamento.A_CONFIRMAR, StatusAgendamento.CONFIRMADO]),
            Agendamento.data_hora_inicio >= inicio_hoje,
            Agendamento.data_hora_inicio <= fim_semana_dt,
        )
        .scalar()
    )

    total_clientes = Cliente.query.filter_by(tenant_id=tenant_id).count()

    top_servicos = (
        db.session.query(Servico.nome, func.count(Agendamento.id).label("qtd"))
        .join(Agendamento, Agendamento.servico_id == Servico.id)
        .filter(
            Agendamento.tenant_id == tenant_id,
            Agendamento.status != StatusAgendamento.CANCELADO,
            Agendamento.data_hora_inicio >= inicio_mes_dt,
            Agendamento.data_hora_inicio <= fim_mes_dt,
        )
        .group_by(Servico.nome)
        .order_by(func.count(Agendamento.id).desc())
        .limit(5)
        .all()
    )

    return render_template(
        "painel/index.html",
        user=user,
        agendamentos_hoje=agendamentos_hoje,
        faturamento_mes=faturamento_mes,
        previsto_semana=previsto_semana,
        total_clientes=total_clientes,
        top_servicos=top_servicos,
        hoje=hoje,
    )
