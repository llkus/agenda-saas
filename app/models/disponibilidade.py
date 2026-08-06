from app.extensions import db


class Disponibilidade(db.Model):
    __tablename__ = "disponibilidades"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    dia_semana = db.Column(db.Integer, nullable=False)  # 0 = segunda ... 6 = domingo
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fim = db.Column(db.Time, nullable=False)

    tenant = db.relationship("Tenant", backref="disponibilidades")

    def __repr__(self):
        return f"<Disponibilidade {self.id} tenant={self.tenant_id} dia={self.dia_semana}>"
