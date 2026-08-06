import enum
from datetime import datetime, timezone

from app.extensions import db


class StatusAgendamento(str, enum.Enum):
    A_CONFIRMAR = "a_confirmar"
    CONFIRMADO = "confirmado"
    REALIZADO = "realizado"
    FEEDBACK = "feedback"
    CANCELADO = "cancelado"


class Agendamento(db.Model):
    __tablename__ = "agendamentos"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    servico_id = db.Column(db.Integer, db.ForeignKey("servicos.id"), nullable=False)
    data_hora_inicio = db.Column(db.DateTime, nullable=False)
    data_hora_fim = db.Column(db.DateTime, nullable=False)
    status = db.Column(
        db.Enum(StatusAgendamento, name="status_agendamento"),
        nullable=False,
        default=StatusAgendamento.A_CONFIRMAR,
    )
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    tenant = db.relationship("Tenant", backref="agendamentos")
    cliente = db.relationship("Cliente", backref="agendamentos")
    servico = db.relationship("Servico", backref="agendamentos")

    def __repr__(self):
        return f"<Agendamento {self.id} {self.status}>"
