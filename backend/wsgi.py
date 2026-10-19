"""Entrypoint WSGI usado pelo gunicorn e pelo `flask run`."""
from app import create_app

app = create_app()
