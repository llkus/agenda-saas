def test_login_com_senha_correta_seta_cookie_e_redireciona(client, usuario):
    resp = client.post(
        "/auth/login", data={"email": usuario.email, "senha": "senha123"}
    )
    assert resp.status_code == 302
    assert resp.headers["Location"] == "/painel/"
    assert "access_token_cookie" in resp.headers.get("Set-Cookie", "")


def test_login_com_senha_errada_nao_autentica(client, usuario):
    resp = client.post(
        "/auth/login", data={"email": usuario.email, "senha": "senha-errada"}
    )
    assert resp.status_code == 200  # re-renderiza o form de login, não redireciona
    assert b"Email ou senha inv\xc3\xa1lidos" in resp.data


def test_painel_sem_login_retorna_401(client):
    resp = client.get("/painel/")
    assert resp.status_code == 401


def test_painel_com_login_retorna_200(auth_client):
    resp = auth_client.get("/painel/")
    assert resp.status_code == 200


def test_logout_limpa_cookie(auth_client):
    resp = auth_client.get("/auth/logout")
    assert resp.status_code == 302
    resp2 = auth_client.get("/painel/")
    assert resp2.status_code == 401
