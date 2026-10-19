"""Cadastros simples: servicos, profissionais (com expediente) e busca de clientes."""
from app.extensions import db
from app.models import Client


def test_catalog_requires_session(client):
    assert client.get("/api/services").status_code == 401
    assert client.get("/api/professionals").status_code == 401
    assert client.get("/api/clients").status_code == 401


def test_create_list_and_deactivate_service(auth_client):
    r = auth_client.post(
        "/api/services", json={"name": "Barba", "duration_minutes": 30, "price": "35.5"}
    )
    assert r.status_code == 201
    sid = r.json["id"]
    assert r.json["price"] == "35.50"

    r = auth_client.put(f"/api/services/{sid}", json={"active": False})
    assert r.status_code == 200 and r.json["active"] is False
    assert [s["name"] for s in auth_client.get("/api/services").json] == ["Barba"]


def test_service_rejects_invalid_duration(auth_client):
    r = auth_client.post("/api/services", json={"name": "X", "duration_minutes": 0, "price": 10})
    assert r.status_code == 400


def test_new_professional_gets_default_working_hours(auth_client):
    r = auth_client.post("/api/professionals", json={"name": "Ana"})
    assert r.status_code == 201
    assert [w["weekday"] for w in r.json["working_hours"]] == [0, 1, 2, 3, 4, 5]
    assert r.json["working_hours"][0] == {"weekday": 0, "start_time": "09:00", "end_time": "18:00"}


def test_update_professional_replaces_working_hours(auth_client, professional):
    r = auth_client.put(
        f"/api/professionals/{professional.id}",
        json={"working_hours": [{"weekday": 2, "start_time": "10:00", "end_time": "14:00"}]},
    )
    assert r.status_code == 200
    assert r.json["working_hours"] == [{"weekday": 2, "start_time": "10:00", "end_time": "14:00"}]


def test_working_hours_end_before_start_is_400(auth_client, professional):
    r = auth_client.put(
        f"/api/professionals/{professional.id}",
        json={"working_hours": [{"weekday": 2, "start_time": "14:00", "end_time": "10:00"}]},
    )
    assert r.status_code == 400


def test_other_tenant_record_is_404(auth_client, professional):
    from app.models import Tenant, Professional

    other = Tenant(name="Outra", slug="outra")
    db.session.add(other)
    db.session.flush()
    p = Professional(tenant_id=other.id, name="Fora")
    db.session.add(p)
    db.session.commit()
    assert auth_client.put(f"/api/professionals/{p.id}", json={"name": "x"}).status_code == 404


def test_client_search_by_name_or_whatsapp(auth_client, tenant):
    db.session.add_all(
        [
            Client(tenant_id=tenant.id, name="Maria Silva", whatsapp="+5511999990001"),
            Client(tenant_id=tenant.id, name="Pedro", whatsapp="+5511988880002"),
        ]
    )
    db.session.commit()
    assert [c["name"] for c in auth_client.get("/api/clients?q=mar").json] == ["Maria Silva"]
    assert [c["name"] for c in auth_client.get("/api/clients?q=8888").json] == ["Pedro"]


def test_client_search_accepts_formatted_phone(auth_client, tenant):
    db.session.add(Client(tenant_id=tenant.id, name="Pedro", whatsapp="+5511988880002"))
    db.session.commit()
    assert [c["name"] for c in auth_client.get("/api/clients?q=(11) 98888").json] == ["Pedro"]
