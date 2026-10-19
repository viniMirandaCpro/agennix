"""Tipo de servico oferecido: nome, duracao e preco.

A duracao alimenta o calculo automatico do horario de termino. Ver docs/modelagem.md secao 3.5.
"""
from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin


class Service(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "services"

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        db.CheckConstraint("duration_minutes > 0", name="ck_services_duration"),
        db.CheckConstraint("price >= 0", name="ck_services_price"),
    )
