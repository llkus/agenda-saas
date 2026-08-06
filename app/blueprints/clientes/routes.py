from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_jwt_extended import get_current_user, jwt_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Cliente

clientes_bp = Blueprint("clientes", __name__, url_prefix="/painel/clientes")


def _parse_form():
    nome = request.form.get("nome", "").strip()
    telefone = request.form.get("telefone", "").strip()

    erros = []
    if not nome:
        erros.append("Nome é obrigatório.")
    if not telefone:
        erros.append("Telefone é obrigatório.")

    return nome, telefone, erros


@clientes_bp.route("/")
@jwt_required()
def listar():
    user = get_current_user()
    clientes = (
        Cliente.query.filter_by(tenant_id=user.tenant_id)
        .order_by(Cliente.nome)
        .all()
    )
    return render_template("clientes/list.html", clientes=clientes)


@clientes_bp.route("/novo", methods=["GET", "POST"])
@jwt_required()
def novo():
    if request.method == "POST":
        user = get_current_user()
        nome, telefone, erros = _parse_form()

        if erros:
            for erro in erros:
                flash(erro, "error")
            return render_template("clientes/form.html", cliente=None, form=request.form)

        cliente = Cliente(tenant_id=user.tenant_id, nome=nome, telefone=telefone)
        db.session.add(cliente)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Já existe um cliente com esse telefone.", "error")
            return render_template("clientes/form.html", cliente=None, form=request.form)

        flash("Cliente criado.", "success")
        return redirect(url_for("clientes.listar"))

    return render_template("clientes/form.html", cliente=None, form={})


@clientes_bp.route("/<int:cliente_id>/editar", methods=["GET", "POST"])
@jwt_required()
def editar(cliente_id):
    user = get_current_user()
    cliente = Cliente.query.filter_by(id=cliente_id, tenant_id=user.tenant_id).first_or_404()

    if request.method == "POST":
        nome, telefone, erros = _parse_form()

        if erros:
            for erro in erros:
                flash(erro, "error")
            return render_template("clientes/form.html", cliente=cliente, form=request.form)

        cliente.nome = nome
        cliente.telefone = telefone
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Já existe um cliente com esse telefone.", "error")
            return render_template("clientes/form.html", cliente=cliente, form=request.form)

        flash("Cliente atualizado.", "success")
        return redirect(url_for("clientes.listar"))

    return render_template("clientes/form.html", cliente=cliente, form=None)


@clientes_bp.route("/<int:cliente_id>/excluir", methods=["POST"])
@jwt_required()
def excluir(cliente_id):
    user = get_current_user()
    cliente = Cliente.query.filter_by(id=cliente_id, tenant_id=user.tenant_id).first_or_404()
    db.session.delete(cliente)
    db.session.commit()
    flash("Cliente excluído.", "success")
    return redirect(url_for("clientes.listar"))
