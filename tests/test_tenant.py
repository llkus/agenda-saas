from datetime import date, datetime, time, timedelta

from app.extensions import db
from app.models import (
    Agendamento,
    Cliente,
    ContaFinanceira,
    ContaPagar,
    ConversaEstado,
    Disponibilidade,
    GrupoDRE,
    LancamentoFinanceiro,
    Mensagem,
    PlanoDeContas,
    Recorrencia,
    RemetenteMensagem,
    StatusAgendamento,
    Tenant,
    TipoLancamento,
    User,
)
from app.utils.security import hash_senha
from app.utils.tenant import excluir_tenant


def _popular_tenant_completo(app, tenant_id: int, sufixo: str):
    """Cria pelo menos um registro em toda tabela que referencia tenant_id
    (direta ou indiretamente), pra garantir que excluir_tenant cobre tudo."""
    db.session.add(User(
        tenant_id=tenant_id, nome=f"User {sufixo}", email=f"user{sufixo}@teste.com",
        senha_hash=hash_senha("senha123"),
    ))
    cliente = Cliente(tenant_id=tenant_id, nome=f"Cliente {sufixo}", telefone=f"55999{sufixo}")
    servico = None
    from app.models import Servico
    servico = Servico(tenant_id=tenant_id, nome=f"Servico {sufixo}", duracao_min=30, preco=45)
    db.session.add_all([cliente, servico])
    db.session.flush()

    db.session.add(Disponibilidade(tenant_id=tenant_id, dia_semana=1, hora_inicio=time(9, 0), hora_fim=time(18, 0)))

    inicio = datetime.now() + timedelta(days=10)
    agendamento = Agendamento(
        tenant_id=tenant_id, cliente_id=cliente.id, servico_id=servico.id,
        data_hora_inicio=inicio, data_hora_fim=inicio + timedelta(minutes=30),
        status=StatusAgendamento.A_CONFIRMAR, valor=45,
    )
    db.session.add(agendamento)

    db.session.add(Mensagem(
        tenant_id=tenant_id, cliente_id=cliente.id, telefone=cliente.telefone,
        remetente=RemetenteMensagem.CLIENTE, texto="oi",
    ))
    db.session.add(ConversaEstado(tenant_id=tenant_id, telefone=cliente.telefone))
    db.session.add(Recorrencia(
        tenant_id=tenant_id, cliente_id=cliente.id, servico_id=servico.id,
        dia_semana=1, hora=time(9, 0),
    ))

    conta_fin = ContaFinanceira(tenant_id=tenant_id, nome=f"Caixa {sufixo}", saldo_inicial=0)
    categoria = PlanoDeContas(tenant_id=tenant_id, nome=f"Receita {sufixo}", grupo=GrupoDRE.RECEITA, sistema=False)
    db.session.add_all([conta_fin, categoria])
    db.session.flush()

    db.session.add(LancamentoFinanceiro(
        tenant_id=tenant_id, conta_id=conta_fin.id, categoria_id=categoria.id,
        tipo=TipoLancamento.ENTRADA, valor=45, data=date.today(), descricao="teste",
    ))
    db.session.add(ContaPagar(
        tenant_id=tenant_id, categoria_id=categoria.id, descricao="conta teste",
        valor=100, vencimento=date.today(),
    ))

    db.session.commit()


def test_excluir_tenant_apaga_tudo_e_preserva_outros_tenants(app, tenant, outro_tenant):
    tenant_id = tenant.id
    outro_tenant_id = outro_tenant.id
    _popular_tenant_completo(app, tenant_id, "a")
    _popular_tenant_completo(app, outro_tenant_id, "b")

    excluir_tenant(tenant_id)

    assert db.session.get(Tenant, tenant_id) is None

    tabelas_tenant_direto = [User, Cliente, Disponibilidade, Agendamento, Mensagem,
                              ConversaEstado, Recorrencia, ContaFinanceira, PlanoDeContas,
                              LancamentoFinanceiro, ContaPagar]
    from app.models import Servico
    tabelas_tenant_direto.append(Servico)

    for modelo in tabelas_tenant_direto:
        assert modelo.query.filter_by(tenant_id=tenant_id).count() == 0, modelo.__name__

    # o outro tenant não foi tocado
    assert db.session.get(Tenant, outro_tenant_id) is not None
    for modelo in tabelas_tenant_direto:
        assert modelo.query.filter_by(tenant_id=outro_tenant_id).count() == 1, modelo.__name__


def test_excluir_tenant_sem_dados_vinculados(app, tenant):
    tenant_id = tenant.id
    excluir_tenant(tenant_id)
    assert db.session.get(Tenant, tenant_id) is None


def test_delete_tenant_cli_pede_confirmacao(app):
    runner = app.test_cli_runner()
    t = Tenant(nome_estabelecimento="Vai Apagar")
    db.session.add(t)
    db.session.commit()
    tenant_id = t.id

    result = runner.invoke(args=["delete-tenant", "--tenant-id", str(tenant_id)], input="n\n")
    assert db.session.get(Tenant, tenant_id) is not None

    result = runner.invoke(args=["delete-tenant", "--tenant-id", str(tenant_id), "--confirmar"])
    assert result.exit_code == 0
    assert db.session.get(Tenant, tenant_id) is None


def test_delete_tenant_cli_id_inexistente(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["delete-tenant", "--tenant-id", "999999", "--confirmar"])
    assert result.exit_code == 0
    assert "Nenhum tenant" in result.output
