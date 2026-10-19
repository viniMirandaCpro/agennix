"""Validacao de entrada e serializacao de saida, um modulo por recurso.

Erros de validacao viram 400 com {"message": ...} via flask_restful.abort.
"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import request
from flask_restful import abort


def json_body():
    return request.get_json(silent=True) or {}


def require(data, *fields):
    missing = [f for f in fields if data.get(f) in (None, "")]
    if missing:
        abort(400, message="Campos obrigatórios ausentes: " + ", ".join(missing), fields=missing)


# Faixa sensata: evita OverflowError em date.max + 1 dia nos calculos de agenda.
MIN_DATE, MAX_DATE = date(2000, 1, 1), date(2100, 12, 31)


def parse_date(value, field):
    try:
        day = date.fromisoformat(value)
    except (TypeError, ValueError):
        abort(400, message=f"Data inválida em '{field}' (use AAAA-MM-DD)")
    if not MIN_DATE <= day <= MAX_DATE:
        abort(400, message=f"Data fora do período permitido em '{field}'")
    return day


def parse_time(value, field):
    try:
        # So HH:MM: segundos tirariam o agendamento da grade de horarios.
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError):
        abort(400, message=f"Horário inválido em '{field}' (use HH:MM)")


def parse_int(value, field):
    try:
        return int(value)
    except (TypeError, ValueError):
        abort(400, message=f"Número inválido em '{field}'")


def parse_decimal(value, field):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        abort(400, message=f"Valor inválido em '{field}'")
