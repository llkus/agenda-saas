from datetime import date, time, timedelta

import pytest

from app import create_app
from app.extensions import db
from app.models import Disponibilidade, Servico, Tenant, User
from app.utils.security import hash_senha


class TestConfig:
    SECRET_KEY = "test-secret-key-com-pelo-menos-32-bytes-de-tamanho"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = "test-jwt-secret-key-com-pelo-menos-32-bytes"
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 8
    JWT_COOKIE_CSRF_PROTECT = False
    WTF_CSRF_ENABLED = False
    TESTING = True


@pytest.fixture
def app():
    application = create_app(TestConfig)

    with application.app_context():
        db.create_all()
        # replica o índice único parcial da migration a1b2c3d4e5f6 (Postgres usa
        # sintaxe com cast de enum; sqlite aceita comparar direto com o texto)
        db.session.execute(
            db.text(
                "CREATE UNIQUE INDEX uq_agendamento_tenant_horario_ativo "
                "ON agendamentos (tenant_id, data_hora_inicio) "
                "WHERE status != 'CANCELADO'"
            )
        )
        db.session.commit()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def tenant(app):
    t = Tenant(nome_estabelecimento="Salão de Teste")
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture
def outro_tenant(app):
    t = Tenant(nome_estabelecimento="Outro Salão")
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture
def usuario(app, tenant):
    u = User(
        tenant_id=tenant.id,
        nome="Admin Teste",
        email="admin@teste.com",
        senha_hash=hash_senha("senha123"),
        role="admin",
    )
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture
def servico(app, tenant):
    s = Servico(tenant_id=tenant.id, nome="Corte de Cabelo", duracao_min=30, preco=45)
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture
def dia_disponivel():
    """Um dia sempre no futuro, evitando flakiness por causa do filtro de horário passado."""
    return date.today() + timedelta(days=7)


@pytest.fixture
def disponibilidade(app, tenant, dia_disponivel):
    d = Disponibilidade(
        tenant_id=tenant.id,
        dia_semana=dia_disponivel.weekday(),
        hora_inicio=time(9, 0),
        hora_fim=time(18, 0),
    )
    db.session.add(d)
    db.session.commit()
    return d


@pytest.fixture
def auth_client(client, usuario):
    client.post("/auth/login", data={"email": usuario.email, "senha": "senha123"})
    return client
