// Link publico de agendamento: /agendar/{slug}. Sem login.
// Suspense obrigatorio: com cacheComponents, useParams numa rota dinamica suspende no prerender.
import { Suspense } from "react";

import BookingFlow from "@/components/booking/BookingFlow";

export default function AgendarPage() {
  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4 sm:py-10">
      <div>
        <p className="text-sm font-semibold text-indigo-600">Agennix</p>
        <h1 className="text-2xl font-bold">Agende seu horário</h1>
      </div>
      <Suspense fallback={<p className="text-sm text-gray-500">Carregando...</p>}>
        <BookingFlow />
      </Suspense>
    </main>
  );
}
