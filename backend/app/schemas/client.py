"""Saida do recurso 'client'."""


def dump_client(c):
    return {"id": c.id, "name": c.name, "whatsapp": c.whatsapp, "email": c.email}
