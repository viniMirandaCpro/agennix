"""Instancias das extensoes Flask, criadas sem app (padrao factory).

O Api do Flask-RESTful e criado dentro do create_app, para que cada app de
teste tenha a sua instancia.

Atencao ao CORS: o painel Next.js envia o cookie de sessao, entao e
obrigatorio supports_credentials=True com a origem explicita
(http://localhost:3000). Curinga "*" nao funciona junto de credenciais.
"""
from flask_cors import CORS
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
cors = CORS()
