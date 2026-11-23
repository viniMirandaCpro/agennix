"""Configuracao da aplicacao por ambiente, lida do .env."""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    # A string "False" do .env seria truthy; compara explicitamente.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False") == "True"
    ERROR_404_HELP = False
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")
    REMINDER_HOURS_BEFORE = int(os.environ.get("REMINDER_HOURS_BEFORE", 2))


class DevConfig(Config):
    DEBUG = True


class ProdConfig(Config):
    pass


class TestConfig(Config):
    TESTING = True
    # Testes nao dependem do backend/.env nem usam credencial real
    TWILIO_ACCOUNT_SID = TWILIO_AUTH_TOKEN = TWILIO_FROM_NUMBER = ""
    REMINDER_HOURS_BEFORE = 2
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg2://agennix:agennix@localhost:5432/agennix_test",
    )
