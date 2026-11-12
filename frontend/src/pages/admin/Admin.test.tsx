import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "../../App";
import { descreverDias, formatarCnpj, linhasParaLista } from "../../lib/cadastros";

type Resposta = { status: number; body?: unknown };
type Rota = Resposta | ((init?: RequestInit) => Resposta);

const ADMIN = { id: "u1", email: "admin@rfp.local", nome: "Adm", papeis: ["admin"] };
const VALIDADOR = { id: "u2", email: "val@rfp.local", nome: "Vera", papeis: ["validador"] };
// Cliente fictício.
const AURORA = {
  id: "c1",
  sigla: "AUR",
  nome: "Banco Aurora S.A.",
  outros_nomes: ["Banco Aurora"],
  cnpj: "11222333000181",
  dominios: ["bancoaurora.example"],
  apelidos: [],
  modelo_implantacao_padrao: "hosting",
  ativo: true,
  atualizado_em: "2026-11-12T12:00:00Z",
};
const SEGURANCA = {
  id: "e1",
  nome: "Segurança",
  escopo: "ISO 27001 e LGPD",
  email: null,
  ativo: true,
  membros: [] as unknown[],
};

/** Simula a API. A chave é "MÉTODO caminho" (sem a query string). */
function mockApi(rotas: Record<string, Rota>) {
  const base: Record<string, Rota> = {
    "GET /api/v1/auth/me": { status: 200, body: ADMIN },
    "GET /api/v1/health/ready": { status: 200, body: { status: "ok", checks: {} } },
  };
  const todas = { ...base, ...rotas };
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const chave = `${init?.method ?? "GET"} ${url.split("?")[0]}`;
    const rota = todas[chave];
    if (!rota) throw new Error(`rota não simulada: ${chave}`);
    const r = typeof rota === "function" ? rota(init) : rota;
    return new Response(r.body === undefined ? null : JSON.stringify(r.body), {
      status: r.status,
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const corpo = (init?: RequestInit) => JSON.parse(String(init?.body)) as Record<string, unknown>;

afterEach(() => vi.unstubAllGlobals());

describe("formatação", () => {
  it("formata CNPJ, prazos e listas", () => {
    expect(formatarCnpj("11222333000181")).toBe("11.222.333/0001-81");
    expect(formatarCnpj(null)).toBe("");
    expect(descreverDias(-2)).toBe("2 dias úteis antes do prazo");
    expect(descreverDias(0)).toBe("No dia do prazo");
    expect(descreverDias(1)).toBe("1 dia útil depois do prazo");
    expect(linhasParaLista(" a \n\n b\n")).toEqual(["a", "b"]);
  });
});

describe("clientes", () => {
  it("lista os clientes e cadastra um novo", async () => {
    const clientes = [AURORA];
    const fetchMock = mockApi({
      "GET /api/v1/cadastros/clientes": () => ({ status: 200, body: clientes }),
      "POST /api/v1/cadastros/clientes": (init) => {
        const novo = { ...AURORA, ...corpo(init), id: "c2" };
        clientes.push(novo as typeof AURORA);
        return { status: 201, body: novo };
      },
    });
    renderAt("/admin");

    expect(await screen.findByText("Banco Aurora S.A.")).toBeInTheDocument();
    expect(screen.getByText("11.222.333/0001-81")).toBeInTheDocument();
    expect(screen.getByText("Hosting")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Novo cliente" }));
    const form = within(screen.getByRole("form", { name: "Novo cliente" }));
    fireEvent.change(form.getByLabelText(/^Sigla/), { target: { value: "bor" } });
    fireEvent.change(form.getByLabelText(/^Nome/), { target: { value: "Seguradora Boreal" } });
    fireEvent.change(form.getByLabelText(/^Domínios/), {
      target: { value: "boreal.example\n\nboreal-seguros.example" },
    });
    fireEvent.change(form.getByLabelText(/^Modelo de implantação padrão/), {
      target: { value: "on_premise" },
    });
    fireEvent.click(form.getByRole("button", { name: "Salvar cliente" }));

    expect(await screen.findByText("Seguradora Boreal")).toBeInTheDocument();
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(corpo(post?.[1])).toEqual({
      sigla: "BOR",
      nome: "Seguradora Boreal",
      cnpj: null,
      outros_nomes: [],
      dominios: ["boreal.example", "boreal-seguros.example"],
      apelidos: [],
      modelo_implantacao_padrao: "on_premise",
    });
    // O formulário fecha depois de salvar.
    expect(screen.queryByRole("form", { name: "Novo cliente" })).not.toBeInTheDocument();
  });

  it("mostra o erro da API e mantém o formulário aberto", async () => {
    mockApi({
      "GET /api/v1/cadastros/clientes": { status: 200, body: [AURORA] },
      "PATCH /api/v1/cadastros/clientes/c1": {
        status: 409,
        body: { error: { code: "conflito", message: "Já existe um cliente com esta sigla." } },
      },
    });
    renderAt("/admin/clientes");
    fireEvent.click(await screen.findByRole("button", { name: "Editar AUR" }));
    const form = within(screen.getByRole("form", { name: "Editar cliente AUR" }));
    expect(form.getByLabelText(/^CNPJ/)).toHaveValue("11.222.333/0001-81");
    fireEvent.click(form.getByRole("button", { name: "Salvar cliente" }));
    expect(await form.findByRole("alert")).toHaveTextContent("Já existe um cliente");
  });
});

describe("equipes", () => {
  it("inclui um membro na equipe", async () => {
    let equipe = SEGURANCA;
    const fetchMock = mockApi({
      "GET /api/v1/cadastros/equipes": () => ({ status: 200, body: [equipe] }),
      "GET /api/v1/cadastros/usuarios": { status: 200, body: [ADMIN, VALIDADOR] },
      "PUT /api/v1/cadastros/equipes/e1/membros/u2": (init) => {
        const membro = { usuario_id: "u2", nome: "Vera", email: "val@rfp.local", ...corpo(init) };
        equipe = { ...equipe, membros: [membro] };
        return { status: 200, body: equipe };
      },
    });
    renderAt("/admin/equipes");

    expect(await screen.findByRole("heading", { name: "Segurança" })).toBeInTheDocument();
    expect(screen.getByText("ISO 27001 e LGPD")).toBeInTheDocument();
    const seletor = screen.getByLabelText("Incluir membro em Segurança");
    await within(seletor).findByRole("option", { name: "Vera (val@rfp.local)" });
    fireEvent.change(seletor, { target: { value: "u2" } });
    fireEvent.click(screen.getByRole("button", { name: "Incluir" }));

    expect(
      await screen.findByRole("checkbox", { name: "Vera é responsável por Segurança" }),
    ).not.toBeChecked();
    const put = fetchMock.mock.calls.find(([, init]) => init?.method === "PUT");
    expect(corpo(put?.[1])).toEqual({ responsavel: false });
  });
});

describe("escalonamento", () => {
  it("cria uma regra antes do prazo", async () => {
    const regras: unknown[] = [];
    const fetchMock = mockApi({
      "GET /api/v1/cadastros/equipes": { status: 200, body: [SEGURANCA] },
      "GET /api/v1/cadastros/regras-escalonamento": () => ({ status: 200, body: regras }),
      "POST /api/v1/cadastros/regras-escalonamento": (init) => {
        const regra = { id: "r1", ativo: true, ...corpo(init) };
        regras.push(regra);
        return { status: 201, body: regra };
      },
    });
    renderAt("/admin/escalonamento");

    expect(await screen.findByText("Nenhuma regra cadastrada.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Nova regra" }));
    fireEvent.change(screen.getByLabelText("Nome da regra"), { target: { value: "Lembrete" } });
    fireEvent.change(screen.getByLabelText("Dias úteis"), { target: { value: "2" } });
    fireEvent.click(screen.getByLabelText("Teams"));
    fireEvent.click(screen.getByRole("button", { name: "Salvar regra" }));

    expect(await screen.findByText("2 dias úteis antes do prazo")).toBeInTheDocument();
    expect(screen.getByText("Padrão (todas)")).toBeInTheDocument();
    expect(screen.getByText("E-mail, Teams")).toBeInTheDocument();
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(corpo(post?.[1])).toEqual({
      nome: "Lembrete",
      equipe_id: null,
      dias_do_prazo: -2,
      destinatario: "validador",
      canais: ["email", "teams"],
    });
  });
});

describe("auditoria", () => {
  it("mostra quem fez o quê, sem valores", async () => {
    const fetchMock = mockApi({
      "GET /api/v1/auditoria": {
        status: 200,
        body: {
          total: 30,
          itens: [
            {
              id: "a1",
              ocorrido_em: "2026-11-12T15:00:00Z",
              ator_id: "u1",
              ator_email: "admin@rfp.local",
              acao: "cliente.alterado",
              entidade: "cliente",
              entidade_id: "c1c1c1c1-0000-0000-0000-000000000000",
              campos: ["apelidos", "cnpj"],
              request_id: "req-1",
            },
          ],
        },
      },
    });
    renderAt("/admin/auditoria");

    expect(await screen.findByText("Cliente alterado")).toBeInTheDocument();
    expect(screen.getByText("admin@rfp.local")).toBeInTheDocument();
    expect(screen.getByText("apelidos, cnpj")).toBeInTheDocument();
    expect(screen.getByText(/Página 1 de 2/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Próxima" }));
    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([url]) => String(url).includes("offset=25"))).toBe(true),
    );
  });
});
