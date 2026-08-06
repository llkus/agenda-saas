from app.extensions import db


class Servico(db.Model):
    __tablename__ = "servicos"

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    duracao_min = db.Column(db.Integer, nullable=False)
    preco = db.Column(db.Numeric(10, 2), nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)

    tenant = db.relationship("Tenant", backref="servicos")

    def __repr__(self):
        return f"<Servico {self.id} {self.nome}>"
