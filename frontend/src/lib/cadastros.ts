/** Cadastros e auditoria: tipos, chamadas à API e hooks. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch, type Papel } from "./api";

const BASE = "/api/v1/cadastros";

// ------------------------------------------------------------------ tipos

export type ModeloImplantacao = "on_premise" | "hosting";

export const NOMES_MODELO: Record<ModeloImplantacao, string> = {
  on_premise: "On premise",
  hosting: "Hosting",
};

export type Cliente = {
  id: string;
  sigla: string;
  nome: string;
  outros_nomes: string[];
  cnpj: string | null;
  dominios: string[];
  apelidos: string[];
  modelo_implantacao_padrao: ModeloImplantacao | null;
  ativo: boolean;
  atualizado_em: string;
};

export type ClienteDados = Omit<Cliente, "id" | "ativo" | "atualizado_em"> & { ativo?: boolean };

export type Membro = { usuario_id: string; nome: string; email: string; responsavel: boolean };

export type Equipe = {
  id: string;
  nome: string;
  escopo: string;
  email: string | null;
  ativo: boolean;
  membros: Membro[];
};

export type EquipeDados = { nome: string; escopo: string; email: string | null; ativo?: boolean };

export type UsuarioResumo = { id: string; nome: string; email: string; papeis: Papel[] };

export type Destinatario = "validador" | "responsavel_equipe" | "analista" | "admin";
export type Canal = "email" | "teams";

export const NOMES_DESTINATARIO: Record<Destinatario, string> = {
  validador: "Validador da tarefa",
  responsavel_equipe: "Responsável da equipe",
  analista: "Analista da requisição",
  admin: "Administradores",
};

export const NOMES_CANAL: Record<Canal, string> = { email: "E-mail", teams: "Teams" };

export type Regra = {
  id: string;
  equipe_id: string | null;
  nome: string;
  dias_do_prazo: number;
  destinatario: Destinatario;
  canais: Canal[];
  ativo: boolean;
};

export type RegraDados = Omit<Regra, "id" | "ativo">;

export type RegistroAuditoria = {
  id: string;
  ocorrido_em: string;
  ator_id: string | null;
  ator_email: string | null;
  acao: string;
  entidade: string;
  entidade_id: string;
  campos: string[];
  request_id: string | null;
};

export type PaginaAuditoria = { itens: RegistroAuditoria[]; total: number };

// ------------------------------------------------------------------ formatação

export function formatarCnpj(cnpj: string | null): string {
  if (!cnpj || cnpj.length !== 14) return cnpj ?? "";
  return `${cnpj.slice(0, 2)}.${cnpj.slice(2, 5)}.${cnpj.slice(5, 8)}/${cnpj.slice(8, 12)}-${cnpj.slice(12)}`;
}

/** "2 dias úteis antes do prazo", "No dia do prazo", "1 dia útil depois do prazo". */
export function descreverDias(dias: number): string {
  if (dias === 0) return "No dia do prazo";
  const n = Math.abs(dias);
  return `${n} ${n === 1 ? "dia útil" : "dias úteis"} ${dias < 0 ? "antes" : "depois"} do prazo`;
}

/** Uma entrada por linha; linhas vazias são ignoradas. */
export const linhasParaLista = (texto: string) =>
  texto
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

// ------------------------------------------------------------------ hooks

const json = (metodo: string, corpo?: unknown): RequestInit => ({
  method: metodo,
  body: corpo === undefined ? undefined : JSON.stringify(corpo),
});

const CHAVES = {
  clientes: ["cadastros", "clientes"],
  equipes: ["cadastros", "equipes"],
  usuarios: ["cadastros", "usuarios"],
  regras: ["cadastros", "regras"],
  auditoria: ["auditoria"],
} as const;

/** Mutação que, ao terminar, recarrega a lista afetada e a auditoria. */
function useAlteracao<V, R>(fn: (v: V) => Promise<R>, chave: readonly string[]) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: chave });
      void qc.invalidateQueries({ queryKey: CHAVES.auditoria });
    },
  });
}

export const useClientes = () =>
  useQuery({ queryKey: CHAVES.clientes, queryFn: () => apiFetch<Cliente[]>(`${BASE}/clientes`) });

export const useSalvarCliente = () =>
  useAlteracao(
    ({ id, dados }: { id?: string; dados: ClienteDados }) =>
      id
        ? apiFetch<Cliente>(`${BASE}/clientes/${id}`, json("PATCH", dados))
        : apiFetch<Cliente>(`${BASE}/clientes`, json("POST", dados)),
    CHAVES.clientes,
  );

export const useEquipes = () =>
  useQuery({ queryKey: CHAVES.equipes, queryFn: () => apiFetch<Equipe[]>(`${BASE}/equipes`) });

export const useSalvarEquipe = () =>
  useAlteracao(
    ({ id, dados }: { id?: string; dados: EquipeDados }) =>
      id
        ? apiFetch<Equipe>(`${BASE}/equipes/${id}`, json("PATCH", dados))
        : apiFetch<Equipe>(`${BASE}/equipes`, json("POST", dados)),
    CHAVES.equipes,
  );

export const useUsuarios = () =>
  useQuery({
    queryKey: CHAVES.usuarios,
    queryFn: () => apiFetch<UsuarioResumo[]>(`${BASE}/usuarios`),
  });

export const useDefinirMembro = () =>
  useAlteracao(
    (v: { equipeId: string; usuarioId: string; responsavel: boolean }) =>
      apiFetch<Equipe>(
        `${BASE}/equipes/${v.equipeId}/membros/${v.usuarioId}`,
        json("PUT", { responsavel: v.responsavel }),
      ),
    CHAVES.equipes,
  );

export const useRemoverMembro = () =>
  useAlteracao(
    (v: { equipeId: string; usuarioId: string }) =>
      apiFetch<void>(`${BASE}/equipes/${v.equipeId}/membros/${v.usuarioId}`, json("DELETE")),
    CHAVES.equipes,
  );

export const useRegras = () =>
  useQuery({
    queryKey: CHAVES.regras,
    queryFn: () => apiFetch<Regra[]>(`${BASE}/regras-escalonamento`),
  });

export const useCriarRegra = () =>
  useAlteracao(
    (dados: RegraDados) => apiFetch<Regra>(`${BASE}/regras-escalonamento`, json("POST", dados)),
    CHAVES.regras,
  );

export const useAtualizarRegra = () =>
  useAlteracao(
    ({ id, dados }: { id: string; dados: Partial<Omit<Regra, "id" | "equipe_id">> }) =>
      apiFetch<Regra>(`${BASE}/regras-escalonamento/${id}`, json("PATCH", dados)),
    CHAVES.regras,
  );

export const useRemoverRegra = () =>
  useAlteracao(
    (id: string) => apiFetch<void>(`${BASE}/regras-escalonamento/${id}`, json("DELETE")),
    CHAVES.regras,
  );

export const TAMANHO_PAGINA_AUDITORIA = 25;

export const useAuditoria = (pagina: number) =>
  useQuery({
    queryKey: [...CHAVES.auditoria, pagina],
    queryFn: () =>
      apiFetch<PaginaAuditoria>(
        `/api/v1/auditoria?limite=${TAMANHO_PAGINA_AUDITORIA}&offset=${pagina * TAMANHO_PAGINA_AUDITORIA}`,
      ),
    placeholderData: (anterior) => anterior,
  });
