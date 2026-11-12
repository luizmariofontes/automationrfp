import { type FormEvent, useState } from "react";

import {
  AreaTexto,
  Botao,
  Campo,
  ErroApi,
  EstadoLista,
  Selecao,
  Selo,
  Tabela,
} from "../../components/ui";
import {
  type Cliente,
  type ClienteDados,
  formatarCnpj,
  linhasParaLista,
  type ModeloImplantacao,
  NOMES_MODELO,
  useClientes,
  useSalvarCliente,
} from "../../lib/cadastros";

export function Clientes() {
  const clientes = useClientes();
  // `null`: formulário fechado. "novo": cadastro. Cliente: edição.
  const [aberto, setAberto] = useState<Cliente | "novo" | null>(null);

  return (
    <section aria-labelledby="titulo-clientes" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="titulo-clientes" className="text-lg font-semibold">
            Clientes
          </h2>
          <p className="max-w-2xl text-sm text-tinta-suave">
            Sigla, nomes, CNPJ, domínios e apelidos são usados para anonimizar os questionários.
            Quanto mais completo o cadastro, menos identificadores escapam.
          </p>
        </div>
        {aberto === null && (
          <Botao variante="primario" onClick={() => setAberto("novo")}>
            Novo cliente
          </Botao>
        )}
      </div>

      {aberto !== null && (
        <FormCliente
          key={aberto === "novo" ? "novo" : aberto.id}
          cliente={aberto === "novo" ? null : aberto}
          aoFechar={() => setAberto(null)}
        />
      )}

      <EstadoLista
        carregando={clientes.isPending}
        erro={clientes.error}
        vazio={clientes.data?.length === 0}
        textoVazio="Nenhum cliente cadastrado."
      />
      {!!clientes.data?.length && (
        <Tabela colunas={["Sigla", "Nome", "CNPJ", "Implantação padrão", "Situação", ""]}>
          {clientes.data.map((c) => (
            <tr key={c.id}>
              <td className="px-4 py-2 font-medium">{c.sigla}</td>
              <td className="px-4 py-2">{c.nome}</td>
              <td className="px-4 py-2 whitespace-nowrap">{formatarCnpj(c.cnpj) || "—"}</td>
              <td className="px-4 py-2">
                {c.modelo_implantacao_padrao ? NOMES_MODELO[c.modelo_implantacao_padrao] : "—"}
              </td>
              <td className="px-4 py-2">
                <Selo ativo={c.ativo} />
              </td>
              <td className="px-4 py-2 text-right">
                <Botao
                  variante="texto"
                  aria-label={`Editar ${c.sigla}`}
                  onClick={() => setAberto(c)}
                >
                  Editar
                </Botao>
              </td>
            </tr>
          ))}
        </Tabela>
      )}
    </section>
  );
}

function FormCliente({ cliente, aoFechar }: { cliente: Cliente | null; aoFechar: () => void }) {
  const salvar = useSalvarCliente();
  const [sigla, setSigla] = useState(cliente?.sigla ?? "");
  const [nome, setNome] = useState(cliente?.nome ?? "");
  const [cnpj, setCnpj] = useState(formatarCnpj(cliente?.cnpj ?? null));
  const [outrosNomes, setOutrosNomes] = useState((cliente?.outros_nomes ?? []).join("\n"));
  const [dominios, setDominios] = useState((cliente?.dominios ?? []).join("\n"));
  const [apelidos, setApelidos] = useState((cliente?.apelidos ?? []).join("\n"));
  const [modelo, setModelo] = useState<ModeloImplantacao | "">(
    cliente?.modelo_implantacao_padrao ?? "",
  );
  const [ativo, setAtivo] = useState(cliente?.ativo ?? true);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const dados: ClienteDados = {
      sigla,
      nome,
      cnpj: cnpj.trim() || null,
      outros_nomes: linhasParaLista(outrosNomes),
      dominios: linhasParaLista(dominios),
      apelidos: linhasParaLista(apelidos),
      modelo_implantacao_padrao: modelo || null,
      ...(cliente ? { ativo } : {}),
    };
    salvar.mutate({ id: cliente?.id, dados }, { onSuccess: aoFechar });
  }

  return (
    <form
      onSubmit={onSubmit}
      aria-label={cliente ? `Editar cliente ${cliente.sigla}` : "Novo cliente"}
      className="grid gap-4 rounded-lg border border-borda bg-white p-4 md:grid-cols-2"
    >
      <Campo
        rotulo="Sigla"
        ajuda="De 2 a 12 letras ou números. É como o cliente aparece nas requisições."
        required
        maxLength={12}
        value={sigla}
        onChange={(e) => setSigla(e.target.value.toUpperCase())}
      />
      <Campo
        rotulo="Nome"
        required
        maxLength={200}
        value={nome}
        onChange={(e) => setNome(e.target.value)}
      />
      <Campo
        rotulo="CNPJ"
        ajuda="Opcional. Com ou sem pontuação."
        value={cnpj}
        onChange={(e) => setCnpj(e.target.value)}
      />
      <Selecao
        rotulo="Modelo de implantação padrão"
        ajuda="Sugerido ao abrir uma requisição deste cliente."
        value={modelo}
        onChange={(e) => setModelo(e.target.value as ModeloImplantacao | "")}
      >
        <option value="">Não definido</option>
        <option value="on_premise">{NOMES_MODELO.on_premise}</option>
        <option value="hosting">{NOMES_MODELO.hosting}</option>
      </Selecao>
      <AreaTexto
        rotulo="Outros nomes"
        ajuda="Razão social, nome fantasia, nomes antigos. Um por linha."
        value={outrosNomes}
        onChange={(e) => setOutrosNomes(e.target.value)}
      />
      <AreaTexto
        rotulo="Domínios"
        ajuda="Um por linha, como empresa.com.br."
        value={dominios}
        onChange={(e) => setDominios(e.target.value)}
      />
      <AreaTexto
        rotulo="Apelidos"
        ajuda="Como o cliente costuma ser chamado nos questionários. Um por linha."
        value={apelidos}
        onChange={(e) => setApelidos(e.target.value)}
      />
      {cliente && (
        <label className="flex items-center gap-2 self-start text-sm font-medium">
          <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} />
          Cliente ativo
        </label>
      )}
      <div className="flex flex-wrap items-center gap-3 md:col-span-2">
        <Botao type="submit" variante="primario" disabled={salvar.isPending || !sigla || !nome}>
          {salvar.isPending ? "Salvando…" : "Salvar cliente"}
        </Botao>
        <Botao onClick={aoFechar}>Cancelar</Botao>
        <ErroApi erro={salvar.error} />
      </div>
    </form>
  );
}
