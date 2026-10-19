"""Entrada/saida do recurso 'professional' (com o expediente embutido)."""
from flask_restful import abort

from app.schemas import parse_int, parse_time, require


def dump_professional(p):
    return {
        "id": p.id,
        "name": p.name,
        "nickname": p.nickname,
        "phone": p.phone,
        "active": p.active,
        "working_hours": [
            {
                "weekday": w.weekday,
                "start_time": w.start_time.strftime("%H:%M"),
                "end_time": w.end_time.strftime("%H:%M"),
            }
            for w in p.working_hours
        ],
    }


def load_working_hours(rows):
    if not isinstance(rows, list):
        abort(400, message="'working_hours' deve ser uma lista")
    out = []
    for row in rows:
        weekday = parse_int(row.get("weekday"), "weekday")
        start = parse_time(row.get("start_time"), "start_time")
        end = parse_time(row.get("end_time"), "end_time")
        if not 0 <= weekday <= 6:
            abort(400, message="Dia da semana deve ir de 0 (segunda) a 6 (domingo)")
        if end <= start:
            abort(400, message="O fim do expediente deve ser depois do início")
        out.append((weekday, start, end))
    return out


def load_professional(data, partial=False):
    if not partial:
        require(data, "name")
    out = {}
    if "name" in data:
        out["name"] = (data["name"] or "").strip()
        if not out["name"]:
            abort(400, message="Informe o nome do profissional")
    for field in ("nickname", "phone"):
        if field in data:
            out[field] = data[field] or None
    if "active" in data:
        out["active"] = bool(data["active"])
    if "working_hours" in data:
        out["working_hours"] = load_working_hours(data["working_hours"])
    return out
