// node --test (Node >= 22.18 roda .ts direto). Sem dependencias extras.
import assert from "node:assert/strict";
import { test } from "node:test";

import { addDays, periodOf, shift } from "./dates.ts";

test("semana vai de segunda a domingo", () => {
  // 2026-10-18 e domingo
  assert.deepEqual(periodOf("semana", "2026-10-18"), { start: "2026-10-12", end: "2026-10-18" });
  assert.deepEqual(periodOf("semana", "2026-10-19"), { start: "2026-10-19", end: "2026-10-25" });
});

test("mes cobre do primeiro ao ultimo dia, inclusive fevereiro", () => {
  assert.deepEqual(periodOf("mes", "2028-02-10"), { start: "2028-02-01", end: "2028-02-29" });
});

test("navegacao atravessa virada de mes e de ano", () => {
  assert.equal(addDays("2026-12-31", 1), "2027-01-01");
  assert.equal(shift("mes", "2026-12-15", 1), "2027-01-01");
  assert.equal(shift("semana", "2026-10-30", 1), "2026-11-06");
});
