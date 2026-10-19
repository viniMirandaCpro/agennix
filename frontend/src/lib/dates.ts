// Datas como strings "AAAA-MM-DD" no fuso do estabelecimento. A aritmetica usa
// UTC puro para que o fuso do navegador nunca desloque o dia.

export type View = "dia" | "semana" | "mes";

const toDate = (iso: string) => new Date(`${iso}T00:00:00Z`);
const toIso = (d: Date) => d.toISOString().slice(0, 10);

export function todayIn(timeZone: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone }).format(new Date());
}

export function addDays(iso: string, days: number): string {
  const d = toDate(iso);
  d.setUTCDate(d.getUTCDate() + days);
  return toIso(d);
}

export function periodOf(view: View, anchor: string): { start: string; end: string } {
  if (view === "dia") return { start: anchor, end: anchor };
  const d = toDate(anchor);
  if (view === "semana") {
    const monday = addDays(anchor, -((d.getUTCDay() + 6) % 7));
    return { start: monday, end: addDays(monday, 6) };
  }
  const first = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1));
  const last = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0));
  return { start: toIso(first), end: toIso(last) };
}

export function shift(view: View, anchor: string, direction: 1 | -1): string {
  if (view === "dia") return addDays(anchor, direction);
  if (view === "semana") return addDays(anchor, 7 * direction);
  const d = toDate(anchor);
  return toIso(new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + direction, 1)));
}

export function formatDay(iso: string, options: Intl.DateTimeFormatOptions = {}): string {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "UTC",
    weekday: "long",
    day: "numeric",
    month: "long",
    ...options,
  }).format(toDate(iso));
}

export function formatPeriod(view: View, anchor: string): string {
  const { start, end } = periodOf(view, anchor);
  if (view === "dia") return formatDay(start);
  if (view === "mes") return formatDay(start, { weekday: undefined, day: undefined, year: "numeric" });
  const short = { weekday: undefined, month: "short" } as const;
  return `${formatDay(start, short)} – ${formatDay(end, short)}`;
}

export const brl = (value: string | number) =>
  Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
