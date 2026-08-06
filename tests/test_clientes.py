def test_criar_cliente(auth_client):
    resp = auth_client.post(
        "/painel/clientes/novo", data={"nome": "João Silva", "telefone": "11999999999"}
    )
    assert resp.status_code == 302

    resp = auth_client.get("/painel/clientes/")
    assert "João Silva".encode() in resp.data


def test_telefone_duplicado_no_mesmo_tenant_e_barrado(auth_client):
    auth_client.post(
        "/painel/clientes/novo", data={"nome": "João Silva", "telefone": "11999999999"}
    )
    resp = auth_client.post(
        "/painel/clientes/novo", data={"nome": "João Duplicado", "telefone": "11999999999"}
    )
    assert b"J\xc3\xa1 existe um cliente" in resp.data


def test_excluir_cliente(auth_client):
    import re

    auth_client.post(
        "/painel/clientes/novo", data={"nome": "João Silva", "telefone": "11999999999"}
    )
    resp = auth_client.get("/painel/clientes/")
    cliente_id = re.search(r"clientes/(\d+)/editar", resp.data.decode()).group(1)

    auth_client.post(f"/painel/clientes/{cliente_id}/excluir")
    resp = auth_client.get("/painel/clientes/")
    assert "João Silva".encode() not in resp.data
