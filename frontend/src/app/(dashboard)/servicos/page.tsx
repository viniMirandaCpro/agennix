"use client";

// Cadastro de servicos: nome, duracao (alimenta o horario de termino) e preco.
import { useCallback, useEffect, useState } from "react";

import Modal from "@/components/ui/Modal";
import { api, errorMessage } from "@/lib/api";
import { brl } from "@/lib/dates";
import type { Service } from "@/lib/types";

type Form = { id?: number; name: string; duration_minutes: string; price: string; active: boolean };
const EMPTY: Form = { name: "", duration_minutes: "30", price: "", active: true };

export default function ServicosPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [form, setForm] = useState<Form | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    api<Service[]>("/services").then(setServices).catch((e) => setError(errorMessage(e)));
  }, []);
  useEffect(load, [load]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    setError("");
    const body = { ...form, duration_minutes: Number(form.duration_minutes), price: form.price.replace(",", ".") };
    try {
      if (form.id) await api(`/services/${form.id}`, { method: "PUT", body });
      else await api("/services", { method: "POST", body });
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
        <h1 className="text-2xl font-semibold">Serviços</h1>
        <button className="btn-primary" onClick={() => { setError(""); setForm(EMPTY); }}>
          Novo serviço
        </button>
      </div>

      {error && !form && <p className="text-sm text-red-600">{error}</p>}

      <div className="card divide-y divide-gray-100">
        {services.length === 0 && <p className="p-4 text-sm text-gray-500">Nenhum serviço cadastrado.</p>}
        {services.map((s) => (
          <div key={s.id} className="flex items-center justify-between gap-3 p-4">
            <div className={s.active ? "" : "opacity-50"}>
              <p className="font-medium">
                {s.name} {!s.active && <span className="text-xs text-gray-500">(inativo)</span>}
              </p>
              <p className="text-sm text-gray-500">
                {s.duration_minutes} min · {brl(s.price)}
              </p>
            </div>
            <button
              className="btn"
              onClick={() => {
                setError("");
                setForm({ id: s.id, name: s.name, duration_minutes: String(s.duration_minutes), price: s.price, active: s.active });
              }}
            >
              Editar
            </button>
          </div>
        ))}
      </div>

      {form && (
        <Modal title={form.id ? "Editar serviço" : "Novo serviço"} onClose={() => setForm(null)}>
          <form onSubmit={save} className="space-y-4">
            <div>
              <label htmlFor="name" className="label">Nome</label>
              <input id="name" className="input" required value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="duration" className="label">Duração (min)</label>
                <input id="duration" type="number" min={5} step={5} className="input" required
                  value={form.duration_minutes}
                  onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })} />
              </div>
              <div>
                <label htmlFor="price" className="label">Preço (R$)</label>
                <input id="price" inputMode="decimal" className="input" required placeholder="45,00"
                  value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.active}
                onChange={(e) => setForm({ ...form, active: e.target.checked })} />
              Ativo (aparece para agendamento)
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
