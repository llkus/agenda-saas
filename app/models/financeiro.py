import enum
from datetime import datetime, timezone

from app.extensions import db


class GrupoDRE(str, enum.Enum):
    RECEITA = "receita"
    CUSTO_VARIAVEL = "custo_variavel"
    DESPESA_FIXA = "despesa_fixa"
    OUTRAS_RECEITAS = "outras_receitas"
    OUTRAS_DESPESAS = "outras_despesas"


class TipoLancamento(str, enum.Enum):
    ENTRADA = "entrada"
    SAIDA = "saida"


class FormaPagamento(str, enum.Enum):
    DINHEIRO = "dinheiro"
    PIX = "pix"
    CREDITO = "credito"
    DEBITO = "debito"
    OUTRO = "outro"


class OrigemLancamento(str, enum.Enum):
    MANUAL = "manual"
    AGENDAMENTO = "agendamento"
    CONTA_PAGAR = "conta_pagar"


class ContaFinanceira(db.Model):
    __tablename__ = "contas_financeiras"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    nome = db.Column(db.String(80), nullable=False)
    saldo_inicial = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    tenant = db.relationship("Tenant", backref="contas_financeiras")

    def __repr__(self):
        return f"<ContaFinanceira {self.nome}>"


class PlanoDeContas(db.Model):
    __tablename__ = "plano_de_contas"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    nome = db.Column(db.String(80), nullable=False)
    grupo = db.Column(db.Enum(GrupoDRE, name="grupo_dre"), nullable=False)
    nota = db.Column(db.String(160), nullable=True)
    sistema = db.Column(db.Boolean, nullable=False, default=False)

    tenant = db.relationship("Tenant", backref="plano_de_contas")

    def __repr__(self):
        return f"<PlanoDeContas {self.nome} ({self.grupo})>"


class LancamentoFinanceiro(db.Model):
    __tablename__ = "lancamentos_financeiros"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    conta_id = db.Column(db.Integer, db.ForeignKey("contas_financeiras.id"), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey("plano_de_contas.id"), nullable=False)
    tipo = db.Column(db.Enum(TipoLancamento, name="tipo_lancamento"), nullable=False)
    forma = db.Column(db.Enum(FormaPagamento, name="forma_pagamento"), nullable=False, default=FormaPagamento.OUTRO)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    data = db.Column(db.Date, nullable=False)
    descricao = db.Column(db.String(160), nullable=False)
    origem = db.Column(db.Enum(OrigemLancamento, name="origem_lancamento"), nullable=False, default=OrigemLancamento.MANUAL)
    origem_id = db.Column(db.Integer, nullable=True)
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    tenant = db.relationship("Tenant", backref="lancamentos_financeiros")
    conta = db.relationship("ContaFinanceira", backref="lancamentos")
    categoria = db.relationship("PlanoDeContas", backref="lancamentos")

    def __repr__(self):
        return f"<LancamentoFinanceiro {self.tipo} {self.valor}>"


class ContaPagar(db.Model):
    __tablename__ = "contas_pagar"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey("plano_de_contas.id"), nullable=False)
    descricao = db.Column(db.String(160), nullable=False)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    vencimento = db.Column(db.Date, nullable=False)
    recorrente_mensal = db.Column(db.Boolean, nullable=False, default=False)
    parcela_atual = db.Column(db.Integer, nullable=True)
    parcelas_total = db.Column(db.Integer, nullable=True)
    pago = db.Column(db.Boolean, nullable=False, default=False)
    pago_em = db.Column(db.Date, nullable=True)
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    tenant = db.relationship("Tenant", backref="contas_pagar")
    categoria = db.relationship("PlanoDeContas", backref="contas_pagar")

    def __repr__(self):
        return f"<ContaPagar {self.descricao} {self.valor}>"
