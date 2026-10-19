"""Entrada/saida do recurso 'service'."""
from flask_restful import abort

from app.schemas import parse_decimal, parse_int, require


def dump_service(s):
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "duration_minutes": s.duration_minutes,
        "price": str(s.price),
        "active": s.active,
    }


def load_service(data, partial=False):
    if not partial:
        require(data, "name", "duration_minutes", "price")
    out = {}
    if "name" in data:
        out["name"] = (data["name"] or "").strip()
        if not out["name"]:
            abort(400, message="Informe o nome do serviço")
    if "description" in data:
        out["description"] = data["description"] or None
    if "duration_minutes" in data:
        out["duration_minutes"] = parse_int(data["duration_minutes"], "duration_minutes")
        if out["duration_minutes"] <= 0:
            abort(400, message="A duração deve ser maior que zero")
    if "price" in data:
        out["price"] = parse_decimal(data["price"], "price")
        if out["price"] < 0:
            abort(400, message="O preço não pode ser negativo")
    if "active" in data:
        out["active"] = bool(data["active"])
    return out
