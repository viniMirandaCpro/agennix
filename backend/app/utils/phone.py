"""Validacao e normalizacao de numeros de WhatsApp para E.164."""
import phonenumbers
from flask_restful import abort


def normalize_whatsapp(raw):
    """'(11) 91234-5678' -> '+5511912345678'. Numero invalido vira 400."""
    try:
        number = phonenumbers.parse(str(raw or ""), "BR")
    except phonenumbers.NumberParseException:
        number = None
    if number is None or not phonenumbers.is_valid_number(number):
        abort(400, message="Número de WhatsApp inválido")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
