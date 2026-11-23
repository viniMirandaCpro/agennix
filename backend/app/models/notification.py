"""SMS de confirmacao e de lembrete de um agendamento (Historias 5.3 e 5.12).

UNIQUE (appointment_id, type) impede enviar o mesmo lembrete duas vezes.
Ver docs/modelagem.md secoes 3.19 e 4.6.
"""
from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin

TYPES = ("confirmacao", "lembrete")
CHANNELS = ("sms", "email")
STATUSES = ("pendente", "enviada", "falhou")


def _in(column, values):
    return "{} IN ({})".format(column, ",".join(f"'{v}'" for v in values))


class Notification(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.BigInteger, primary_key=True)
    appointment_id = db.Column(db.BigInteger, db.ForeignKey("appointments.id"), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    channel = db.Column(db.String(20), nullable=False, default="sms")
    destination = db.Column(db.String(180), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pendente")
    scheduled_for = db.Column(db.DateTime(timezone=True), nullable=False)
    sent_at = db.Column(db.DateTime(timezone=True))
    provider_message_id = db.Column(db.String(120))
    error_message = db.Column(db.Text)
    attempts = db.Column(db.Integer, nullable=False, default=0)

    appointment = db.relationship("Appointment")

    __table_args__ = (
        db.CheckConstraint(_in("type", TYPES), name="ck_notifications_type"),
        db.CheckConstraint(_in("channel", CHANNELS), name="ck_notifications_channel"),
        db.CheckConstraint(_in("status", STATUSES), name="ck_notifications_status"),
        db.UniqueConstraint("appointment_id", "type", name="notifications_unique_per_appointment"),
        db.Index("ix_notifications_status_scheduled", "status", "scheduled_for"),
    )
