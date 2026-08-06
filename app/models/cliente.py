from datetime import datetime, timezone

from app.extensions import db


class Cliente(db.Model):
    __tablename__ = "clientes"
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "telefone", name="uq_cliente_tenant_telefone"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    tenant = db.relationship("Tenant", backref="clientes")

    def __repr__(self):
        return f"<Cliente {self.id} {self.nome}>"
