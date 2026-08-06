import click
from flask import Flask

from app.extensions import db
from app.models import Tenant, User
from app.utils.security import hash_senha


def register_commands(app: Flask):
    @app.cli.command("create-tenant")
    @click.argument("nome_estabelecimento")
    def create_tenant(nome_estabelecimento):
        """Cria um novo tenant (estabelecimento) e imprime a api_key gerada."""
        tenant = Tenant(nome_estabelecimento=nome_estabelecimento)
        db.session.add(tenant)
        db.session.commit()
        click.echo(f"Tenant criado: id={tenant.id} api_key={tenant.api_key}")

    @app.cli.command("create-user")
    @click.option("--tenant-id", required=True, type=int)
    @click.option("--nome", required=True)
    @click.option("--email", required=True)
    @click.option("--senha", required=True)
    @click.option("--role", default="admin")
    def create_user(tenant_id, nome, email, senha, role):
        """Cria um usuário do painel vinculado a um tenant existente."""
        user = User(
            tenant_id=tenant_id,
            nome=nome,
            email=email.strip().lower(),
            senha_hash=hash_senha(senha),
            role=role,
        )
        db.session.add(user)
        db.session.commit()
        click.echo(f"Usuário criado: id={user.id} email={user.email}")
