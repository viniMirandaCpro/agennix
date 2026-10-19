"""Estabelecimento (tenant). Raiz do isolamento multitenant.

'slug' alimenta a URL publica /agendar/{slug}. Ver docs/modelagem.md secao 3.1.
"""
from app.extensions import db
from app.models.mixins import TimestampMixin


class Tenant(TimestampMixin, db.Model):
    __tablename__ = "tenants"

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(60), nullable=False, unique=True)
    segment = db.Column(db.String(30), nullable=False, default="outro")
    email = db.Column(db.String(180))
    whatsapp = db.Column(db.String(20))
    address = db.Column(db.String(255))
    timezone = db.Column(db.String(50), nullable=False, default="America/Sao_Paulo")
    active = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        db.CheckConstraint(
            "segment IN ('barbearia','salao','clinica','estudio','consultorio','outro')",
            name="ck_tenants_segment",
        ),
    )
