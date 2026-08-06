import enum
from datetime import datetime, timezone

from app.extensions import db


class RemetenteMensagem(str, enum.Enum):
    CLIENTE = "cliente"
    ROBO = "robo"
    EQUIPE = "equipe"


class Mensagem(db.Model):
    __tablename__ = "mensagens"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=True)
    telefone = db.Column(db.String(20), nullable=False)
    remetente = db.Column(
        db.Enum(RemetenteMensagem, name="remetente_mensagem"), nullable=False
    )
    texto = db.Column(db.Text, nullable=False)
    criado_em = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    tenant = db.relationship("Tenant", backref="mensagens")
    cliente = db.relationship("Cliente", backref="mensagens")

    def __repr__(self):
        return f"<Mensagem {self.id} {self.remetente} {self.telefone}>"
