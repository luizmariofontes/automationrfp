import { useState } from "react";

import { Botao, EstadoLista, Tabela } from "../../components/ui";
import { TAMANHO_PAGINA_AUDITORIA, useAuditoria } from "../../lib/cadastros";

const ACOES: Record<string, string> = {
  "cliente.criado": "Cliente criado",
  "cliente.alterado": "Cliente alterado",
  "equipe.criada": "Equipe criada",
  "equipe.alterada": "Equipe alterada",
  "membro.incluido": "Membro incluído",
  "membro.alterado": "Membro alterado",
  "membro.removido": "Membro removido",
  "regra_escalonamento.criada": "Regra criada",
  "regra_escalonamento.alterada": "Regra alterada",
  "regra_escalonamento.removida": "Regra removida",
};

const formatoData = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "medium" });

export function Auditoria() {
  const [pagina, setPagina] = useState(0);
  const auditoria = useAuditoria(pagina);
  const total = auditoria.data?.total ?? 0;
  const paginas = Math.max(1, Math.ceil(total / TAMANHO_PAGINA_AUDITORIA));

  return (
    <section aria-labelledby="titulo-auditoria" className="flex flex-col gap-4">
      <div>
        <h2 id="titulo-auditoria" className="text-lg font-semibold">
          Auditoria
        </h2>
        <p className="max-w-2xl text-sm text-tinta-suave">
          Quem fez o quê e quando. O registro mostra quais campos mudaram, sem os valores, para não
          guardar dados de clientes.
        </p>
      </div>

      <EstadoLista
        carregando={auditoria.isPending}
        erro={auditoria.error}
        vazio={total === 0 && !auditoria.isPending}
        textoVazio="Nenhuma ação registrada."
      />
      {!!auditoria.data?.itens.length && (
        <>
          <Tabela colunas={["Quando", "Quem", "Ação", "Campos alterados", "Registro"]}>
            {auditoria.data.itens.map((r) => (
              <tr key={r.id}>
                <td className="px-4 py-2 whitespace-nowrap">
                  {formatoData.format(new Date(r.ocorrido_em))}
                </td>
                <td className="px-4 py-2 break-all">{r.ator_email ?? "Sistema"}</td>
                <td className="px-4 py-2">{ACOES[r.acao] ?? r.acao}</td>
                <td className="px-4 py-2 text-tinta-suave">{r.campos.join(", ") || "—"}</td>
                <td className="px-4 py-2 font-mono text-xs text-tinta-suave" title={r.entidade_id}>
                  {r.entidade_id.slice(0, 8)}
                </td>
              </tr>
            ))}
          </Tabela>
          <div className="flex items-center gap-3 text-sm">
            <Botao disabled={pagina === 0} onClick={() => setPagina((p) => p - 1)}>
              Anterior
            </Botao>
            <span className="text-tinta-suave">
              Página {pagina + 1} de {paginas} · {total} {total === 1 ? "registro" : "registros"}
            </span>
            <Botao disabled={pagina + 1 >= paginas} onClick={() => setPagina((p) => p + 1)}>
              Próxima
            </Botao>
          </div>
        </>
      )}
    </section>
  );
}
