"use client";

// Formulario de agendamento do painel (Historias 5.2 e 5.8): exige cliente,
// profissional, servico, data e horario; cliente novo e cadastrado no mesmo envio.
import { useEffect, useState } from "react";

import Modal from "@/components/ui/Modal";
import { api, errorMessage } from "@/lib/api";
import type { Appointment, Client, Professional, Service } from "@/lib/types";

import { updateAppointment } from "./updateAppointment";

type Props = {
  appointment?: Appointment;
  professionals: Professional[];
  services: Service[];
  defaultDate: string;
  onSaved: () => void;
  onClose: () => void;
};

export default function AppointmentForm({ appointment, professionals, services, defaultDate, onSaved, onClose }: Props) {
  const editing = Boolean(appointment);
  const [newClient, setNewClient] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Client[]>([]);
  const [client, setClient] = useState<Client | null>(appointment?.client ?? null);
  const [clientName, setClientName] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [professionalId, setProfessionalId] = useState(String(appointment?.professional.id ?? ""));
  const [serviceId, setServiceId] = useState(String(appointment?.service.id ?? ""));
  const [date, setDate] = useState(appointment?.date ?? defaultDate);
  const [time, setTime] = useState(appointment?.time ?? "");
  const [notes, setNotes] = useState(appointment?.notes ?? "");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (editing || newClient || query.trim().length < 2) return;
    const timer = setTimeout(() => {
      api<Client[]>(`/clients?q=${encodeURIComponent(query.trim())}`).then(setResults).catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [query, editing, newClient]);

  // Inativos so aparecem se ja forem os do agendamento em edicao.
  const professionalOptions = professionals.filter((p) => p.active || String(p.id) === professionalId);
  const serviceOptions = services.filter((s) => s.active || String(s.id) === serviceId);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!editing && !newClient && !client) {
      setError("Escolha um cliente ou cadastre um novo.");
      return;
    }
    const body: Record<string, unknown> = {
      professional_id: Number(professionalId),
      service_id: Number(serviceId),
      date,
      time,
      notes,
    };
    setSaving(true);
    try {
      if (appointment) {
        if (!(await updateAppointment(appointment.id, body))) return setSaving(false);
      } else {
        if (newClient) body.client = { name: clientName, whatsapp };
        else body.client_id = client!.id;
        await api("/appointments", { method: "POST", body });
      }
      onSaved();
    } catch (err) {
      setError(errorMessage(err));
      setSaving(false);
    }
  }

  return (
    <Modal title={editing ? "Editar agendamento" : "Novo agendamento"} onClose={onClose}>
      <form onSubmit={onSubmit} className="space-y-4">
        <fieldset>
          <legend className="label">Cliente</legend>
          {editing || client ? (
            <div className="flex items-center justify-between rounded-md bg-gray-50 px-3 py-2 text-sm">
              <span>
                {client?.name} <span className="text-gray-500">{client?.whatsapp}</span>
              </span>
              {!editing && (
                <button type="button" className="text-indigo-600 hover:underline" onClick={() => setClient(null)}>
                  Trocar
                </button>
              )}
            </div>
          ) : newClient ? (
            <div className="space-y-2">
              <input className="input" placeholder="Nome" aria-label="Nome do cliente" required
                value={clientName} onChange={(e) => setClientName(e.target.value)} />
              <input className="input" placeholder="WhatsApp (11) 91234-5678" aria-label="WhatsApp do cliente"
                inputMode="tel" required value={whatsapp} onChange={(e) => setWhatsapp(e.target.value)} />
              <button type="button" className="text-sm text-indigo-600 hover:underline" onClick={() => setNewClient(false)}>
                Buscar cliente cadastrado
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <input className="input" placeholder="Buscar por nome ou WhatsApp" aria-label="Buscar cliente"
                value={query} onChange={(e) => setQuery(e.target.value)} />
              {results.length > 0 && (
                <ul className="max-h-40 divide-y divide-gray-100 overflow-y-auto rounded-md border border-gray-200">
                  {results.map((c) => (
                    <li key={c.id}>
                      <button type="button" className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50"
                        onClick={() => setClient(c)}>
                        {c.name} <span className="text-gray-500">{c.whatsapp}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <button type="button" className="text-sm text-indigo-600 hover:underline" onClick={() => setNewClient(true)}>
                + Cadastrar cliente novo
              </button>
            </div>
          )}
        </fieldset>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="professional" className="label">Profissional</label>
            <select id="professional" className="input" required value={professionalId}
              onChange={(e) => setProfessionalId(e.target.value)}>
              <option value="">Selecione</option>
              {professionalOptions.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor="service" className="label">Serviço</label>
            <select id="service" className="input" required value={serviceId}
              onChange={(e) => setServiceId(e.target.value)}>
              <option value="">Selecione</option>
              {serviceOptions.map((s) => (
                <option key={s.id} value={s.id}>{s.name} ({s.duration_minutes} min)</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="date" className="label">Data</label>
            <input id="date" type="date" className="input" required value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div>
            <label htmlFor="time" className="label">Horário</label>
            <input id="time" type="time" step={300} className="input" required value={time}
              onChange={(e) => setTime(e.target.value)} />
          </div>
        </div>
        <div>
          <label htmlFor="notes" className="label">Observações</label>
          <textarea id="notes" rows={2} className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
        <p className="text-xs text-gray-500">O término é calculado pela duração do serviço.</p>
        {error && <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn" onClick={onClose}>Cancelar</button>
          <button type="submit" className="btn-primary" disabled={saving}>Salvar</button>
        </div>
      </form>
    </Modal>
  );
}
