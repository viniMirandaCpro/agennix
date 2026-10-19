"""Historias 5.2 (CRUD de agendamento), 5.8 (atendente cria agendamento) e 5.4 (agenda)."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Appointment, Client, Professional
from tests.conftest import FUTURE_DAY, PAST_DAY


@pytest.fixture
def customer(tenant):
    c = Client(tenant_id=tenant.id, name="Maria", whatsapp="+5511987654321")
    db.session.add(c)
    db.session.commit()
    return c


def book(http, professional, service, customer=None, **overrides):
    body = {
        "professional_id": professional.id,
        "service_id": service.id,
        "date": FUTURE_DAY,
        "time": "10:00",
    }
    if customer is not None:
        body["client_id"] = customer.id
    body.update(overrides)
    return http.post("/api/appointments", json=body)


def test_requires_session(client):
    assert client.get("/api/appointments?start=2026-01-01&end=2026-01-31").status_code == 401


def test_create_computes_end_and_keeps_price_snapshot(auth_client, professional, service, customer):
    r = book(auth_client, professional, service, customer)
    assert r.status_code == 201
    assert r.json["time"] == "10:00"
    assert r.json["ends_at"].startswith(f"{FUTURE_DAY}T10:30:00")
    assert r.json["ends_at"].endswith("-03:00")
    assert r.json["price_charged"] == "40.00"
    assert r.json["status"] == "confirmado" and r.json["source"] == "painel"

    service.price = Decimal("99.00")
    db.session.commit()
    listed = auth_client.get(f"/api/appointments?start={FUTURE_DAY}&end={FUTURE_DAY}").json
    assert listed[0]["price_charged"] == "40.00"


def test_create_with_new_client_registers_client(auth_client, professional, service):
    r = book(auth_client, professional, service, client={"name": "Jose", "whatsapp": "(11) 91234-5678"})
    assert r.status_code == 201
    assert r.json["client"]["whatsapp"] == "+5511912345678"
    assert Client.query.count() == 1


def test_new_client_with_invalid_whatsapp_is_400(auth_client, professional, service):
    r = book(auth_client, professional, service, client={"name": "Jose", "whatsapp": "123"})
    assert r.status_code == 400
    assert Client.query.count() == 0


def test_missing_fields_is_400(auth_client):
    r = auth_client.post("/api/appointments", json={})
    assert r.status_code == 400
    assert set(r.json["fields"]) >= {"professional_id", "service_id", "date", "time", "client"}


def test_overlap_with_same_professional_is_409(auth_client, professional, service, customer):
    assert book(auth_client, professional, service, customer).status_code == 201
    r = book(auth_client, professional, service, customer, time="10:15")
    assert r.status_code == 409
    assert r.json["message"] == "Profissional já tem agendamento nesse horário"


def test_back_to_back_is_allowed(auth_client, professional, service, customer):
    assert book(auth_client, professional, service, customer).status_code == 201
    assert book(auth_client, professional, service, customer, time="10:30").status_code == 201


def test_other_professional_same_time_is_allowed(auth_client, tenant, professional, service, customer):
    other = Professional(tenant_id=tenant.id, name="Ana")
    db.session.add(other)
    db.session.commit()
    assert book(auth_client, professional, service, customer).status_code == 201
    assert book(auth_client, other, service, customer).status_code == 201


def test_cancelled_appointment_frees_the_slot(auth_client, professional, service, customer):
    appt_id = book(auth_client, professional, service, customer).json["id"]
    r = auth_client.put(f"/api/appointments/{appt_id}", json={"status": "cancelado"})
    assert r.status_code == 200
    assert book(auth_client, professional, service, customer).status_code == 201


def test_database_blocks_overlap_even_without_python_check(tenant, professional, service, customer):
    start = datetime.now(timezone.utc) + timedelta(days=3)
    for minutes in (0, 10):
        db.session.add(
            Appointment(
                tenant_id=tenant.id,
                client_id=customer.id,
                professional_id=professional.id,
                service_id=service.id,
                starts_at=start + timedelta(minutes=minutes),
                ends_at=start + timedelta(minutes=minutes + 30),
                price_charged=Decimal("40.00"),
            )
        )
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_reschedule_past_requires_confirmation(auth_client, professional, service, customer):
    r = book(auth_client, professional, service, customer, date=PAST_DAY)
    assert r.status_code == 201  # registrar atendimento passado e permitido
    url = f"/api/appointments/{r.json['id']}"

    r = auth_client.put(url, json={"time": "11:00"})
    assert r.status_code == 409
    assert r.json["code"] == "past_requires_confirmation"

    r = auth_client.put(url, json={"time": "11:00", "confirm_past": True})
    assert r.status_code == 200
    assert r.json["time"] == "11:00"


def test_cancel_past_requires_confirmation(auth_client, professional, service, customer):
    url = f"/api/appointments/{book(auth_client, professional, service, customer, date=PAST_DAY).json['id']}"
    assert auth_client.put(url, json={"status": "cancelado"}).status_code == 409
    r = auth_client.put(
        url, json={"status": "cancelado", "cancellation_reason": "Erro", "confirm_past": True}
    )
    assert r.status_code == 200
    assert r.json["status"] == "cancelado" and r.json["cancellation_reason"] == "Erro"


def test_complete_past_needs_no_confirmation(auth_client, professional, service, customer):
    url = f"/api/appointments/{book(auth_client, professional, service, customer, date=PAST_DAY).json['id']}"
    r = auth_client.put(url, json={"status": "concluido"})
    assert r.status_code == 200 and r.json["status"] == "concluido"


def test_resending_unchanged_fields_on_past_needs_no_confirmation(auth_client, professional, service, customer):
    created = book(auth_client, professional, service, customer, date=PAST_DAY).json
    r = auth_client.put(
        f"/api/appointments/{created['id']}",
        json={"date": PAST_DAY, "time": "10:00", "professional_id": professional.id, "notes": "ok"},
    )
    assert r.status_code == 200 and r.json["notes"] == "ok"


def test_list_filters_by_period_and_professional(auth_client, tenant, professional, service, customer):
    other = Professional(tenant_id=tenant.id, name="Ana")
    db.session.add(other)
    db.session.commit()
    book(auth_client, professional, service, customer)
    book(auth_client, other, service, customer)
    book(auth_client, professional, service, customer, date=PAST_DAY)

    period = f"start={FUTURE_DAY}&end={FUTURE_DAY}"
    assert len(auth_client.get(f"/api/appointments?{period}").json) == 2
    only = auth_client.get(f"/api/appointments?{period}&professional_id={professional.id}").json
    assert [a["professional"]["id"] for a in only] == [professional.id]
