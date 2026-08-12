import enum
from datetime import datetime, timezone

from app.extensions import db


class ModoConversa(str, enum.Enum):
    BOT = "bot"
    HUMANO = "humano"
    ENCERRADA = "encerrada"


class ConversaEstado(db.Model):
    __tablename__ = "conversa_estados"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    modo = db.Column(db.Enum(ModoConversa, name="modo_conversa"), nullable=False, default=ModoConversa.BOT)
    atualizado_em = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    tenant = db.relationship("Tenant", backref="conversa_estados")

    __table_args__ = (db.UniqueConstraint("tenant_id", "telefone", name="uq_conversa_estado_tenant_telefone"),)

    def __repr__(self):
        return f"<ConversaEstado {self.telefone} modo={self.modo}>"
