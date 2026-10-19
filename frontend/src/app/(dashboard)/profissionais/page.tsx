"use client";

// Cadastro de profissionais + expediente semanal (base dos horarios livres do link publico).
// ponytail: um turno por dia na tela; um turno partido salvo no banco vira um turno so ao editar aqui.
import { useCallback, useEffect, useState } from "react";

import Modal from "@/components/ui/Modal";
import { api, errorMessage } from "@/lib/api";
import type { Professional } from "@/lib/types";

const WEEKDAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];

type Day = { on: boolean; start: string; end: string };
type Form = { id?: number; name: string; nickname: string; active: boolean; days: Day[] };

const defaultDays = (): Day[] => WEEKDAYS.map((_, i) => ({ on: i < 6, start: "09:00", end: "18:00" }));

function toForm(p: Professional): Form {
  const days = WEEKDAYS.map((_, i) => {
    const shift = p.working_hours.find((w) => w.weekday === i);
    return shift ? { on: true, start: shift.start_time, end: shift.end_time } : { on: false, start: "09:00", end: "18:00" };
  });
  return { id: p.id, name: p.name, nickname: p.nickname ?? "", active: p.active, days };
}

function summary(p: Professional) {
  if (p.working_hours.length === 0) return "Sem expediente";
  return p.working_hours
    .map((w) => `${WEEKDAYS[w.weekday].slice(0, 3)} ${w.start_time}-${w.end_time}`)
    .join(" · ");
}

export default function ProfissionaisPage() {
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [form, setForm] = useState<Form | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    api<Professional[]>("/professionals").then(setProfessionals).catch((e) => setError(errorMessage(e)));
  }, []);
  useEffect(load, [load]);

  function setDay(i: number, patch: Partial<Day>) {
    if (!form) return;
    setForm({ ...form, days: form.days.map((d, j) => (j === i ? { ...d, ...patch } : d)) });
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    setError("");
    const body = {
      name: form.name,
      nickname: form.nickname,
      active: form.active,
      working_hours: form.days.flatMap((d, i) => (d.on ? [{ weekday: i, start_time: d.start, end_time: d.end }] : [])),
    };
    try {
      if (form.id) await api(`/professionals/${form.id}`, { method: "PUT", body });
      else await api("/professionals", { method: "POST", body });
      setForm(null);
      load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Profissionais</h1>
        <button
          className="btn-primary"
          onClick={() => { setError(""); setForm({ name: "", nickname: "", active: true, days: defaultDays() }); }}
        >
          Novo profissional
        </button>
      </div>

      {error && !form && <p className="text-sm text-red-600">{error}</p>}

      <div className="card divide-y divide-gray-100">
        {professionals.length === 0 && <p className="p-4 text-sm text-gray-500">Nenhum profissional cadastrado.</p>}
        {professionals.map((p) => (
          <div key={p.id} className="flex items-center justify-between gap-3 p-4">
            <div className={`min-w-0 ${p.active ? "" : "opacity-50"}`}>
              <p className="font-medium">
                {p.name}
                {p.nickname && <span className="text-gray-500"> ({p.nickname})</span>}
                {!p.active && <span className="text-xs text-gray-500"> (inativo)</span>}
              </p>
              <p className="truncate text-sm text-gray-500">{summary(p)}</p>
            </div>
            <button className="btn" onClick={() => { setError(""); setForm(toForm(p)); }}>
              Editar
            </button>
          </div>
        ))}
      </div>

      {form && (
        <Modal title={form.id ? "Editar profissional" : "Novo profissional"} onClose={() => setForm(null)}>
          <form onSubmit={save} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="name" className="label">Nome</label>
                <input id="name" className="input" required value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div>
                <label htmlFor="nickname" className="label">Apelido</label>
                <input id="nickname" className="input" value={form.nickname}
                  onChange={(e) => setForm({ ...form, nickname: e.target.value })} />
              </div>
            </div>

            <fieldset>
              <legend className="label">Expediente</legend>
              <div className="space-y-2">
                {WEEKDAYS.map((day, i) => (
                  <div key={day} className="flex items-center gap-2">
                    <label className="flex w-28 items-center gap-2 text-sm">
                      <input type="checkbox" checked={form.days[i].on}
                        onChange={(e) => setDay(i, { on: e.target.checked })} />
                      {day}
                    </label>
                    <input type="time" aria-label={`Início ${day}`} className="input" disabled={!form.days[i].on}
                      value={form.days[i].start} onChange={(e) => setDay(i, { start: e.target.value })} />
                    <span className="text-gray-400">até</span>
                    <input type="time" aria-label={`Fim ${day}`} className="input" disabled={!form.days[i].on}
                      value={form.days[i].end} onChange={(e) => setDay(i, { end: e.target.value })} />
                  </div>
                ))}
              </div>
            </fieldset>

            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.active}
                onChange={(e) => setForm({ ...form, active: e.target.checked })} />
              Ativo (aparece na agenda e no link público)
            </label>
            {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
            <div className="flex justify-end gap-2">
              <button type="button" className="btn" onClick={() => setForm(null)}>Cancelar</button>
              <button type="submit" className="btn-primary" disabled={saving}>Salvar</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
