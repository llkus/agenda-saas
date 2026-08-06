"""indice unico parcial para evitar dois agendamentos ativos no mesmo horario

Revision ID: a1b2c3d4e5f6
Revises: 5f5967dee734
Create Date: 2026-08-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "5f5967dee734"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "uq_agendamento_tenant_horario_ativo",
        "agendamentos",
        ["tenant_id", "data_hora_inicio"],
        unique=True,
        # SQLAlchemy grava o .name do enum Python (maiúsculo), não o .value
        postgresql_where=sa.text("status != 'CANCELADO'::status_agendamento"),
    )


def downgrade():
    op.drop_index("uq_agendamento_tenant_horario_ativo", table_name="agendamentos")
