from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func

from app.extensions import db
from app.utils.dates import mes_abreviado_pt
from app.models import (
    Caixa,
    CaixaMovimento,
    ContaFinanceira,
    ContaPagar,
    FormaPagamento,
    GrupoDRE,
    LancamentoFinanceiro,
    PlanoDeContas,
    TipoLancamento,
)

GRUPOS_ORDEM = [
    (GrupoDRE.RECEITA, "Receita de serviços", "+"),
    (GrupoDRE.CUSTO_VARIAVEL, "Custos variáveis", "-"),
    (GrupoDRE.OUTRAS_RECEITAS, "Outras receitas", "+"),
    (GrupoDRE.DESPESA_FIXA, "Despesas fixas", "-"),
    (GrupoDRE.OUTRAS_DESPESAS, "Outras despesas", "-"),
]

CATEGORIAS_PADRAO = [
    ("Serviços", GrupoDRE.RECEITA, "Receita gerada pelos agendamentos realizados", True),
    ("Produtos e insumos", GrupoDRE.CUSTO_VARIAVEL, "Material consumido por atendimento", False),
    ("Taxas de cartão", GrupoDRE.CUSTO_VARIAVEL, "Taxa cobrada pela maquininha", False),
    ("Aluguel", GrupoDRE.DESPESA_FIXA, "", False),
    ("Contas fixas", GrupoDRE.DESPESA_FIXA, "Água, luz, internet", False),
    ("Marketing", GrupoDRE.DESPESA_FIXA, "", False),
    ("Outras receitas", GrupoDRE.OUTRAS_RECEITAS, "", False),
    ("Outras despesas", GrupoDRE.OUTRAS_DESPESAS, "", False),
]


def seed_plano_de_contas(tenant_id: int) -> None:
    if PlanoDeContas.query.filter_by(tenant_id=tenant_id).first():
        return
    for nome, grupo, nota, sistema in CATEGORIAS_PADRAO:
        db.session.add(PlanoDeContas(tenant_id=tenant_id, nome=nome, grupo=grupo, nota=nota, sistema=sistema))
    if not ContaFinanceira.query.filter_by(tenant_id=tenant_id).first():
        db.session.add(ContaFinanceira(tenant_id=tenant_id, nome="Caixa/Banco", saldo_inicial=0))
    db.session.commit()


def _soma(tenant_id: int, tipo: TipoLancamento, conta_id: int | None, inicio: date | None, fim: date | None) -> Decimal:
    q = db.session.query(func.coalesce(func.sum(LancamentoFinanceiro.valor), 0)).filter(
        LancamentoFinanceiro.tenant_id == tenant_id, LancamentoFinanceiro.tipo == tipo
    )
    if conta_id is not None:
        q = q.filter(LancamentoFinanceiro.conta_id == conta_id)
    if inicio is not None:
        q = q.filter(LancamentoFinanceiro.data >= inicio)
    if fim is not None:
        q = q.filter(LancamentoFinanceiro.data <= fim)
    return q.scalar() or Decimal("0")


def saldo_conta(conta: ContaFinanceira) -> Decimal:
    entradas = _soma(conta.tenant_id, TipoLancamento.ENTRADA, conta.id, None, None)
    saidas = _soma(conta.tenant_id, TipoLancamento.SAIDA, conta.id, None, None)
    return conta.saldo_inicial + entradas - saidas


def saldos_contas(tenant_id: int) -> list[dict]:
    contas = ContaFinanceira.query.filter_by(tenant_id=tenant_id).all()
    return [{"conta": c, "saldo": saldo_conta(c)} for c in contas]


@dataclass
class ResumoPeriodo:
    receita: Decimal = Decimal("0")
    despesas: Decimal = Decimal("0")
    resultado: Decimal = Decimal("0")
    atendimentos: int = 0
    ticket_medio: Decimal = Decimal("0")


def resumo_periodo(tenant_id: int, inicio: date, fim: date) -> ResumoPeriodo:
    receita = _soma(tenant_id, TipoLancamento.ENTRADA, None, inicio, fim)
    despesas = _soma(tenant_id, TipoLancamento.SAIDA, None, inicio, fim)
    atendimentos = (
        LancamentoFinanceiro.query.filter(
            LancamentoFinanceiro.tenant_id == tenant_id,
            LancamentoFinanceiro.tipo == TipoLancamento.ENTRADA,
            LancamentoFinanceiro.data >= inicio,
            LancamentoFinanceiro.data <= fim,
        ).count()
    )
    ticket = (receita / atendimentos) if atendimentos else Decimal("0")
    return ResumoPeriodo(receita=receita, despesas=despesas, resultado=receita - despesas, atendimentos=atendimentos, ticket_medio=ticket)


