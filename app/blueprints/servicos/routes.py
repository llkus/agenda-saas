from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_jwt_extended import get_current_user, jwt_required

from app.extensions import db
from app.models import Servico

servicos_bp = Blueprint("servicos", __name__, url_prefix="/painel/servicos")


def _parse_form():
    nome = request.form.get("nome", "").strip()
    duracao_raw = request.form.get("duracao_min", "").strip()
    preco_raw = request.form.get("preco", "").strip()

    erros = []
    if not nome:
        erros.append("Nome é obrigatório.")

    duracao_min = None
    try:
        duracao_min = int(duracao_raw)
        if duracao_min <= 0:
            erros.append("Duração deve ser maior que zero.")
    except ValueError:
        erros.append("Duração inválida.")

    preco = None
    try:
        preco = Decimal(preco_raw.replace(",", "."))
        if preco < 0:
            erros.append("Preço não pode ser negativo.")
    except (InvalidOperation, AttributeError):
        erros.append("Preço inválido.")

    return nome, duracao_min, preco, erros


@servicos_bp.route("/")
@jwt_required()
def listar():
    user = get_current_user()
    servicos = (
        Servico.query.filter_by(tenant_id=user.tenant_id)
        .order_by(Servico.nome)
        .all()
    )
    return render_template("servicos/list.html", servicos=servicos)


@servicos_bp.route("/novo", methods=["GET", "POST"])
@jwt_required()
def novo():
    if request.method == "POST":
        user = get_current_user()
        nome, duracao_min, preco, erros = _parse_form()

        if erros:
            for erro in erros:
                flash(erro, "error")
            return render_template("servicos/form.html", servico=None, form=request.form)

        servico = Servico(
            tenant_id=user.tenant_id,
            nome=nome,
            duracao_min=duracao_min,
            preco=preco,
        )
        db.session.add(servico)
        db.session.commit()
        flash("Serviço criado.", "success")
        return redirect(url_for("servicos.listar"))

    return render_template("servicos/form.html", servico=None, form={})


@servicos_bp.route("/<int:servico_id>/editar", methods=["GET", "POST"])
@jwt_required()
def editar(servico_id):
    user = get_current_user()
    servico = Servico.query.filter_by(id=servico_id, tenant_id=user.tenant_id).first_or_404()

    if request.method == "POST":
        nome, duracao_min, preco, erros = _parse_form()

        if erros:
            for erro in erros:
                flash(erro, "error")
            return render_template("servicos/form.html", servico=servico, form=request.form)

        servico.nome = nome
        servico.duracao_min = duracao_min
        servico.preco = preco
        db.session.commit()
        flash("Serviço atualizado.", "success")
        return redirect(url_for("servicos.listar"))

    return render_template("servicos/form.html", servico=servico, form=None)


@servicos_bp.route("/<int:servico_id>/alternar-status", methods=["POST"])
@jwt_required()
def alternar_status(servico_id):
    user = get_current_user()
    servico = Servico.query.filter_by(id=servico_id, tenant_id=user.tenant_id).first_or_404()
    servico.ativo = not servico.ativo
    db.session.commit()
    flash("Serviço ativado." if servico.ativo else "Serviço desativado.", "success")
    return redirect(url_for("servicos.listar"))
