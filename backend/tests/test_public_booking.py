"""Historia 5.12: agendamento rapido pelo cliente, sem login."""
from datetime import date, time
from decimal import Decimal

from app.extensions import db
from app.models import Appointment, Client, Service, WorkingHours
from tests.conftest import FUTURE_DAY, PAST_DAY

BASE = "/api/public/teste"


def slots(http, professional, service, day=FUTURE_DAY):
    r = http.get(
        f"{BASE}/availability?service_id={service.id}&professional_id={professional.id}&date={day}"
    )
    assert r.status_code == 200
    return r.json["slots"]


def public_book(http, professional, service, **overrides):
    body = {
        "service_id": service.id,
        "professional_id": professional.id,
        "date": FUTURE_DAY,
        "time": "10:00",
        "name": "Maria",
        "whatsapp": "(11) 98765-4321",
    }
    body.update(overrides)
    return http.post(f"{BASE}/appointments", json=body)


def test_unknown_slug_is_404(client):
    assert client.get("/api/public/nao-existe").status_code == 404


def test_info_lists_only_active_services_and_professionals(client, tenant, professional, service):
    db.session.add(Service(tenant_id=tenant.id, name="Antigo", duration_minutes=30, price=1, active=False))
    db.session.commit()
    r = client.get(BASE)
    assert r.status_code == 200
    assert r.json["tenant"]["timezone"] == "America/Sao_Paulo"
    assert [s["name"] for s in r.json["services"]] == ["Corte"]
    assert [p["name"] for p in r.json["professionals"]] == ["Joao"]


def test_slots_cover_the_shift_in_30_minute_steps(client, professional, service):
    s = slots(client, professional, service)
    assert s[0] == "09:00" and s[-1] == "17:30" and len(s) == 18


def test_slots_skip_busy_times(client, professional, service):
    assert public_book(client, professional, service).status_code == 201
    s = slots(client, professional, service)
    assert "10:00" not in s
    assert "09:30" in s and "10:30" in s


def test_slots_respect_working_hours_and_duration(client, tenant, professional, service):
    weekday = date.fromisoformat(FUTURE_DAY).weekday()
    professional.working_hours = [
        WorkingHours(tenant_id=tenant.id, weekday=weekday, start_time=time(13), end_time=time(15))
    ]
    long = Service(tenant_id=tenant.id, name="Longo", duration_minutes=60, price=Decimal("10"))
    db.session.add(long)
    db.session.commit()
    assert slots(client, professional, service) == ["13:00", "13:30", "14:00", "14:30"]
    assert slots(client, professional, long) == ["13:00", "13:30", "14:00"]


def test_day_off_has_no_slots(client, professional, service):
    professional.working_hours = []
    db.session.commit()
    assert slots(client, professional, service) == []


def test_past_day_has_no_slots(client, professional, service):
    assert slots(client, professional, service, day=PAST_DAY) == []


def test_booking_creates_client_and_appointment(client, professional, service):
    r = public_book(client, professional, service)
    assert r.status_code == 201
    assert r.json["time"] == "10:00" and r.json["service"] == "Corte"
    appt = Appointment.query.one()
    assert appt.source == "publico" and appt.status == "confirmado"
    assert appt.client.whatsapp == "+5511987654321"


def test_booking_reuses_client_by_whatsapp(client, professional, service):
    assert public_book(client, professional, service).status_code == 201
    assert public_book(client, professional, service, time="11:00", whatsapp="+55 11 98765-4321").status_code == 201
    assert Client.query.count() == 1


def test_booking_invalid_whatsapp_is_400(client, professional, service):
    assert public_book(client, professional, service, whatsapp="999").status_code == 400


def test_booking_requires_name_and_whatsapp(client, professional, service):
    r = public_book(client, professional, service, name="", whatsapp="")
    assert r.status_code == 400
    assert set(r.json["fields"]) == {"name", "whatsapp"}


def test_booking_taken_slot_is_409(client, professional, service):
    assert public_book(client, professional, service).status_code == 201
    assert public_book(client, professional, service, whatsapp="11912345678").status_code == 409


def test_booking_outside_working_hours_is_409(client, professional, service):
    assert public_book(client, professional, service, time="20:00").status_code == 409


def test_booking_time_with_seconds_is_400(client, professional, service):
    assert public_book(client, professional, service, time="09:00:59").status_code == 400


def test_booking_name_too_long_or_not_text_is_400(client, professional, service):
    assert public_book(client, professional, service, name="x" * 121).status_code == 400
    assert public_book(client, professional, service, name=123).status_code == 400


def test_availability_absurd_date_is_400(client, professional, service):
    r = client.get(
        f"{BASE}/availability?service_id={service.id}&professional_id={professional.id}&date=9999-12-31"
    )
    assert r.status_code == 400
