"use client";

// Guarda de sessao do painel: sem sessao valida, volta para /login (Historia 5.1).
// Menu por perfil (Historia 5.5); a garantia de acesso e do backend (403).
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { SessionContext } from "@/components/dashboard/session";
import { logout, me } from "@/lib/auth";
import type { Role, Session } from "@/lib/types";

const ALL: Role[] = ["administrador", "atendente", "profissional"];
const ADMIN: Role[] = ["administrador"];

const NAV = [
  { href: "/agendamentos", label: "Agendamentos", roles: ALL },
  { href: "/profissionais", label: "Profissionais", roles: ADMIN },
  { href: "/servicos", label: "Serviços", roles: ADMIN },
  { href: "/configuracoes", label: "Configurações", roles: ADMIN },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    me()
      .then(setSession)
      .catch(() => router.replace("/login"));
  }, [router]);

  const nav = session ? NAV.filter((item) => item.roles.includes(session.user.role)) : [];
  const forbidden = !!session && NAV.some((item) => pathname.startsWith(item.href) && !nav.includes(item));

  useEffect(() => {
    if (forbidden) router.replace("/agendamentos");
  }, [forbidden, router]);

  async function onLogout() {
    await logout().catch(() => {});
    router.replace("/login");
  }

  if (!session || forbidden) {
    return <p className="p-8 text-sm text-gray-500">Carregando...</p>;
  }

  return (
    <SessionContext value={session}>
      <div className="flex min-h-screen flex-col md:flex-row">
        <aside className="border-b border-gray-200 bg-white md:w-56 md:border-r md:border-b-0">
          <div className="flex items-center justify-between px-4 py-4 md:block">
            <div>
              <p className="text-lg font-bold text-indigo-600">Agennix</p>
              <p className="text-xs text-gray-500">{session.tenant.name}</p>
            </div>
            <button onClick={onLogout} className="text-sm text-gray-500 hover:text-gray-800 md:hidden">
              Sair
            </button>
          </div>
          <nav className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-col md:pb-0">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-md px-3 py-2 text-sm whitespace-nowrap ${
                  pathname.startsWith(item.href)
                    ? "bg-indigo-50 font-medium text-indigo-700"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="mt-6 hidden border-t border-gray-100 px-4 py-4 md:block">
            <p className="truncate text-xs text-gray-500">{session.user.email}</p>
            <button onClick={onLogout} className="mt-1 text-sm text-gray-600 hover:text-gray-900">
              Sair
            </button>
          </div>
        </aside>
        <main className="min-w-0 flex-1 p-4 md:p-8">{children}</main>
      </div>
    </SessionContext>
  );
}
