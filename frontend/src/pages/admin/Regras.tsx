import { type FormEvent, useState } from "react";

import { Botao, Campo, ErroApi, EstadoLista, Selecao, Tabela } from "../../components/ui";
import {
  type Canal,
  descreverDias,
  type Destinatario,
  NOMES_CANAL,
  NOMES_DESTINATARIO,
  useAtualizarRegra,
  useCriarRegra,
  useEquipes,
  useRegras,
  useRemoverRegra,
} from "../../lib/cadastros";

const CANAIS: Canal[] = ["email", "teams"];

export function Regras() {
  const regras = useRegras();
  const equipes = useEquipes();
  const atualizar = useAtualizarRegra();
  const remover = useRemoverRegra();
  const [criando, setCriando] = useState(false);

  const nomeEquipe = (id: string | null) =>
    id === null ? "Padrão (todas)" : (equipes.data?.find((e) => e.id === id)?.nome ?? "—");

  return (
    <section aria-labelledby="titulo-regras" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="titulo-regras" className="text-lg font-semibold">
            Regras de escalonamento
          </h2>
          <p className="max-w-2xl text-sm text-tinta-suave">
            Definem quem é avisado, e quando, em relação ao prazo interno de cada tarefa. Uma equipe
            sem regra própria usa as regras padrão. Os envios começam com o worker de cobrança.
          </p>
        </div>
        {!criando && (
          <Botao variante="primario" onClick={() => setCriando(true)}>
            Nova regra
          </Botao>
        )}
      </div>

      {criando && <FormRegra aoFechar={() => setCriando(false)} />}

      <EstadoLista
        carregando={regras.isPending}
        erro={regras.error}
        vazio={regras.data?.length === 0}
        textoVazio="Nenhuma regra cadastrada."
      />
      <ErroApi erro={atualizar.error ?? remover.error} />
      {!!regras.data?.length && (
        <Tabela colunas={["Regra", "Equipe", "Quando", "Quem recebe", "Canais", "Ativa", ""]}>
          {regras.data.map((r) => (
            <tr key={r.id}>
              <td className="px-4 py-2 font-medium">{r.nome}</td>
              <td className="px-4 py-2">{nomeEquipe(r.equipe_id)}</td>
              <td className="px-4 py-2">{descreverDias(r.dias_do_prazo)}</td>
              <td className="px-4 py-2">{NOMES_DESTINATARIO[r.destinatario]}</td>
              <td className="px-4 py-2">{r.canais.map((c) => NOMES_CANAL[c]).join(", ")}</td>
              <td className="px-4 py-2">
                <input
                  type="checkbox"
                  checked={r.ativo}
                  disabled={atualizar.isPending}
                  aria-label={`Regra ${r.nome} ativa`}
                  onChange={(e) =>
                    atualizar.mutate({ id: r.id, dados: { ativo: e.target.checked } })
                  }
                />
              </td>
              <td className="px-4 py-2 text-right">
                <Botao
                  variante="texto"
                  disabled={remover.isPending}
                  aria-label={`Excluir regra ${r.nome}`}
                  onClick={() => {
                    if (window.confirm(`Excluir a regra "${r.nome}"?`)) remover.mutate(r.id);
                  }}
                >
                  Excluir
                </Botao>
              </td>
            </tr>
          ))}
        </Tabela>
      )}
    </section>
  );
}

function FormRegra({ aoFechar }: { aoFechar: () => void }) {
  const equipes = useEquipes();
  const criar = useCriarRegra();
  const [nome, setNome] = useState("");
  const [equipeId, setEquipeId] = useState("");
  const [momento, setMomento] = useState<"antes" | "no_dia" | "depois">("antes");
  const [dias, setDias] = useState(1);
  const [destinatario, setDestinatario] = useState<Destinatario>("validador");
  const [canais, setCanais] = useState<Canal[]>(["email"]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const diasDoPrazo = momento === "no_dia" ? 0 : momento === "antes" ? -dias : dias;
    criar.mutate(
      { nome, equipe_id: equipeId || null, dias_do_prazo: diasDoPrazo, destinatario, canais },
      { onSuccess: aoFechar },
    );
  }

  function alternarCanal(canal: Canal, marcado: boolean) {
    setCanais((atuais) => (marcado ? [...atuais, canal] : atuais.filter((c) => c !== canal)));
  }

  return (
    <form
      onSubmit={onSubmit}
      aria-label="Nova regra de escalonamento"
      className="grid gap-4 rounded-lg border border-borda bg-white p-4 md:grid-cols-2"
    >
      <Campo
        rotulo="Nome da regra"
        required
        maxLength={120}
        value={nome}
        onChange={(e) => setNome(e.target.value)}
      />
      <Selecao rotulo="Equipe" value={equipeId} onChange={(e) => setEquipeId(e.target.value)}>
        <option value="">Padrão (todas as equipes)</option>
        {equipes.data?.map((e) => (
          <option key={e.id} value={e.id}>
            {e.nome}
          </option>
        ))}
      </Selecao>
      <Selecao
        rotulo="Quando avisar"
        value={momento}
        onChange={(e) => setMomento(e.target.value as typeof momento)}
      >
        <option value="antes">Antes do prazo</option>
        <option value="no_dia">No dia do prazo</option>
        <option value="depois">Depois do prazo</option>
      </Selecao>
      {momento !== "no_dia" && (
        <Campo
          rotulo="Dias úteis"
          type="number"
          min={1}
          max={60}
          required
          value={dias}
          onChange={(e) => setDias(Number(e.target.value))}
        />
      )}
      <Selecao
        rotulo="Quem recebe"
        value={destinatario}
        onChange={(e) => setDestinatario(e.target.value as Destinatario)}
      >
        {(Object.keys(NOMES_DESTINATARIO) as Destinatario[]).map((d) => (
          <option key={d} value={d}>
            {NOMES_DESTINATARIO[d]}
          </option>
        ))}
      </Selecao>
      <fieldset className="flex flex-col gap-1 text-sm">
        <legend className="font-medium">Canais</legend>
        <div className="flex gap-4 pt-1">
          {CANAIS.map((c) => (
            <label key={c} className="flex items-center gap-1.5">
              <input
                type="checkbox"
                checked={canais.includes(c)}
                onChange={(e) => alternarCanal(c, e.target.checked)}
              />
              {NOMES_CANAL[c]}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="flex flex-wrap items-center gap-3 md:col-span-2">
        <Botao
          type="submit"
          variante="primario"
          disabled={criar.isPending || !nome.trim() || canais.length === 0}
        >
          {criar.isPending ? "Salvando…" : "Salvar regra"}
        </Botao>
        <Botao onClick={aoFechar}>Cancelar</Botao>
        <ErroApi erro={criar.error} />
      </div>
    </form>
  );
}
