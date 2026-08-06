from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Agendamento, Cliente, StatusAgendamento


@pytest.fixture
def cliente(app, tenant):
    c = Cliente(tenant_id=tenant.id, nome="João Silva", telefone="11999999999")
    db.session.add(c)
    db.session.commit()
    return c


def test_criar_agendamento(auth_client, tenant, cliente, servico, disponibilidade, dia_disponivel):
    resp = auth_client.post(
        "/painel/agendamentos/novo",
        data={
            "cliente_id": cliente.id,
            "servico_id": servico.id,
            "data": dia_disponivel.isoformat(),
            "horario": "10:00",
        },
    )
    assert resp.status_code == 302

    ag = Agendamento.query.filter_by(tenant_id=tenant.id).first()
    assert ag is not None
    assert ag.status == StatusAgendamento.A_CONFIRMAR
    assert ag.valor == servico.preco  # snapshot do preço no momento da criação


def test_criar_agendamento_em_horario_ja_ocupado_e_barrado(
    auth_client, tenant, cliente, servico, disponibilidade, dia_disponivel
):
    payload = {
        "cliente_id": cliente.id,
        "servico_id": servico.id,
        "data": dia_disponivel.isoformat(),
        "horario": "10:00",
    }
    auth_client.post("/painel/agendamentos/novo", data=payload)
    resp = auth_client.post("/painel/agendamentos/novo", data=payload)

    assert "não está mais disponível".encode() in resp.data
    assert Agendamento.query.filter_by(tenant_id=tenant.id).count() == 1


def test_indice_unico_barra_insercao_direta_no_mesmo_horario(app, tenant, cliente, servico, dia_disponivel):
    inicio = datetime.combine(dia_disponivel, datetime.min.time().replace(hour=10))

    ag1 = Agendamento(
        tenant_id=tenant.id,
        cliente_id=cliente.id,
        servico_id=servico.id,
        data_hora_inicio=inicio,
        data_hora_fim=inicio,
        valor=servico.preco,
        status=StatusAgendamento.A_CONFIRMAR,
    )
    db.session.add(ag1)
    db.session.commit()

    ag2 = Agendamento(
        tenant_id=tenant.id,
        cliente_id=cliente.id,
        servico_id=servico.id,
        data_hora_inicio=inicio,
        data_hora_fim=inicio,
        valor=servico.preco,
        status=StatusAgendamento.CONFIRMADO,
    )
    db.session.add(ag2)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_mudar_status_via_kanban_endpoint(auth_client, tenant, cliente, servico, dia_disponivel):
    inicio = datetime.combine(dia_disponivel, datetime.min.time().replace(hour=10))
    ag = Agendamento(
        tenant_id=tenant.id,
        cliente_id=cliente.id,
        servico_id=servico.id,
        data_hora_inicio=inicio,
        data_hora_fim=inicio,
        valor=servico.preco,
        status=StatusAgendamento.A_CONFIRMAR,
    )
    db.session.add(ag)
    db.session.commit()

    resp = auth_client.post(
        f"/painel/agendamentos/{ag.id}/mover-status", json={"status": "confirmado"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "confirmado"


def test_isolamento_multi_tenant_agendamento(auth_client, outro_tenant, servico, dia_disponivel):
    from app.models import Cliente

    cliente_outro = Cliente(tenant_id=outro_tenant.id, nome="Cliente Alheio", telefone="11911112222")
    db.session.add(cliente_outro)
    db.session.commit()

    inicio = datetime.combine(dia_disponivel, datetime.min.time().replace(hour=10))
    ag_outro = Agendamento(
        tenant_id=outro_tenant.id,
        cliente_id=cliente_outro.id,
        servico_id=servico.id,
        data_hora_inicio=inicio,
        data_hora_fim=inicio,
        valor=servico.preco,
        status=StatusAgendamento.A_CONFIRMAR,
    )
    db.session.add(ag_outro)
    db.session.commit()

    resp = auth_client.post(
        f"/painel/agendamentos/{ag_outro.id}/mover-status", json={"status": "confirmado"}
    )
    assert resp.status_code == 404
