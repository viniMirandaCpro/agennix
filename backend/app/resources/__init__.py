"""Registro central dos recursos Flask-RESTful (prefixo /api, aplicado no create_app)."""
from app.resources.auth import Login, Logout, Me


def register_resources(api):
    api.add_resource(Login, "/auth/login")
    api.add_resource(Logout, "/auth/logout")
    api.add_resource(Me, "/auth/me")
