/** Peças de formulário e tabela usadas nas telas de administração. */
import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

import { ApiError } from "../lib/api";

const CAMPO =
  "rounded-md border border-borda bg-white px-3 py-2 text-sm font-normal outline-none focus:border-marca";

type RotuloProps = { rotulo: string; ajuda?: string; children: ReactNode };

function Rotulo({ rotulo, ajuda, children }: RotuloProps) {
  return (
    <label className="flex flex-col gap-1 text-sm font-medium">
      {rotulo}
      {children}
      {ajuda && <span className="text-xs font-normal text-tinta-suave">{ajuda}</span>}
    </label>
  );
}

type Extra = { rotulo: string; ajuda?: string };

export function Campo({ rotulo, ajuda, ...props }: Extra & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <Rotulo rotulo={rotulo} ajuda={ajuda}>
      <input {...props} className={CAMPO} />
    </Rotulo>
  );
}

export function AreaTexto({
  rotulo,
  ajuda,
  ...props
}: Extra & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <Rotulo rotulo={rotulo} ajuda={ajuda}>
      <textarea rows={3} {...props} className={CAMPO} />
    </Rotulo>
  );
}

export function Selecao({
  rotulo,
  ajuda,
  children,
  ...props
}: Extra & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <Rotulo rotulo={rotulo} ajuda={ajuda}>
      <select {...props} className={CAMPO}>
        {children}
      </select>
    </Rotulo>
  );
}

type BotaoProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: "primario" | "secundario" | "texto";
};

const VARIANTES = {
  primario: "bg-marca text-white",
  secundario: "border border-borda bg-white hover:bg-fundo",
  texto: "text-marca hover:underline",
};

export function Botao({ variante = "secundario", type = "button", ...props }: BotaoProps) {
  const espaco = variante === "texto" ? "" : "px-3 py-1.5";
  return (
    <button
      type={type}
      {...props}
      className={`rounded-md text-sm font-medium disabled:opacity-50 ${espaco} ${VARIANTES[variante]}`}
    />
  );
}

/** Mensagem de erro de uma chamada à API, com o request_id para o suporte. */
export function ErroApi({ erro }: { erro: unknown }) {
  if (!erro) return null;
  const api = erro instanceof ApiError ? erro : null;
  return (
    <p role="alert" className="text-sm text-falha">
      {api?.message ?? "Não foi possível concluir. Tente novamente."}
      {api?.status === 422 && " Confira os campos e tente de novo."}
      {api?.requestId && api.status >= 500 && ` (código ${api.requestId})`}
    </p>
  );
}

export function Selo({ ativo }: { ativo: boolean }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-xs ${
        ativo ? "bg-marca-suave text-marca" : "bg-fundo text-tinta-suave"
      }`}
    >
      {ativo ? "Ativo" : "Inativo"}
    </span>
  );
}

export function Tabela({ colunas, children }: { colunas: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-borda bg-white">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-borda text-xs text-tinta-suave">
          <tr>
            {colunas.map((c) => (
              <th key={c} scope="col" className="px-4 py-2 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-borda">{children}</tbody>
      </table>
    </div>
  );
}

/** Estados de carregamento, erro e lista vazia de uma consulta. */
export function EstadoLista({
  carregando,
  erro,
  vazio,
  textoVazio,
}: {
  carregando: boolean;
  erro: unknown;
  vazio: boolean;
  textoVazio: string;
}) {
  if (carregando) return <p className="text-sm text-tinta-suave">Carregando…</p>;
  if (erro) return <ErroApi erro={erro} />;
  if (vazio) return <p className="text-sm text-tinta-suave">{textoVazio}</p>;
  return null;
}
