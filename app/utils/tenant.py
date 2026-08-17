from sqlalchemy import text

from app.extensions import db

# Ordem obrigatória: tabelas dependentes antes das que elas referenciam via FK.
# caixa_movimentos não tem tenant_id (só caixa_id), por isso o join com caixas.
_DELETES_EM_ORDEM = [
    "DELETE FROM caixa_movimentos WHERE caixa_id IN (SELECT id FROM caixas WHERE tenant_id=:tid)",
    "DELETE FROM lancamentos_financeiros WHERE tenant_id=:tid",
    "DELETE FROM contas_pagar WHERE tenant_id=:tid",
    "DELETE FROM mensagens WHERE tenant_id=:tid",
    "DELETE FROM recorrencias WHERE tenant_id=:tid",
    "DELETE FROM agendamentos WHERE tenant_id=:tid",
    "DELETE FROM caixas WHERE tenant_id=:tid",
    "DELETE FROM contas_financeiras WHERE tenant_id=:tid",
    "DELETE FROM plano_de_contas WHERE tenant_id=:tid",
    "DELETE FROM disponibilidades WHERE tenant_id=:tid",
    "DELETE FROM servicos WHERE tenant_id=:tid",
    "DELETE FROM clientes WHERE tenant_id=:tid",
    "DELETE FROM conversa_estados WHERE tenant_id=:tid",
    "DELETE FROM users WHERE tenant_id=:tid",
    "DELETE FROM tenants WHERE id=:tid",
]


def excluir_tenant(tenant_id: int) -> None:
    """Apaga um tenant e todos os dados vinculados a ele, em cascata.

    Não existe cascade no nível do ORM/banco (ver README) porque um tenant
    tem dependentes em duas camadas (ex: caixa_movimentos -> caixas -> tenant),
    então as exclusões são feitas em ordem explícita dentro de uma única
    transação. Se qualquer passo falhar, nada é apagado.
    """
    for stmt in _DELETES_EM_ORDEM:
        db.session.execute(text(stmt), {"tid": tenant_id})
    db.session.commit()
