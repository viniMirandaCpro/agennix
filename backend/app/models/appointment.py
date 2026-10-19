"""Agendamento: cliente, profissional, servico, inicio, fim e status.

'ends_at' calculado pela duracao do servico; 'price_charged' e snapshot do preco.
Constraint EXCLUDE impede choque de horario. Ver docs/modelagem.md secoes 3.7, 4.1 e 4.2.
"""
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import ExcludeConstraint

from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin

STATUSES = ("pendente", "confirmado", "em_atendimento", "concluido", "cancelado", "nao_compareceu")
SOURCES = ("painel", "publico", "api")


class Appointment(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.BigInteger, primary_key=True)
    client_id = db.Column(db.BigInteger, db.ForeignKey("clients.id"), nullable=False)
    professional_id = db.Column(db.BigInteger, db.ForeignKey("professionals.id"), nullable=False)
    service_id = db.Column(db.BigInteger, db.ForeignKey("services.id"), nullable=False)
    starts_at = db.Column(db.DateTime(timezone=True), nullable=False)
    ends_at = db.Column(db.DateTime(timezone=True), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="confirmado")
    price_charged = db.Column(db.Numeric(10, 2), nullable=False)
    source = db.Column(db.String(10), nullable=False, default="painel")
    notes = db.Column(db.Text)
    created_by_user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"))
    cancelled_at = db.Column(db.DateTime(timezone=True))
    cancellation_reason = db.Column(db.String(255))

    client = db.relationship("Client")
    professional = db.relationship("Professional")
    service = db.relationship("Service")

    __table_args__ = (
        db.CheckConstraint(
            "status IN ({})".format(",".join(f"'{s}'" for s in STATUSES)),
            name="ck_appointments_status",
        ),
        db.CheckConstraint(
            "source IN ({})".format(",".join(f"'{s}'" for s in SOURCES)),
            name="ck_appointments_source",
        ),
        ExcludeConstraint(
            (professional_id, "="),
            (func.tstzrange(starts_at, ends_at), "&&"),
            using="gist",
            where="status <> 'cancelado'",
            name="appointments_no_overlap",
        ),
        db.Index("ix_appointments_tenant_starts", "tenant_id", "starts_at"),
    )
