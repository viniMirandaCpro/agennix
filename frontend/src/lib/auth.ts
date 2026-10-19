// Login, logout e leitura do usuario autenticado (Historia 5.1 - Flask-Login).
import { api } from "@/lib/api";
import type { Session } from "@/lib/types";

export const login = (email: string, password: string) =>
  api<Session>("/auth/login", { method: "POST", body: { email, password } });

export const logout = () => api("/auth/logout", { method: "POST" });

export const me = () => api<Session>("/auth/me");
