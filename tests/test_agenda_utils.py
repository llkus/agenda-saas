from datetime import datetime, timedelta

from app.extensions import db
from app.models import Agendamento, StatusAgendamento
from app.utils.agenda import horarios_disponiveis


def test_horarios_disponiveis_dentro_da_janela(app, tenant, servico, disponibilidade, dia_disponivel):
    horarios = horarios_disponiveis(tenant.id, servico.id, dia_disponivel)
    assert horarios[0].strftime("%H:%M") == "09:00"
    assert horarios[-1].strftime("%H:%M") == "17:30"  # último início possível pra 30min antes das 18:00


def test_sem_disponibilidade_cadastrada_retorna_vazio(app, tenant, servico, dia_disponivel):
    horarios = horarios_disponiveis(tenant.id, servico.id, dia_disponivel)
    assert horarios == []


def test_horario_ocupado_some_da_lista(app, tenant, servico, disponibilidade, dia_disponivel):
    inicio = datetime.combine(dia_disponivel, datetime.min.time().replace(hour=10))
    ag = Agendamento(
        tenant_id=tenant.id,
        cliente_id=_criar_cliente(tenant.id).id,
        servico_id=servico.id,
        data_hora_inicio=inicio,
        data_hora_fim=inicio + timedelta(minutes=servico.duracao_min),
        valor=servico.preco,
        status=StatusAgendamento.CONFIRMADO,
    )
    db.session.add(ag)
    db.session.commit()

    horarios = [h.strftime("%H:%M") for h in horarios_disponiveis(tenant.id, servico.id, dia_disponivel)]
    assert "10:00" not in horarios
    assert "09:00" in horarios


def test_agendamento_cancelado_nao_ocupa_horario(app, tenant, servico, disponibilidade, dia_disponivel):
    inicio = datetime.combine(dia_disponivel, datetime.min.time().replace(hour=10))
    ag = Agendamento(
        tenant_id=tenant.id,
        cliente_id=_criar_cliente(tenant.id).id,
        servico_id=servico.id,
        data_hora_inicio=inicio,
        data_hora_fim=inicio + timedelta(minutes=servico.duracao_min),
        valor=servico.preco,
        status=StatusAgendamento.CANCELADO,
    )
    db.session.add(ag)
    db.session.commit()

    horarios = [h.strftime("%H:%M") for h in horarios_disponiveis(tenant.id, servico.id, dia_disponivel)]
    assert "10:00" in horarios


def _criar_cliente(tenant_id):
    from app.models import Cliente

    c = Cliente(tenant_id=tenant_id, nome="Cliente Teste", telefone="11988887777")
    db.session.add(c)
    db.session.commit()
    return c
