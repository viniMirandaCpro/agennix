"""Envio de SMS pelo Twilio e texto das mensagens (Historias 5.3 e 5.12).

Chamada direta na API REST com requests: o SDK do Twilio seria uma dependencia
a mais para um unico POST.
"""
import unicodedata
from zoneinfo import ZoneInfo

import requests
from flask import current_app

from app.extensions import db
from app.models import Tenant

TWILIO_URL = "https://api.twilio.com/2010-04-01/Accounts/{}/Messages.json"


def send_sms(to, body):
    """Envia e devolve o SID da mensagem. Qualquer recusa vira RuntimeError."""
    cfg = current_app.config
    sid, token, sender = cfg["TWILIO_ACCOUNT_SID"], cfg["TWILIO_AUTH_TOKEN"], cfg["TWILIO_FROM_NUMBER"]
    if not (sid and token and sender):
        raise RuntimeError("Twilio não configurado")
    r = requests.post(
        TWILIO_URL.format(sid),
        auth=(sid, token),
        data={"From": sender, "To": to, "Body": body},
        timeout=10,
    )
    if not r.ok:
        raise RuntimeError(r.json().get("message", r.text))
    return r.json()["sid"]


def _ascii(text):
    # Acento faz o SMS cair de 160 para 70 caracteres por segmento.
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def message_for(notification):
    appt = notification.appointment
    tenant = db.session.get(Tenant, notification.tenant_id)
    local = appt.starts_at.astimezone(ZoneInfo(tenant.timezone))
    name = appt.client.name.split()[0]
    when = f"{local:%d/%m} as {local:%H:%M}"
    what = f"{appt.service.name} com {appt.professional.name}"
    if notification.type == "confirmacao":
        text = f"{tenant.name}: Ola {name}, seu horario de {what} esta confirmado para {when}."
    else:
        text = f"{tenant.name}: Ola {name}, lembrete: {what} em {when}."
    return _ascii(text)
