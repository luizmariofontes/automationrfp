type Props = { titulo: string; descricao: string; sprint: number };

/** Página provisória das áreas que ainda serão construídas. */
export function EmBreve({ titulo, descricao, sprint }: Props) {
  return (
    <section className="max-w-2xl">
      <h1 className="text-2xl font-semibold">{titulo}</h1>
      <p className="mt-2 text-tinta-suave">{descricao}</p>
      <p className="mt-6 inline-block rounded-md border border-borda bg-white px-3 py-2 text-sm text-tinta-suave">
        Disponível a partir do sprint {sprint}.
      </p>
    </section>
  );
}
