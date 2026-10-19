// Tipos espelhando as respostas do backend (backend/app/schemas/).

export type Session = {
  user: { id: number; name: string; email: string; role: string };
  tenant: { id: number; name: string; slug: string; timezone: string };
};

export type Service = {
  id: number;
  name: string;
  description: string | null;
  duration_minutes: number;
  price: string;
  active: boolean;
};

export type WorkingHour = { weekday: number; start_time: string; end_time: string };

export type Professional = {
  id: number;
  name: string;
  nickname: string | null;
  phone: string | null;
  active: boolean;
  working_hours: WorkingHour[];
};

export type Client = { id: number; name: string; whatsapp: string | null; email: string | null };

export type AppointmentStatus =
  | "pendente"
  | "confirmado"
  | "em_atendimento"
  | "concluido"
  | "cancelado"
  | "nao_compareceu";

export type Appointment = {
  id: number;
  status: AppointmentStatus;
  source: "painel" | "publico" | "api";
  starts_at: string;
  ends_at: string;
  date: string; // AAAA-MM-DD no fuso do estabelecimento
  time: string; // HH:MM no fuso do estabelecimento
  price_charged: string;
  notes: string | null;
  cancellation_reason: string | null;
  client: Client;
  professional: { id: number; name: string };
  service: { id: number; name: string; duration_minutes: number };
};
