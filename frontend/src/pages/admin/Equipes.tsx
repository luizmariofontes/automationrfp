import { type FormEvent, useState } from "react";

import { AreaTexto, Botao, Campo, ErroApi, EstadoLista, Selo } from "../../components/ui";
import {
  type Equipe,
  useDefinirMembro,
  useEquipes,
  useRemoverMembro,
  useSalvarEquipe,
  useUsuarios,
} from "../../lib/cadastros";

export function Equipes() {
  const equipes = useEquipes();
  const [aberto, setAberto] = useState<Equipe | "novo" | null>(null);

  return (
    <section aria-labelledby="titulo-equipes" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="titulo-equipes" className="text-lg font-semibold">
            Equipes
          </h2>
          <p className="max-w-2xl text-sm text-tinta-suave">
            O escopo descreve os assuntos que a equipe responde e orienta o direcionamento das
            perguntas. Os responsáveis recebem os escalonamentos.
          </p>
        </div>
        {aberto === null && (
          <Botao variante="primario" onClick={() => setAberto("novo")}>
            Nova equipe
          </Botao>
        )}
      </div>

      {aberto !== null && (
        <FormEquipe
          key={aberto === "novo" ? "novo" : aberto.id}
          equipe={aberto === "novo" ? null : aberto}
          aoFechar={() => setAberto(null)}
        />
      )}

      <EstadoLista
        carregando={equipes.isPending}
        erro={equipes.error}
        vazio={equipes.data?.length === 0}
        textoVazio="Nenhuma equipe cadastrada."
      />
      <ul className="grid gap-4 lg:grid-cols-2">
        {equipes.data?.map((e) => (
          <li
            key={e.id}
            className="flex flex-col gap-3 rounded-lg border border-borda bg-white p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="font-semibold">{e.nome}</h3>
                {e.email && <p className="text-xs break-all text-tinta-suave">{e.email}</p>}
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <Selo ativo={e.ativo} />
                <Botao
                  variante="texto"
                  aria-label={`Editar ${e.nome}`}
                  onClick={() => setAberto(e)}
                >
                  Editar
                </Botao>
              </div>
            </div>
            <p className="text-sm whitespace-pre-line text-tinta-suave">
              {e.escopo || "Sem escopo definido."}
            </p>
            <Membros equipe={e} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function FormEquipe({ equipe, aoFechar }: { equipe: Equipe | null; aoFechar: () => void }) {
  const salvar = useSalvarEquipe();
  const [nome, setNome] = useState(equipe?.nome ?? "");
  const [escopo, setEscopo] = useState(equipe?.escopo ?? "");
  const [email, setEmail] = useState(equipe?.email ?? "");
  const [ativo, setAtivo] = useState(equipe?.ativo ?? true);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const dados = { nome, escopo, email: email.trim() || null, ...(equipe ? { ativo } : {}) };
    salvar.mutate({ id: equipe?.id, dados }, { onSuccess: aoFechar });
  }

  return (
    <form
      onSubmit={onSubmit}
      aria-label={equipe ? `Editar equipe ${equipe.nome}` : "Nova equipe"}
      className="grid gap-4 rounded-lg border border-borda bg-white p-4 md:grid-cols-2"
    >
      <Campo
        rotulo="Nome da equipe"
        required
        maxLength={120}
        value={nome}
        onChange={(e) => setNome(e.target.value)}
      />
      <Campo
        rotulo="E-mail da equipe"
        ajuda="Opcional. Caixa compartilhada ou lista de distribuição."
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <div className="md:col-span-2">
        <AreaTexto
          rotulo="Escopo"
          ajuda="Assuntos, produtos e normas que a equipe responde."
          maxLength={4000}
          value={escopo}
          onChange={(e) => setEscopo(e.target.value)}
        />
      </div>
      {equipe && (
        <label className="flex items-center gap-2 text-sm font-medium md:col-span-2">
          <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} />
          Equipe ativa
        </label>
      )}
      <div className="flex flex-wrap items-center gap-3 md:col-span-2">
        <Botao type="submit" variante="primario" disabled={salvar.isPending || !nome.trim()}>
          {salvar.isPending ? "Salvando…" : "Salvar equipe"}
        </Botao>
        <Botao onClick={aoFechar}>Cancelar</Botao>
        <ErroApi erro={salvar.error} />
      </div>
    </form>
  );
}

function Membros({ equipe }: { equipe: Equipe }) {
  const usuarios = useUsuarios();
  const definir = useDefinirMembro();
  const remover = useRemoverMembro();
  const [novo, setNovo] = useState("");

  const jaMembros = new Set(equipe.membros.map((m) => m.usuario_id));
  const disponiveis = (usuarios.data ?? []).filter((u) => !jaMembros.has(u.id));
  const ocupado = definir.isPending || remover.isPending;

  return (
    <div className="flex flex-col gap-2 border-t border-borda pt-3">
      <h4 className="text-xs font-medium text-tinta-suave">Membros ({equipe.membros.length})</h4>
      <ul className="flex flex-col gap-2">
        {equipe.membros.map((m) => (
          <li
            key={m.usuario_id}
            className="flex flex-wrap items-center justify-between gap-2 text-sm"
          >
            <span className="min-w-0">
              <span className="block">{m.nome}</span>
              <span className="block text-xs break-all text-tinta-suave">{m.email}</span>
            </span>
            <span className="flex items-center gap-3">
              <label className="flex items-center gap-1.5 text-xs">
                <input
                  type="checkbox"
                  checked={m.responsavel}
                  disabled={ocupado}
                  aria-label={`${m.nome} é responsável por ${equipe.nome}`}
                  onChange={(e) =>
                    definir.mutate({
                      equipeId: equipe.id,
                      usuarioId: m.usuario_id,
                      responsavel: e.target.checked,
                    })
                  }
                />
                Responsável
              </label>
              <Botao
                variante="texto"
                disabled={ocupado}
                aria-label={`Remover ${m.nome} de ${equipe.nome}`}
                onClick={() => remover.mutate({ equipeId: equipe.id, usuarioId: m.usuario_id })}
              >
                Remover
              </Botao>
            </span>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap items-end gap-2">
        <label className="flex min-w-0 flex-1 flex-col gap-1 text-xs font-medium">
          Incluir membro em {equipe.nome}
          <select
            value={novo}
            onChange={(e) => setNovo(e.target.value)}
            className="rounded-md border border-borda bg-white px-2 py-1.5 text-sm font-normal"
          >
            <option value="">Escolha um usuário</option>
            {disponiveis.map((u) => (
              <option key={u.id} value={u.id}>
                {u.nome} ({u.email})
              </option>
            ))}
          </select>
        </label>
        <Botao
          disabled={!novo || ocupado}
          onClick={() =>
            definir.mutate(
              { equipeId: equipe.id, usuarioId: novo, responsavel: false },
              { onSuccess: () => setNovo("") },
            )
          }
        >
          Incluir
        </Botao>
      </div>
      <ErroApi erro={definir.error ?? remover.error ?? usuarios.error} />
    </div>
  );
}
