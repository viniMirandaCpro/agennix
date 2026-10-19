import { api, ApiError } from "@/lib/api";
import type { Appointment } from "@/lib/types";

// Historia 5.2.3: alterar ou cancelar agendamento passado exige confirmacao.
// Devolve null se o usuario desistir na confirmacao.
export async function updateAppointment(id: number, body: Record<string, unknown>): Promise<Appointment | null> {
  try {
    return await api<Appointment>(`/appointments/${id}`, { method: "PUT", body });
  } catch (err) {
    if (!(err instanceof ApiError) || err.code !== "past_requires_confirmation") throw err;
    if (!window.confirm("Este agendamento já passou. Deseja alterar mesmo assim?")) return null;
    return api<Appointment>(`/appointments/${id}`, { method: "PUT", body: { ...body, confirm_past: true } });
  }
}
