import click
from flask import Flask

from app.extensions import db
from app.models import Recorrencia, Tenant, User
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

    @app.cli.command("gerar-recorrencias")
    def gerar_recorrencias():
        """Gera agendamentos dos próximos 60 dias para todas as regras ativas. Pensado para rodar via cron do sistema."""
        from app.utils.recorrencia import gerar_agendamentos

        total = 0
        for recorrencia in Recorrencia.query.filter_by(ativo=True).all():
            criados = gerar_agendamentos(recorrencia, dias_a_frente=60)
            total += criados
            click.echo(f"Recorrência {recorrencia.id} (tenant {recorrencia.tenant_id}): {criados} agendamento(s)")
        click.echo(f"Total: {total} agendamento(s) gerado(s).")
