"""Job que cria os lembretes da janela e envia os SMS pendentes (Historias 5.3 e 5.12).

Roda a cada minuto pelo comando `flask scheduler` (app/tasks/__init__.py).
A antecedencia vem de REMINDER_HOURS_BEFORE.
"""
from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy import and_, exists

from app.extensions import db
from app.models import Appointment, Client, Notification
from app.services.sms_service import message_for, send_sms

MAX_ATTEMPTS = 3


def queue_reminders(now):
    window = timedelta(hours=current_app.config["REMINDER_HOURS_BEFORE"])
    has_reminder = exists().where(
        and_(Notification.appointment_id == Appointment.id, Notification.type == "lembrete")
    )
    due = (
        Appointment.query.join(Client, Appointment.client_id == Client.id)
        .filter(
            Appointment.status.in_(("pendente", "confirmado")),
            Appointment.starts_at > now,
            Appointment.starts_at <= now + window,
            # quem agendou dentro da janela acabou de agendar: nao precisa de lembrete
            Appointment.created_at <= Appointment.starts_at - window,
            Client.whatsapp.isnot(None),
            ~has_reminder,
        )
        .all()
    )
    for appt in due:
        db.session.add(
            Notification(
                tenant_id=appt.tenant_id,
                appointment=appt,
                type="lembrete",
                channel="sms",
                destination=appt.client.whatsapp,
                scheduled_for=appt.starts_at - window,
            )
        )
    db.session.commit()


def send_pending(now):
    # ponytail: sem trava de linha porque o agendador e um processo so (servico scheduler,
    # max_instances=1); com mais de um, buscar com FOR UPDATE SKIP LOCKED e commit no fim do lote.
    pending = (
        Notification.query.filter(Notification.status == "pendente", Notification.scheduled_for <= now)
        .order_by(Notification.scheduled_for)
        .all()
    )
    for n in pending:
        if n.appointment.status == "cancelado":
            n.status, n.error_message = "falhou", "Agendamento cancelado"
        else:
            n.attempts += 1
            try:
                n.provider_message_id = send_sms(n.destination, message_for(n))
                n.status, n.sent_at = "enviada", now
            except Exception as e:  # rede, credencial ou recusa do Twilio: tenta no proximo minuto
                n.error_message = str(e)
                if n.attempts >= MAX_ATTEMPTS:
                    n.status = "falhou"
        db.session.commit()  # um por mensagem: uma queda no meio do lote nao reenvia o que ja saiu


def run_once(now=None):
    now = now or datetime.now(timezone.utc)
    queue_reminders(now)
    send_pending(now)
