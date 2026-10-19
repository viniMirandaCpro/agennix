"""Profissional que presta o atendimento.

'user_id' e OPCIONAL: profissional pode ter agenda sem ter login. Ver docs/modelagem.md secao 3.4.
ponytail: professional_services (3.6) fica para depois - no MVP qualquer profissional faz qualquer servico.
"""
from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin


class Professional(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "professionals"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"))
    name = db.Column(db.String(120), nullable=False)
    nickname = db.Column(db.String(60))
    phone = db.Column(db.String(20))
    active = db.Column(db.Boolean, nullable=False, default=True)

    working_hours = db.relationship(
        "WorkingHours", cascade="all, delete-orphan", order_by="WorkingHours.weekday"
    )
