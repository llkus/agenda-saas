from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_jwt_extended import get_current_user, jwt_required

from app.extensions import db
from app.utils.dates import mes_completo_pt
from app.models import (
    Agendamento,
    ContaFinanceira,
    ContaPagar,
    FormaPagamento,
    GrupoDRE,
    LancamentoFinanceiro,
    OrigemLancamento,
    PlanoDeContas,
    StatusAgendamento,
    TipoLancamento,
)
from app.utils.financeiro import (
    GRUPOS_ORDEM,
    demonstrativo,
    mes_a_mes,
    projecao_contas_pagar,
    resumo_periodo,
    saldos_contas,
    seed_plano_de_contas,
)

financeiro_bp = Blueprint("financeiro", __name__, url_prefix="/painel/financeiro")


def _garantir_setup(tenant_id: int):
    seed_plano_de_contas(tenant_id)


def _conta_padrao(tenant_id: int) -> ContaFinanceira:
    return ContaFinanceira.query.filter_by(tenant_id=tenant_id).order_by(ContaFinanceira.id).first()


def _categoria_servicos(tenant_id: int) -> PlanoDeContas:
    return PlanoDeContas.query.filter_by(tenant_id=tenant_id, sistema=True, grupo=GrupoDRE.RECEITA).first()


def _parse_decimal(valor: str) -> Decimal | None:
    try:
        return Decimal(valor.replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def _add_months(d: date, meses: int) -> date:
    total = d.month - 1 + meses
    ano = d.year + total // 12
    mes = total % 12 + 1
    dia = min(d.day, monthrange(ano, mes)[1])
    return date(ano, mes, dia)


# ------------------------------------------------------------------ #
# Caixa
# ------------------------------------------------------------------ #


@financeiro_bp.route("/caixa")
@jwt_required()
def caixa():
    user = get_current_user()
    _garantir_setup(user.tenant_id)
    aba = request.args.get("aba", "receber")
    hoje = date.today()

    a_receber = (
        Agendamento.query.filter(
            Agendamento.tenant_id == user.tenant_id,
            Agendamento.status == StatusAgendamento.REALIZADO,
        )
        .outerjoin(
            LancamentoFinanceiro,
            (LancamentoFinanceiro.origem == OrigemLancamento.AGENDAMENTO)
            & (LancamentoFinanceiro.origem_id == Agendamento.id),
        )
        .filter(LancamentoFinanceiro.id.is_(None))
        .order_by(Agendamento.data_hora_inicio.desc())
        .all()
    )

    contas_financeiras = ContaFinanceira.query.filter_by(tenant_id=user.tenant_id).all()
    formas = list(FormaPagamento)

    resumo_hoje = resumo_periodo(user.tenant_id, hoje, hoje)

    contas_pagar_abertas = (
        ContaPagar.query.filter_by(tenant_id=user.tenant_id, pago=False)
        .order_by(ContaPagar.vencimento)
        .all()
    )
    projecao = projecao_contas_pagar(user.tenant_id, 6)
    categorias = PlanoDeContas.query.filter_by(tenant_id=user.tenant_id).order_by(PlanoDeContas.nome).all()

    extrato_dias = request.args.get("dias", type=int) or 30
    inicio_extrato = hoje - timedelta(days=extrato_dias)
    lancamentos = (
        LancamentoFinanceiro.query.filter(
            LancamentoFinanceiro.tenant_id == user.tenant_id,
            LancamentoFinanceiro.data >= inicio_extrato,
        )
        .order_by(LancamentoFinanceiro.data.desc(), LancamentoFinanceiro.criado_em.desc())
        .all()
    )

    return render_template(
        "financeiro/caixa.html",
        aba=aba,
        hoje=hoje,
        a_receber=a_receber,
        contas_financeiras=contas_financeiras,
        formas=formas,
        resumo_hoje=resumo_hoje,
        contas_pagar_abertas=contas_pagar_abertas,
        projecao=projecao,
        categorias=categorias,
        lancamentos=lancamentos,
        extrato_dias=extrato_dias,
        saldos=saldos_contas(user.tenant_id),
        GrupoDRE=GrupoDRE,
        TipoLancamento=TipoLancamento,
        OrigemLancamento=OrigemLancamento,
    )


@financeiro_bp.route("/agendamentos/<int:agendamento_id>/registrar-pagamento", methods=["POST"])
@jwt_required()
def registrar_pagamento(agendamento_id):
    user = get_current_user()
    agendamento = Agendamento.query.filter_by(id=agendamento_id, tenant_id=user.tenant_id).first_or_404()

    conta_id = request.form.get("conta_id", type=int)
    forma_str = request.form.get("forma", "")
    conta = ContaFinanceira.query.filter_by(id=conta_id, tenant_id=user.tenant_id).first()
    try:
        forma = FormaPagamento(forma_str)
    except ValueError:
        forma = FormaPagamento.OUTRO

    if not conta:
        flash("Escolha uma conta válida.", "error")
        return redirect(url_for("financeiro.caixa"))

    categoria = _categoria_servicos(user.tenant_id)
    db.session.add(
        LancamentoFinanceiro(
            tenant_id=user.tenant_id,
            conta_id=conta.id,
            categoria_id=categoria.id,
            tipo=TipoLancamento.ENTRADA,
            forma=forma,
            valor=agendamento.valor,
            data=agendamento.data_hora_inicio.date(),
            descricao=f"{agendamento.servico.nome} — {agendamento.cliente.nome}",
            origem=OrigemLancamento.AGENDAMENTO,
            origem_id=agendamento.id,
        )
    )
    db.session.commit()
    flash("Pagamento registrado.", "success")
    return redirect(url_for("financeiro.caixa"))


# ------------------------------------------------------------------ #
# Contas a pagar
# ------------------------------------------------------------------ #


@financeiro_bp.route("/contas-pagar/nova", methods=["POST"])
@jwt_required()
def nova_conta_pagar():
    user = get_current_user()
    descricao = (request.form.get("descricao") or "").strip()
    categoria_id = request.form.get("categoria_id", type=int)
    valor = _parse_decimal(request.form.get("valor", ""))
    vencimento_str = request.form.get("vencimento", "")
    recorrente = request.form.get("recorrente_mensal") == "on"
    parcelas = request.form.get("parcelas", type=int) or 1

    categoria = PlanoDeContas.query.filter_by(id=categoria_id, tenant_id=user.tenant_id).first()
    try:
        vencimento = datetime.strptime(vencimento_str, "%Y-%m-%d").date()
    except ValueError:
        vencimento = None

    if not descricao or not categoria or not valor or valor <= 0 or not vencimento:
        flash("Preencha os campos da conta corretamente.", "error")
        return redirect(url_for("financeiro.caixa", aba="contas"))

    if parcelas > 1:
        for p in range(parcelas):
            db.session.add(
                ContaPagar(
                    tenant_id=user.tenant_id,
                    categoria_id=categoria.id,
                    descricao=descricao,
                    valor=valor,
                    vencimento=_add_months(vencimento, p),
                    parcela_atual=p + 1,
                    parcelas_total=parcelas,
                )
            )
    else:
        db.session.add(
            ContaPagar(
                tenant_id=user.tenant_id,
                categoria_id=categoria.id,
                descricao=descricao,
                valor=valor,
                vencimento=vencimento,
                recorrente_mensal=recorrente,
            )
        )

    db.session.commit()
    flash("Conta a pagar cadastrada.", "success")
    return redirect(url_for("financeiro.caixa", aba="contas"))


@financeiro_bp.route("/contas-pagar/<int:conta_id>/pagar", methods=["POST"])
@jwt_required()
def pagar_conta(conta_id):
    user = get_current_user()
    conta_pagar = ContaPagar.query.filter_by(id=conta_id, tenant_id=user.tenant_id).first_or_404()
    conta_financeira = _conta_padrao(user.tenant_id)

    conta_pagar.pago = True
    conta_pagar.pago_em = date.today()

    db.session.add(
        LancamentoFinanceiro(
            tenant_id=user.tenant_id,
            conta_id=conta_financeira.id,
            categoria_id=conta_pagar.categoria_id,
            tipo=TipoLancamento.SAIDA,
            valor=conta_pagar.valor,
            data=date.today(),
            descricao=conta_pagar.descricao,
            origem=OrigemLancamento.CONTA_PAGAR,
            origem_id=conta_pagar.id,
        )
    )

    if conta_pagar.recorrente_mensal:
        db.session.add(
            ContaPagar(
                tenant_id=user.tenant_id,
                categoria_id=conta_pagar.categoria_id,
                descricao=conta_pagar.descricao,
                valor=conta_pagar.valor,
                vencimento=_add_months(conta_pagar.vencimento, 1),
                recorrente_mensal=True,
            )
        )

    db.session.commit()
    flash("Conta paga.", "success")
    return redirect(url_for("financeiro.caixa", aba="contas"))


@financeiro_bp.route("/contas-pagar/<int:conta_id>/excluir", methods=["POST"])
@jwt_required()
def excluir_conta_pagar(conta_id):
    user = get_current_user()
    conta_pagar = ContaPagar.query.filter_by(id=conta_id, tenant_id=user.tenant_id).first_or_404()
    db.session.delete(conta_pagar)
    db.session.commit()
    flash("Conta removida.", "success")
    return redirect(url_for("financeiro.caixa", aba="contas"))


# ------------------------------------------------------------------ #
# Extrato (lançamento manual)
# ------------------------------------------------------------------ #


@financeiro_bp.route("/extrato/lancamento", methods=["POST"])
@jwt_required()
def novo_lancamento():
    user = get_current_user()
    conta_id = request.form.get("conta_id", type=int)
    categoria_id = request.form.get("categoria_id", type=int)
    tipo_str = request.form.get("tipo", "")
    valor = _parse_decimal(request.form.get("valor", ""))
    descricao = (request.form.get("descricao") or "").strip()
    data_str = request.form.get("data", "")

    conta = ContaFinanceira.query.filter_by(id=conta_id, tenant_id=user.tenant_id).first()
    categoria = PlanoDeContas.query.filter_by(id=categoria_id, tenant_id=user.tenant_id).first()
    try:
        tipo = TipoLancamento(tipo_str)
    except ValueError:
        tipo = None
    try:
        data_lanc = datetime.strptime(data_str, "%Y-%m-%d").date()
    except ValueError:
        data_lanc = None

    if not (conta and categoria and tipo and valor and valor > 0 and descricao and data_lanc):
        flash("Preencha o lançamento corretamente.", "error")
        return redirect(url_for("financeiro.caixa", aba="extrato"))

    db.session.add(
        LancamentoFinanceiro(
            tenant_id=user.tenant_id,
            conta_id=conta.id,
            categoria_id=categoria.id,
            tipo=tipo,
            valor=valor,
            data=data_lanc,
            descricao=descricao,
            origem=OrigemLancamento.MANUAL,
        )
    )
    db.session.commit()
    flash("Lançamento registrado.", "success")
    return redirect(url_for("financeiro.caixa", aba="extrato"))


@financeiro_bp.route("/extrato/<int:lancamento_id>/excluir", methods=["POST"])
@jwt_required()
def excluir_lancamento(lancamento_id):
    user = get_current_user()
    lancamento = LancamentoFinanceiro.query.filter_by(id=lancamento_id, tenant_id=user.tenant_id).first_or_404()
    if lancamento.origem != OrigemLancamento.MANUAL:
        flash("Só lançamentos manuais podem ser excluídos.", "error")
        return redirect(url_for("financeiro.caixa", aba="extrato"))
    db.session.delete(lancamento)
    db.session.commit()
    flash("Lançamento excluído.", "success")
    return redirect(url_for("financeiro.caixa", aba="extrato"))


# ------------------------------------------------------------------ #
# Plano de contas
# ------------------------------------------------------------------ #


@financeiro_bp.route("/plano-de-contas")
@jwt_required()
def plano_de_contas():
    user = get_current_user()
    _garantir_setup(user.tenant_id)
    categorias = PlanoDeContas.query.filter_by(tenant_id=user.tenant_id).order_by(PlanoDeContas.grupo, PlanoDeContas.nome).all()
    grupos = {g: [c for c in categorias if c.grupo == g] for g, _, _ in GRUPOS_ORDEM}
    return render_template("financeiro/plano_de_contas.html", grupos=grupos, grupos_ordem=GRUPOS_ORDEM)


@financeiro_bp.route("/plano-de-contas/nova", methods=["POST"])
@jwt_required()
def nova_categoria():
    user = get_current_user()
    nome = (request.form.get("nome") or "").strip()
    grupo_str = request.form.get("grupo", "")
    nota = (request.form.get("nota") or "").strip()

    try:
        grupo = GrupoDRE(grupo_str)
    except ValueError:
        grupo = None

    if not nome or not grupo:
        flash("Preencha nome e grupo.", "error")
        return redirect(url_for("financeiro.plano_de_contas"))

    db.session.add(PlanoDeContas(tenant_id=user.tenant_id, nome=nome, grupo=grupo, nota=nota))
    db.session.commit()
    flash("Conta criada.", "success")
    return redirect(url_for("financeiro.plano_de_contas"))


@financeiro_bp.route("/plano-de-contas/<int:categoria_id>/excluir", methods=["POST"])
@jwt_required()
def excluir_categoria(categoria_id):
    user = get_current_user()
    categoria = PlanoDeContas.query.filter_by(id=categoria_id, tenant_id=user.tenant_id).first_or_404()
    if categoria.sistema:
        flash("Esta conta é usada pelo sistema e não pode ser removida.", "error")
        return redirect(url_for("financeiro.plano_de_contas"))
    if categoria.lancamentos or categoria.contas_pagar:
        flash("Esta conta tem lançamentos vinculados e não pode ser removida.", "error")
        return redirect(url_for("financeiro.plano_de_contas"))
    db.session.delete(categoria)
    db.session.commit()
    flash("Conta removida.", "success")
    return redirect(url_for("financeiro.plano_de_contas"))


# ------------------------------------------------------------------ #
# Demonstrativos e mês a mês
# ------------------------------------------------------------------ #


@financeiro_bp.route("/demonstrativos")
@jwt_required()
def demonstrativos():
    user = get_current_user()
    _garantir_setup(user.tenant_id)
    mes_str = request.args.get("mes", "")
    try:
        ref = datetime.strptime(mes_str, "%Y-%m").date()
    except ValueError:
        hoje = date.today()
        ref = date(hoje.year, hoje.month, 1)

    if ref.month == 12:
        fim_mes = date(ref.year, 12, 31)
    else:
        fim_mes = date(ref.year, ref.month + 1, 1) - timedelta(days=1)
    fim_mes = min(fim_mes, date.today()) if ref.year == date.today().year and ref.month == date.today().month else fim_mes

    dre = demonstrativo(user.tenant_id, ref, fim_mes)
    return render_template(
        "financeiro/demonstrativos.html", dre=dre, mes_ref=ref, rotulo_periodo=mes_completo_pt(ref)
    )


@financeiro_bp.route("/mes-a-mes")
@jwt_required()
def mes_a_mes_view():
    user = get_current_user()
    _garantir_setup(user.tenant_id)
    dados = mes_a_mes(user.tenant_id, 6)
    return render_template("financeiro/mes_a_mes.html", dados=dados)
