from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_jwt_extended import get_current_user, jwt_required

from app.extensions import db
from app.models import Disponibilidade

disponibilidade_bp = Blueprint("disponibilidade", __name__, url_prefix="/painel/disponibilidade")

DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


@disponibilidade_bp.route("/")
@jwt_required()
def listar():
    user = get_current_user()
    janelas = (
        Disponibilidade.query.filter_by(tenant_id=user.tenant_id)
        .order_by(Disponibilidade.dia_semana, Disponibilidade.hora_inicio)
        .all()
    )
    return render_template("disponibilidade/list.html", janelas=janelas, dias_semana=DIAS_SEMANA)


@disponibilidade_bp.route("/novo", methods=["GET", "POST"])
@jwt_required()
def novo():
    if request.method == "POST":
        user = get_current_user()
        dia_semana_raw = request.form.get("dia_semana", "")
        hora_inicio_raw = request.form.get("hora_inicio", "")
        hora_fim_raw = request.form.get("hora_fim", "")

        erros = []
        dia_semana = None
        try:
            dia_semana = int(dia_semana_raw)
            if not 0 <= dia_semana <= 6:
                erros.append("Dia da semana inválido.")
        except ValueError:
            erros.append("Dia da semana inválido.")

        hora_inicio = hora_fim = None
        try:
            hora_inicio = datetime.strptime(hora_inicio_raw, "%H:%M").time()
            hora_fim = datetime.strptime(hora_fim_raw, "%H:%M").time()
            if hora_inicio >= hora_fim:
                erros.append("Hora de início deve ser antes da hora de fim.")
        except ValueError:
            erros.append("Horário inválido.")

        if erros:
            for erro in erros:
                flash(erro, "error")
            return render_template("disponibilidade/form.html", dias_semana=DIAS_SEMANA, form=request.form)

        janela = Disponibilidade(
            tenant_id=user.tenant_id,
            dia_semana=dia_semana,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
        )
        db.session.add(janela)
        db.session.commit()
        flash("Horário de disponibilidade criado.", "success")
        return redirect(url_for("disponibilidade.listar"))

    return render_template("disponibilidade/form.html", dias_semana=DIAS_SEMANA, form={})


@disponibilidade_bp.route("/<int:janela_id>/excluir", methods=["POST"])
@jwt_required()
def excluir(janela_id):
    user = get_current_user()
    janela = Disponibilidade.query.filter_by(id=janela_id, tenant_id=user.tenant_id).first_or_404()
    db.session.delete(janela)
    db.session.commit()
    flash("Horário removido.", "success")
    return redirect(url_for("disponibilidade.listar"))
