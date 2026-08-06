from app.extensions import db


def test_sem_api_key_retorna_401(client):
    resp = client.get("/api/v1/servicos")
    assert resp.status_code == 401


def test_api_key_invalida_retorna_401(client):
    resp = client.get("/api/v1/servicos", headers={"X-API-Key": "chave-errada"})
    assert resp.status_code == 401


def test_listar_servicos(client, tenant, servico):
    resp = client.get("/api/v1/servicos", headers={"X-API-Key": tenant.api_key})
    assert resp.status_code == 200
    assert resp.get_json() == [
        {"id": servico.id, "nome": servico.nome, "duracao_min": 30, "preco": "45.00"}
    ]


def test_criar_agendamento_cria_cliente_novo(client, tenant, servico, disponibilidade, dia_disponivel):
    resp = client.post(
        "/api/v1/agendamentos",
        headers={"X-API-Key": tenant.api_key},
        json={
            "nome": "Maria Bot",
            "telefone": "11988887777",
            "servico_id": servico.id,
            "data": dia_disponivel.isoformat(),
            "horario": "10:00",
        },
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["cliente"] == "Maria Bot"
    assert body["status"] == "a_confirmar"

    resp2 = client.get(
        "/api/v1/clientes?telefone=11988887777", headers={"X-API-Key": tenant.api_key}
    )
    assert resp2.status_code == 200


def test_cancelar_agendamento_libera_horario(client, tenant, servico, disponibilidade, dia_disponivel):
    headers = {"X-API-Key": tenant.api_key}
    payload = {
        "nome": "Maria Bot",
        "telefone": "11988887777",
        "servico_id": servico.id,
        "data": dia_disponivel.isoformat(),
        "horario": "10:00",
    }
    criado = client.post("/api/v1/agendamentos", headers=headers, json=payload).get_json()

    resp_horarios = client.get(
        f"/api/v1/horarios-disponiveis?servico_id={servico.id}&data={dia_disponivel.isoformat()}",
        headers=headers,
    )
    assert "10:00" not in resp_horarios.get_json()

    resp_cancelar = client.post(
        f"/api/v1/agendamentos/{criado['id']}/cancelar", headers=headers
    )
    assert resp_cancelar.status_code == 200

    resp_horarios2 = client.get(
        f"/api/v1/horarios-disponiveis?servico_id={servico.id}&data={dia_disponivel.isoformat()}",
        headers=headers,
    )
    assert "10:00" in resp_horarios2.get_json()


def test_isolamento_multi_tenant_api(client, tenant, outro_tenant, servico):
    from app.models import Agendamento, Cliente, StatusAgendamento
    from datetime import datetime, timedelta

    cliente_outro = Cliente(tenant_id=outro_tenant.id, nome="Cliente Alheio", telefone="11911112222")
    db.session.add(cliente_outro)
    db.session.commit()

    inicio = datetime.now() + timedelta(days=1)
    ag = Agendamento(
        tenant_id=outro_tenant.id,
        cliente_id=cliente_outro.id,
        servico_id=servico.id,
        data_hora_inicio=inicio,
        data_hora_fim=inicio,
        valor=servico.preco,
        status=StatusAgendamento.A_CONFIRMAR,
    )
    db.session.add(ag)
    db.session.commit()

    resp = client.post(
        f"/api/v1/agendamentos/{ag.id}/cancelar", headers={"X-API-Key": tenant.api_key}
    )
    assert resp.status_code == 404
