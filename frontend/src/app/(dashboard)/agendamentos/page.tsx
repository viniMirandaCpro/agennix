"use client";

// Agenda (Historias 5.2, 5.4 e 5.8): lista por dia, alternando dia/semana/mes,
// filtros por profissional e servico, status visual e acoes rapidas.
import { useEffect, useMemo, useState } from "react";

import AppointmentForm from "@/components/dashboard/AppointmentForm";
import { useSession } from "@/components/dashboard/session";
import { updateAppointment } from "@/components/dashboard/updateAppointment";
import { api, errorMessage } from "@/lib/api";
import { formatDay, formatPeriod, periodOf, shift, todayIn, type View } from "@/lib/dates";
import type { Appointment, AppointmentStatus, Professional, Service } from "@/lib/types";

const STATUS: Record<AppointmentStatus, { label: string; className: string }> = {
  pendente: { label: "Pendente", className: "bg-yellow-100 text-yellow-800" },
  confirmado: { label: "Confirmado", className: "bg-blue-100 text-blue-800" },
  em_atendimento: { label: "Em atendimento", className: "bg-purple-100 text-purple-800" },
  concluido: { label: "Concluído", className: "bg-green-100 text-green-800" },
  nao_compareceu: { label: "Não compareceu", className: "bg-amber-100 text-amber-800" },
  cancelado: { label: "Cancelado", className: "bg-gray-200 text-gray-600" },
};

const VIEWS: { value: View; label: string }[] = [
  { value: "dia", label: "Dia" },
  { value: "semana", label: "Semana" },
  { value: "mes", label: "Mês" },
];

const endTime = (a: Appointment) => a.ends_at.slice(11, 16);

