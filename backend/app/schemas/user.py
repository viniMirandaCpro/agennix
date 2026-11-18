"""Entrada/saida do recurso 'user' (logins do painel e seus perfis)."""
from email_validator import EmailNotValidError, validate_email
from flask_restful import abort

from app.models.user import ROLES
from app.schemas import parse_int, require

MIN_PASSWORD = 8


def dump_user(u):
    p = u.professional
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "role": u.role,
        "active": u.active,
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        "professional": {"id": p.id, "name": p.name} if p else None,
    }


def load_user(data, partial=False):
    """Senha vazia no PUT mantem a atual."""
    if not partial:
        require(data, "name", "email", "password", "role")
    out = {}
    if "name" in data:
        out["name"] = str(data["name"] or "").strip()
        if not out["name"]:
            abort(400, message="Informe o nome")
        if len(out["name"]) > 120:
            abort(400, message="Nome muito longo (máximo 120 caracteres)")
    if "email" in data:
        try:
            # Minusculo inteiro: o login compara com email.strip().lower()
            email = str(data["email"] or "").strip()
            out["email"] = validate_email(email, check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            abort(400, message="E-mail inválido")
    if data.get("password"):
        if not isinstance(data["password"], str) or len(data["password"]) < MIN_PASSWORD:
            abort(400, message=f"A senha deve ter ao menos {MIN_PASSWORD} caracteres")
        out["password"] = data["password"]
    if "role" in data:
        if data["role"] not in ROLES:
            abort(400, message="Perfil inválido")
        out["role"] = data["role"]
    if "active" in data:
        out["active"] = bool(data["active"])
    if data.get("professional_id") not in (None, ""):
        out["professional_id"] = parse_int(data["professional_id"], "professional_id")
    return out
