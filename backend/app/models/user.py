"""Usuario do sistema. Herda UserMixin do Flask-Login.

Perfil em 'role' - nao ha tabela Role. Email unico global. Ver docs/modelagem.md secoes 3.2 e 4.4.
"""
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin


class User(UserMixin, TenantMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="administrador")
    active = db.Column(db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime(timezone=True))

    tenant = db.relationship("Tenant")

    __table_args__ = (
        db.CheckConstraint(
            "role IN ('administrador','atendente','profissional')", name="ck_users_role"
        ),
    )

    @property
    def is_active(self):
        return self.active

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
