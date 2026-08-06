import re

import pytest

from app import create_app
from app.extensions import db
from tests.conftest import TestConfig


class CSRFConfig(TestConfig):
    WTF_CSRF_ENABLED = True


@pytest.fixture
def csrf_app():
    application = create_app(CSRFConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def csrf_client(csrf_app):
    return csrf_app.test_client()


def test_post_sem_csrf_token_e_rejeitado(csrf_client):
    resp = csrf_client.post(
        "/auth/login", data={"email": "x@x.com", "senha": "qualquer"}
    )
    assert resp.status_code == 400


def test_post_com_csrf_token_do_form_e_aceito(csrf_client):
    pagina_login = csrf_client.get("/auth/login").data.decode()
    token = re.search(r'name="csrf_token" value="([^"]+)"', pagina_login).group(1)

    resp = csrf_client.post(
        "/auth/login",
        data={"email": "x@x.com", "senha": "qualquer", "csrf_token": token},
    )
    # credenciais inválidas, mas passou da checagem de CSRF (não é 400)
    assert resp.status_code == 200


def test_api_e_isenta_de_csrf(csrf_client):
    resp = csrf_client.get("/api/v1/servicos", headers={"X-API-Key": "qualquer"})
    assert resp.status_code == 401  # API key inválida, não bloqueio de CSRF