@dataclass
class LinhaDemonstrativo:
    grupo: GrupoDRE | None
    rotulo: str
    sinal: str
    valor: Decimal
    percentual: Decimal
    forte: bool = False


@dataclass
class Demonstrativo:
    linhas: list[LinhaDemonstrativo] = field(default_factory=list)
    receita_bruta: Decimal = Decimal("0")
    resultado: Decimal = Decimal("0")
    margem_contribuicao_pct: Decimal = Decimal("0")


def demonstrativo(tenant_id: int, inicio: date, fim: date) -> Demonstrativo:
    por_grupo: dict[GrupoDRE, Decimal] = {}
    linhas_categoria: dict[GrupoDRE, list[LinhaDemonstrativo]] = {}

    resultado_q = (
        db.session.query(PlanoDeContas.grupo, PlanoDeContas.nome, func.coalesce(func.sum(LancamentoFinanceiro.valor), 0))
        .join(LancamentoFinanceiro, LancamentoFinanceiro.categoria_id == PlanoDeContas.id)
        .filter(
            LancamentoFinanceiro.tenant_id == tenant_id,
            LancamentoFinanceiro.data >= inicio,
            LancamentoFinanceiro.data <= fim,
        )
        .group_by(PlanoDeContas.grupo, PlanoDeContas.nome)
        .all()
    )

    for grupo, nome, total in resultado_q:
        por_grupo[grupo] = por_grupo.get(grupo, Decimal("0")) + total
        linhas_categoria.setdefault(grupo, []).append(
            LinhaDemonstrativo(grupo=grupo, rotulo=nome, sinal="", valor=total, percentual=Decimal("0"))
        )

    receita_bruta = por_grupo.get(GrupoDRE.RECEITA, Decimal("0"))
    custo_variavel = por_grupo.get(GrupoDRE.CUSTO_VARIAVEL, Decimal("0"))
    outras_receitas = por_grupo.get(GrupoDRE.OUTRAS_RECEITAS, Decimal("0"))
    despesa_fixa = por_grupo.get(GrupoDRE.DESPESA_FIXA, Decimal("0"))
    outras_despesas = por_grupo.get(GrupoDRE.OUTRAS_DESPESAS, Decimal("0"))

    margem_contribuicao = receita_bruta - custo_variavel
    resultado_final = margem_contribuicao + outras_receitas - despesa_fixa - outras_despesas

    base = receita_bruta if receita_bruta else Decimal("1")

    def pct(v: Decimal) -> Decimal:
        return (v / base * 100) if base else Decimal("0")

    linhas: list[LinhaDemonstrativo] = []
    linhas.append(LinhaDemonstrativo(GrupoDRE.RECEITA, "Receita bruta", "+", receita_bruta, pct(receita_bruta), forte=True))
    for l in linhas_categoria.get(GrupoDRE.RECEITA, []):
        l.percentual = pct(l.valor)
        linhas.append(l)

    linhas.append(LinhaDemonstrativo(GrupoDRE.CUSTO_VARIAVEL, "Custos variáveis", "-", -custo_variavel, -pct(custo_variavel), forte=True))
    for l in linhas_categoria.get(GrupoDRE.CUSTO_VARIAVEL, []):
        l.valor = -l.valor
        l.percentual = pct(l.valor)
        linhas.append(l)

    linhas.append(LinhaDemonstrativo(None, "Margem de contribuição", "=", margem_contribuicao, pct(margem_contribuicao), forte=True))

    if outras_receitas:
        linhas.append(LinhaDemonstrativo(GrupoDRE.OUTRAS_RECEITAS, "Outras receitas", "+", outras_receitas, pct(outras_receitas), forte=True))

    linhas.append(LinhaDemonstrativo(GrupoDRE.DESPESA_FIXA, "Despesas fixas", "-", -despesa_fixa, -pct(despesa_fixa), forte=True))
    for l in linhas_categoria.get(GrupoDRE.DESPESA_FIXA, []):
        l.valor = -l.valor
        l.percentual = pct(l.valor)
        linhas.append(l)

    if outras_despesas:
        linhas.append(LinhaDemonstrativo(GrupoDRE.OUTRAS_DESPESAS, "Outras despesas", "-", -outras_despesas, -pct(outras_despesas), forte=True))

    linhas.append(LinhaDemonstrativo(None, "Resultado do período", "=", resultado_final, pct(resultado_final), forte=True))

    margem_pct = pct(margem_contribuicao)

    return Demonstrativo(linhas=linhas, receita_bruta=receita_bruta, resultado=resultado_final, margem_contribuicao_pct=margem_pct)


