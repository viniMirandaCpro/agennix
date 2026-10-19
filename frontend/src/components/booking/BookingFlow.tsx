"use client";

// Historia 5.12: agendamento rapido pelo cliente, sem login. So nome e WhatsApp;
// so mostra horarios livres (expediente - agendamentos - passado).
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api, ApiError, errorMessage } from "@/lib/api";
import { brl, formatDay, todayIn } from "@/lib/dates";

type Info = {
  tenant: { name: string; slug: string; timezone: string };
  services: { id: number; name: string; duration_minutes: number; price: string }[];
  professionals: { id: number; name: string }[];
};

type Booked = { date: string; time: string; service: string; professional: string; price: string; tenant: string };

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="card space-y-3 p-4">
      <h2 className="flex items-center gap-2 font-semibold">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600 text-xs text-white">{n}</span>
        {title}
      </h2>
      {children}
    </section>
  );
}

const choice = (active: boolean) =>
  `rounded-md border px-3 py-2 text-left text-sm ${
    active ? "border-indigo-600 bg-indigo-50 text-indigo-800" : "border-gray-300 bg-white hover:border-indigo-400"
  }`;

export default function BookingFlow() {
  const { slug } = useParams<{ slug: string }>();
  const [info, setInfo] = useState<Info | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [serviceId, setServiceId] = useState<number | null>(null);
  const [professionalId, setProfessionalId] = useState<number | null>(null);
  const [date, setDate] = useState("");
  const [slotsResult, setSlotsResult] = useState<{ key: string; slots: string[] } | null>(null);
  const [picked, setPicked] = useState("");
  const [name, setName] = useState("");
  const [whatsapp, setWhatsapp] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [booked, setBooked] = useState<Booked | null>(null);

  useEffect(() => {
    api<Info>(`/public/${slug}`)
      .then((data) => { setInfo(data); setDate(todayIn(data.tenant.timezone)); })
      .catch((e) => (e instanceof ApiError && e.status === 404 ? setNotFound(true) : setError(errorMessage(e))));
  }, [slug]);

  const slotsKey =
    serviceId && professionalId && date
      ? new URLSearchParams({ service_id: String(serviceId), professional_id: String(professionalId), date }).toString()
      : "";

  const loadSlots = useCallback(() => {
    if (!slotsKey) return;
    api<{ slots: string[] }>(`/public/${slug}/availability?${slotsKey}`)
      .then((r) => setSlotsResult({ key: slotsKey, slots: r.slots }))
      .catch((e) => setError(errorMessage(e)));
  }, [slug, slotsKey]);
  useEffect(loadSlots, [loadSlots]);

  // Derivados: horarios de outra consulta = ainda carregando; horario escolhido so vale se seguir livre.
  const slots = slotsResult?.key === slotsKey ? slotsResult.slots : null;
  const time = slots?.includes(picked) ? picked : "";

  async function confirm(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const body = { service_id: serviceId, professional_id: professionalId, date, time, name, whatsapp };
      setBooked(await api<Booked>(`/public/${slug}/appointments`, { method: "POST", body }));
    } catch (err) {
      setError(errorMessage(err));
      if (err instanceof ApiError && err.status === 409) loadSlots();
    } finally {
      setSaving(false);
    }
  }

  if (notFound) return <p className="p-8 text-center text-gray-600">Estabelecimento não encontrado.</p>;
  if (!info) return <p className="p-8 text-center text-sm text-gray-500">{error || "Carregando..."}</p>;

  if (booked) {
    return (
      <div className="card space-y-3 p-6 text-center">
        <p className="text-4xl">✓</p>
        <h2 className="text-xl font-semibold">Agendamento confirmado!</h2>
        <p className="text-gray-700 first-letter:uppercase">
          {formatDay(booked.date)}, às {booked.time}
        </p>
        <p className="text-sm text-gray-500">
          {booked.service} com {booked.professional} · {brl(booked.price)}
        </p>
        <button className="btn" onClick={() => { setBooked(null); setPicked(""); loadSlots(); }}>
          Fazer outro agendamento
        </button>
      </div>
    );
  }

  const today = todayIn(info.tenant.timezone);

  return (
    <div className="space-y-4">
      <Step n={1} title="Escolha o serviço">
        <div className="grid gap-2 sm:grid-cols-2">
          {info.services.map((s) => (
            <button key={s.id} className={choice(s.id === serviceId)} onClick={() => setServiceId(s.id)}>
              <span className="block font-medium">{s.name}</span>
              <span className="text-gray-500">{s.duration_minutes} min · {brl(s.price)}</span>
            </button>
          ))}
        </div>
      </Step>

      {serviceId && (
        <Step n={2} title="Escolha o profissional">
          <div className="grid gap-2 sm:grid-cols-2">
            {info.professionals.map((p) => (
              <button key={p.id} className={choice(p.id === professionalId)} onClick={() => setProfessionalId(p.id)}>
                {p.name}
              </button>
            ))}
          </div>
        </Step>
      )}

      {serviceId && professionalId && (
        <Step n={3} title="Escolha o dia e o horário">
          <input type="date" className="input sm:w-auto" min={today} value={date} aria-label="Data"
            onChange={(e) => setDate(e.target.value)} />
          {slots === null ? (
            <p className="text-sm text-gray-500">Buscando horários...</p>
          ) : slots.length === 0 ? (
            <p className="text-sm text-gray-500">Nenhum horário livre neste dia. Tente outra data.</p>
          ) : (
            <div className="grid grid-cols-4 gap-2 sm:grid-cols-6">
              {slots.map((s) => (
                <button key={s} className={`${choice(s === time)} text-center`} onClick={() => setPicked(s)}>
                  {s}
                </button>
              ))}
            </div>
          )}
        </Step>
      )}

      {time && (
        <Step n={4} title="Seus dados">
          <form onSubmit={confirm} className="space-y-3">
            <div>
              <label htmlFor="name" className="label">Nome</label>
              <input id="name" className="input" required autoComplete="name" value={name}
                onChange={(e) => setName(e.target.value)} />
            </div>
            <div>
              <label htmlFor="whatsapp" className="label">WhatsApp</label>
              <input id="whatsapp" className="input" required inputMode="tel" autoComplete="tel"
                placeholder="(11) 91234-5678" value={whatsapp} onChange={(e) => setWhatsapp(e.target.value)} />
            </div>
            <button type="submit" className="btn-primary w-full" disabled={saving}>
              {saving ? "Agendando..." : `Confirmar ${time}`}
            </button>
          </form>
        </Step>
      )}

      {error && <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
    </div>
  );
}
