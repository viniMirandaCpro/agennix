"use client";

// Configuracoes: logins do painel e seus perfis (Historia 5.5). So o administrador acessa.
// TODO: Historia: Assinatura e Planos Recorrentes. Trocar de plano e cancelar renovacao automatica.
import { useCallback, useEffect, useState } from "react";

import { useSession } from "@/components/dashboard/session";
import Modal from "@/components/ui/Modal";
import { api, errorMessage } from "@/lib/api";
import type { Professional, Role, User } from "@/lib/types";

const ROLES: { value: Role; label: string; hint: string }[] = [
  { value: "administrador", label: "Administrador", hint: "Acesso total, inclusive cadastros e configurações" },
  { value: "atendente", label: "Atendente", hint: "Gerencia a agenda" },
  { value: "profissional", label: "Profissional", hint: "Vê só a própria agenda" },
];

type Form = {
  id?: number;
  name: string;
  email: string;
  password: string;
  role: Role;
  professionalId: string;
  active: boolean;
};

const emptyForm = (): Form => ({ name: "", email: "", password: "", role: "atendente", professionalId: "", active: true });

const toForm = (u: User): Form => ({
  id: u.id,
  name: u.name,
  email: u.email,
  password: "",
  role: u.role,
  professionalId: String(u.professional?.id ?? ""),
  active: u.active,
});

export default function ConfiguracoesPage() {
  const { user: me } = useSession();
  const [users, setUsers] = useState<User[]>([]);
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [form, setForm] = useState<Form | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    api<User[]>("/users").then(setUsers).catch((e) => setError(errorMessage(e)));
  }, []);
  useEffect(load, [load]);
  useEffect(() => {
    api<Professional[]>("/professionals").then(setProfessionals).catch(() => {});
  }, []);

  // Um profissional so pode ter um login: os ja vinculados a outro usuario saem da lista
  const taken = new Set(users.filter((u) => u.id !== form?.id).map((u) => u.professional?.id));
  const professionalOptions = professionals.filter(
    (p) => !taken.has(p.id) && (p.active || String(p.id) === form?.professionalId),
  );
  const self = form?.id === me.id;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setSaving(true);
    setError("");
    const body = {
      name: form.name,
      email: form.email,
      role: form.role,
      active: form.active,
      ...(form.password && { password: form.password }),
      ...(form.role === "profissional" && { professional_id: Number(form.professionalId) }),
    };
    try {
      if (form.id) await api(`/users/${form.id}`, { method: "PUT", body });
      else await api("/users", { method: "POST", body });
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
        <h1 className="text-2xl font-semibold">Configurações</h1>
        <button className="btn-primary" onClick={() => { setError(""); setForm(emptyForm()); }}>
          Novo usuário
        </button>
      </div>

      <h2 className="text-sm font-semibold text-gray-600">Usuários do painel</h2>
      {error && !form && <p className="text-sm text-red-600">{error}</p>}

      <div className="card divide-y divide-gray-100">
        {users.map((u) => (
          <div key={u.id} className="flex items-center justify-between gap-3 p-4">
            <div className={`min-w-0 ${u.active ? "" : "opacity-50"}`}>
              <p className="font-medium">
                {u.name}
                {u.id === me.id && <span className="text-xs text-gray-500"> (você)</span>}
                {!u.active && <span className="text-xs text-gray-500"> (inativo)</span>}
              </p>
              <p className="truncate text-sm text-gray-500">
                {u.email} · {ROLES.find((r) => r.value === u.role)?.label}
                {u.professional && ` · agenda de ${u.professional.name}`}
              </p>
            </div>
            <button className="btn" onClick={() => { setError(""); setForm(toForm(u)); }}>
              Editar
            </button>
          </div>
        ))}
      </div>

      {form && (
        <Modal title={form.id ? "Editar usuário" : "Novo usuário"} onClose={() => setForm(null)}>
          <form onSubmit={save} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="name" className="label">Nome</label>
                <input id="name" className="input" required value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div>
                <label htmlFor="email" className="label">E-mail</label>
                <input id="email" type="email" className="input" required value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })} />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="label">Senha</label>
              <input id="password" type="password" className="input" autoComplete="new-password"
                required={!form.id} minLength={8} value={form.password}
                placeholder={form.id ? "Em branco mantém a senha atual" : "Mínimo de 8 caracteres"}
                onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="role" className="label">Perfil</label>
                <select id="role" className="input" value={form.role} disabled={self}
                  onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
                  {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
                <p className="mt-1 text-xs text-gray-500">{ROLES.find((r) => r.value === form.role)?.hint}</p>
              </div>
              {form.role === "profissional" && (
                <div>
                  <label htmlFor="professional" className="label">Agenda de</label>
                  <select id="professional" className="input" required value={form.professionalId}
                    onChange={(e) => setForm({ ...form, professionalId: e.target.value })}>
                    <option value="">Selecione</option>
                    {professionalOptions.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
              )}
            </div>

            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.active} disabled={self}
                onChange={(e) => setForm({ ...form, active: e.target.checked })} />
              Ativo (pode entrar no painel)
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