export default function AgendamentosPage() {
  const { tenant } = useSession();
  const today = todayIn(tenant.timezone);
  const [view, setView] = useState<View>("dia");
  const [anchor, setAnchor] = useState(today);
  const [professionalId, setProfessionalId] = useState("");
  const [serviceId, setServiceId] = useState("");
  const [result, setResult] = useState<{ query: string; items: Appointment[] } | null>(null);
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [modal, setModal] = useState<{ appointment?: Appointment } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Professional[]>("/professionals").then(setProfessionals).catch(() => {});
    api<Service[]>("/services").then(setServices).catch(() => {});
  }, []);

  const query = useMemo(() => {
    const params = new URLSearchParams(periodOf(view, anchor));
    if (professionalId) params.set("professional_id", professionalId);
    if (serviceId) params.set("service_id", serviceId);
    return params.toString();
  }, [view, anchor, professionalId, serviceId]);

  const [version, setVersion] = useState(0);
  const reload = () => setVersion((v) => v + 1);

  useEffect(() => {
    let stale = false; // troca rapida de filtro: a resposta da consulta antiga e descartada
    api<Appointment[]>(`/appointments?${query}`)
      .then((items) => { if (!stale) { setResult({ query, items }); setError(""); } })
      .catch((e) => { if (!stale) setError(errorMessage(e)); });
    return () => { stale = true; };
  }, [query, version]);

  // Carregando = o resultado na tela ainda e de outra consulta.
  const loading = result?.query !== query;
  const appointments = useMemo(() => result?.items ?? [], [result]);

  const byDay = useMemo(() => {
    const groups = new Map<string, Appointment[]>();
    for (const a of appointments) groups.set(a.date, [...(groups.get(a.date) ?? []), a]);
    return [...groups.entries()];
  }, [appointments]);

  async function act(a: Appointment, body: Record<string, unknown>) {
    try {
      if (await updateAppointment(a.id, body)) reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  function cancel(a: Appointment) {
    const reason = window.prompt(`Cancelar o horário de ${a.client.name}? Motivo (opcional):`);
    if (reason !== null) act(a, { status: "cancelado", cancellation_reason: reason });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Agendamentos</h1>
        <button className="btn-primary" onClick={() => setModal({})}>Novo agendamento</button>
      </div>

      <div className="card flex flex-wrap items-center gap-3 p-3">
        <div className="inline-flex rounded-md border border-gray-300" role="group" aria-label="Período">
          {VIEWS.map((v) => (
            <button key={v.value} onClick={() => setView(v.value)} aria-pressed={view === v.value}
              className={`px-3 py-1.5 text-sm first:rounded-l-md last:rounded-r-md ${
                view === v.value ? "bg-indigo-600 text-white" : "bg-white text-gray-700 hover:bg-gray-50"
              }`}>
              {v.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1">
          <button className="btn px-2" aria-label="Anterior" onClick={() => setAnchor(shift(view, anchor, -1))}>‹</button>
          <button className="btn" onClick={() => setAnchor(today)}>Hoje</button>
          <button className="btn px-2" aria-label="Próximo" onClick={() => setAnchor(shift(view, anchor, 1))}>›</button>
        </div>
        <p className="text-sm font-medium text-gray-700 first-letter:uppercase">{formatPeriod(view, anchor)}</p>
        <div className="flex flex-1 flex-wrap justify-end gap-2">
          <select className="input w-auto" aria-label="Filtrar por profissional" value={professionalId}
            onChange={(e) => setProfessionalId(e.target.value)}>
            <option value="">Todos os profissionais</option>
            {professionals.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select className="input w-auto" aria-label="Filtrar por serviço" value={serviceId}
            onChange={(e) => setServiceId(e.target.value)}>
            <option value="">Todos os serviços</option>
            {services.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        </div>
      </div>

      {error && <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {!loading && byDay.length === 0 && (
        <p className="card p-6 text-center text-sm text-gray-500">Nenhum agendamento neste período.</p>
      )}

      {loading && <p className="text-sm text-gray-500">Carregando...</p>}

      {!loading && byDay.map(([day, items]) => (
        <section key={day} className="space-y-2">
          {view !== "dia" && (
            <h2 className={`text-sm font-semibold first-letter:uppercase ${day === today ? "text-indigo-600" : "text-gray-600"}`}>
              {formatDay(day)}
            </h2>
          )}
          <ul className="card divide-y divide-gray-100">
            {items.map((a) => {
              const cancelled = a.status === "cancelado";
              return (
                <li key={a.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 p-4">
                  <p className={`w-28 font-mono text-sm ${cancelled ? "text-gray-400 line-through" : ""}`}>
                    {a.time}–{endTime(a)}
                  </p>
                  <div className={`min-w-0 flex-1 ${cancelled ? "opacity-60" : ""}`}>
                    <p className="font-medium">
                      {a.client.name}{" "}
                      {a.source === "publico" && (
                        <span className="ml-1 rounded bg-indigo-50 px-1.5 py-0.5 text-xs text-indigo-700">link público</span>
                      )}
                    </p>
                    <p className="text-sm text-gray-500">
                      {a.service.name} · {a.professional.name}
                      {a.client.whatsapp && ` · ${a.client.whatsapp}`}
                    </p>
                    {cancelled && a.cancellation_reason && (
                      <p className="text-xs text-gray-500">Motivo: {a.cancellation_reason}</p>
                    )}
                  </div>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS[a.status].className}`}>
                    {STATUS[a.status].label}
                  </span>
                  {!cancelled && (
                    <div className="flex flex-wrap gap-1">
                      <button className="btn py-1" onClick={() => setModal({ appointment: a })}>Editar</button>
                      {a.status === "confirmado" && (
                        <>
                          <button className="btn py-1" onClick={() => act(a, { status: "concluido" })}>Concluir</button>
                          <button className="btn py-1" onClick={() => act(a, { status: "nao_compareceu" })}>Faltou</button>
                        </>
                      )}
                      <button className="btn py-1 text-red-600" onClick={() => cancel(a)}>Cancelar</button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      ))}

      {modal && (
        <AppointmentForm
          appointment={modal.appointment}
          professionals={professionals}
          services={services}
          defaultDate={anchor}
          onClose={() => setModal(null)}
          onSaved={() => { setModal(null); reload(); }}
        />
      )}
    </div>
  );
}
