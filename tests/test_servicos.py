from app.extensions import db
from app.models import Servico


def test_criar_servico(auth_client):
    resp = auth_client.post(
        "/painel/servicos/novo",
        data={"nome": "Barba", "duracao_min": "20", "preco": "25,00"},
    )
    assert resp.status_code == 302

    resp = auth_client.get("/painel/servicos/")
    assert b"Barba" in resp.data


def test_alternar_status_servico(auth_client, servico):
    resp = auth_client.get("/painel/servicos/")
    assert b"Ativo" in resp.data

    auth_client.post(f"/painel/servicos/{servico.id}/alternar-status")

    resp = auth_client.get("/painel/servicos/")
    assert b"Inativo" in resp.data


def test_isolamento_multi_tenant_servico(app, auth_client, outro_tenant):
    servico_de_outro_tenant = Servico(
        tenant_id=outro_tenant.id, nome="Serviço Alheio", duracao_min=30, preco=50
    )
    db.session.add(servico_de_outro_tenant)
    db.session.commit()

    resp = auth_client.get(f"/painel/servicos/{servico_de_outro_tenant.id}/editar")
    assert resp.status_code == 404
