from datetime import datetime, timezone

from app.extensions import db


class Recorrencia(db.Model):
    __tablename__ = "recorrencias"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    servico_id = db.Column(db.Integer, db.ForeignKey("servicos.id"), nullable=False)
    dia_semana = db.Column(db.Integer, nullable=False)  # 0 = segunda ... 6 = domingo
    hora = db.Column(db.Time, nullable=False)
    intervalo_semanas = db.Column(db.Integer, nullable=False, default=1)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    gerado_ate = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    tenant = db.relationship("Tenant", backref="recorrencias")
    cliente = db.relationship("Cliente", backref="recorrencias")
    servico = db.relationship("Servico", backref="recorrencias")

    def __repr__(self):
        return f"<Recorrencia {self.id} cliente={self.cliente_id} dia={self.dia_semana}>"
