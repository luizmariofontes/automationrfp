import { useQuery } from "@tanstack/react-query";

import { getReadiness } from "../lib/api";

/** Indicador do estado da API e das dependências (Postgres, Redis). */
export function StatusApi() {
  const { data, isError, isPending } = useQuery({
    queryKey: ["health", "ready"],
    queryFn: getReadiness,
    refetchInterval: 30_000,
    retry: false,
  });

  const ok = !isError && data?.status === "ok";
  const label = isPending ? "Verificando…" : ok ? "Sistema operacional" : "Sistema indisponível";
  const title = data
    ? Object.entries(data.checks)
        .map(([nome, estado]) => `${nome}: ${estado}`)
        .join(" · ")
    : undefined;

  return (
    <span
      role="status"
      title={title}
      className="inline-flex items-center gap-2 text-sm text-tinta-suave"
    >
      <span
        aria-hidden
        className={`h-2 w-2 rounded-full ${isPending ? "bg-borda" : ok ? "bg-ok" : "bg-falha"}`}
      />
      {label}
    </span>
  );
}
