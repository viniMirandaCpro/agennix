"use client";

import { createContext, useContext } from "react";

import type { Session } from "@/lib/types";

// Preenchido pelo layout do painel depois que /auth/me confirma a sessao.
export const SessionContext = createContext<Session | null>(null);

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession fora do painel autenticado");
  return session;
}
