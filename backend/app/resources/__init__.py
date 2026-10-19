"""Registro central dos recursos Flask-RESTful (prefixo /api, aplicado no create_app)."""
from app.resources.appointments import AppointmentItem, AppointmentList
from app.resources.auth import Login, Logout, Me
from app.resources.clients import ClientList
from app.resources.professionals import ProfessionalItem, ProfessionalList
from app.resources.public_booking import PublicAvailability, PublicBooking, PublicInfo
from app.resources.services import ServiceItem, ServiceList


def register_resources(api):
    api.add_resource(Login, "/auth/login")
    api.add_resource(Logout, "/auth/logout")
    api.add_resource(Me, "/auth/me")
    api.add_resource(ServiceList, "/services")
    api.add_resource(ServiceItem, "/services/<int:service_id>")
    api.add_resource(ProfessionalList, "/professionals")
    api.add_resource(ProfessionalItem, "/professionals/<int:professional_id>")
    api.add_resource(ClientList, "/clients")
    api.add_resource(AppointmentList, "/appointments")
    api.add_resource(AppointmentItem, "/appointments/<int:appointment_id>")
    api.add_resource(PublicInfo, "/public/<string:slug>")
    api.add_resource(PublicAvailability, "/public/<string:slug>/availability")
    api.add_resource(PublicBooking, "/public/<string:slug>/appointments")