def mes_a_mes(tenant_id: int, n_meses: int = 6) -> list[dict]:
    hoje = date.today()
    colunas = []
    ref = date(hoje.year, hoje.month, 1)
    for _ in range(n_meses):
        colunas.append(ref)
        if ref.month == 1:
            ref = date(ref.year - 1, 12, 1)
        else:
            ref = date(ref.year, ref.month - 1, 1)
    colunas.reverse()

    resultado = []
    for inicio_mes in colunas:
        ultimo_dia = monthrange(inicio_mes.year, inicio_mes.month)[1]
        fim_mes = min(date(inicio_mes.year, inicio_mes.month, ultimo_dia), hoje) if inicio_mes.month == hoje.month and inicio_mes.year == hoje.year else date(inicio_mes.year, inicio_mes.month, ultimo_dia)
        resumo = resumo_periodo(tenant_id, inicio_mes, fim_mes)
        resultado.append(
            {
                "mes": inicio_mes,
                "rotulo": mes_abreviado_pt(inicio_mes),
                "receita": resumo.receita,
                "despesas": resumo.despesas,
                "resultado": resumo.resultado,
                "em_curso": inicio_mes.month == hoje.month and inicio_mes.year == hoje.year,
            }
        )
    return resultado


def projecao_contas_pagar(tenant_id: int, n_meses: int = 6) -> list[dict]:
    hoje = date.today()
    ref = date(hoje.year, hoje.month, 1)
    meses = []
    for _ in range(n_meses):
        meses.append(ref)
        if ref.month == 12:
            ref = date(ref.year + 1, 1, 1)
        else:
            ref = date(ref.year, ref.month + 1, 1)

    abertas = ContaPagar.query.filter_by(tenant_id=tenant_id, pago=False).all()
    resultado = []
    for inicio_mes in meses:
        ultimo_dia = monthrange(inicio_mes.year, inicio_mes.month)[1]
        fim_mes = date(inicio_mes.year, inicio_mes.month, ultimo_dia)
        total = sum((c.valor for c in abertas if inicio_mes <= c.vencimento <= fim_mes), Decimal("0"))
        estimado = sum(
            (c.valor for c in abertas if c.recorrente_mensal and c.vencimento < inicio_mes),
            Decimal("0"),
        )
        resultado.append({"mes": inicio_mes, "rotulo": mes_abreviado_pt(inicio_mes), "total": total + estimado, "estimado": estimado})
    return resultado


def resumo_caixa_dia(tenant_id: int, dia: date) -> dict:
    caixa = Caixa.query.filter_by(tenant_id=tenant_id, data=dia).first()

    lancamentos_dia = LancamentoFinanceiro.query.filter(
        LancamentoFinanceiro.tenant_id == tenant_id,
        LancamentoFinanceiro.tipo == TipoLancamento.ENTRADA,
        LancamentoFinanceiro.data == dia,
        LancamentoFinanceiro.forma == FormaPagamento.DINHEIRO,
    ).all()
    em_especie = sum((l.valor for l in lancamentos_dia), Decimal("0"))

    sangrias = Decimal("0")
    suprimentos = Decimal("0")
    if caixa:
        for m in caixa.movimentos:
            if m.tipo == "sangria":
                sangrias += m.valor
            else:
                suprimentos += m.valor

    esperado = (caixa.saldo_abertura if caixa else Decimal("0")) + em_especie + suprimentos - sangrias

    return {
        "caixa": caixa,
        "em_especie": em_especie,
        "sangrias": sangrias,
        "suprimentos": suprimentos,
        "esperado": esperado,
    }
