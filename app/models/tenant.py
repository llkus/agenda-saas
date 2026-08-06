import secrets
from datetime import datetime, timezone

from app.extensions import db


def gerar_api_key():
    return secrets.token_hex(32)


class Tenant(db.Model):
    __tablename__ = "tenants"

    id = db.Column(db.Integer, primary_key=True)
    nome_estabelecimento = db.Column(db.String(120), nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=False, default=gerar_api_key)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Tenant {self.id} {self.nome_estabelecimento}>"
