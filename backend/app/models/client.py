"""Cliente final do estabelecimento.

Senha OPCIONAL: agenda sem login e cria conta depois. CHECK exige whatsapp ou email.
UNIQUE (tenant_id, whatsapp). Ver docs/modelagem.md secoes 3.3 e 4.4.
"""
from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin


class Client(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "clients"

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    whatsapp = db.Column(db.String(20))
    email = db.Column(db.String(180))
    password_hash = db.Column(db.String(255))
    notes = db.Column(db.Text)

    __table_args__ = (
        db.CheckConstraint("whatsapp IS NOT NULL OR email IS NOT NULL", name="ck_clients_contact"),
        db.UniqueConstraint("tenant_id", "whatsapp", name="uq_clients_tenant_whatsapp"),
    )
