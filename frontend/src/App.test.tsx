import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

type Resposta = { status: number; body?: unknown };
type Rotas = Record<string, Resposta | ((init?: RequestInit) => Resposta)>;

const ANALISTA = { id: "1", email: "analista@rfp.local", nome: "Ana", papeis: ["analista"] };
const ADMIN = { id: "2", email: "admin@rfp.local", nome: "Adm", papeis: ["admin"] };
const PRONTO = { status: 200, body: { status: "ok", checks: { postgres: "ok", redis: "ok" } } };
const PROVEDORES = { status: 200, body: { local: true, oidc: false } };
const VAZIO = { status: 200, body: [] };
const SEM_SESSAO = { status: 401, body: { error: { code: "nao_autenticado", message: "x" } } };

function mockApi(rotas: Rotas) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const rota = rotas[url];
    if (!rota) throw new Error(`rota não simulada: ${url}`);
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

afterEach(() => vi.unstubAllGlobals());

describe("sem sessão", () => {
  it("manda para a tela de login", async () => {
    mockApi({ "/api/v1/auth/me": SEM_SESSAO, "/api/v1/auth/providers": PROVEDORES });
    renderAt("/requisicoes");
    expect(await screen.findByRole("button", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.getByText(/Login local para testes/)).toBeInTheDocument();
  });

  it("entra e volta para a página pedida", async () => {
    let logado = false;
    const fetchMock = mockApi({
      "/api/v1/auth/me": () => (logado ? { status: 200, body: ANALISTA } : SEM_SESSAO),
      "/api/v1/auth/providers": PROVEDORES,
      "/api/v1/auth/login": () => {
        logado = true;
        return { status: 200, body: ANALISTA };
      },
      "/api/v1/health/ready": PRONTO,
    });
    renderAt("/tarefas");
    fireEvent.change(await screen.findByLabelText("E-mail"), {
      target: { value: "analista@rfp.local" },
    });
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "rfp-local-123" } });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("heading", { name: "Minhas tarefas" })).toBeInTheDocument();
    const chamada = fetchMock.mock.calls.find(([url]) => url === "/api/v1/auth/login");
    expect(JSON.parse(String(chamada?.[1]?.body))).toEqual({
      email: "analista@rfp.local",
      senha: "rfp-local-123",
    });
  });

  it("mostra a mensagem de erro do login", async () => {
    mockApi({
      "/api/v1/auth/me": SEM_SESSAO,
      "/api/v1/auth/providers": PROVEDORES,
      "/api/v1/auth/login": {
        status: 401,
        body: { error: { code: "nao_autenticado", message: "E-mail ou senha incorretos." } },
      },
    });
    renderAt("/login");
    fireEvent.change(await screen.findByLabelText("E-mail"), { target: { value: "a@b.c" } });
    fireEvent.change(screen.getByLabelText("Senha"), { target: { value: "errada" } });
    fireEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("E-mail ou senha incorretos.");
  });

  it("esconde o formulário quando o login local está desativado", async () => {
    mockApi({
      "/api/v1/auth/me": SEM_SESSAO,
      "/api/v1/auth/providers": { status: 200, body: { local: false, oidc: false } },
    });
    renderAt("/login");
    expect(await screen.findByText(/login local está desativado/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Entrar" })).not.toBeInTheDocument();
  });
});

describe("com sessão", () => {
  it("analista não vê Administração no menu", async () => {
    mockApi({ "/api/v1/auth/me": { status: 200, body: ANALISTA }, "/api/v1/health/ready": PRONTO });
    renderAt("/");
    expect(await screen.findByRole("heading", { name: "Requisições" })).toBeInTheDocument();
    expect(screen.getByText("Ana")).toBeInTheDocument();
    expect(screen.getByText("Analista")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Administração" })).not.toBeInTheDocument();
  });

  it("analista que abre /admin vê sem permissão", async () => {
    mockApi({ "/api/v1/auth/me": { status: 200, body: ANALISTA }, "/api/v1/health/ready": PRONTO });
    renderAt("/admin");
    expect(await screen.findByRole("heading", { name: "Sem permissão" })).toBeInTheDocument();
  });

  it("administrador vê todo o menu e o status da API", async () => {
    mockApi({
      "/api/v1/auth/me": { status: 200, body: ADMIN },
      "/api/v1/health/ready": PRONTO,
      "/api/v1/cadastros/clientes": VAZIO,
    });
    renderAt("/admin");
    expect(await screen.findByRole("link", { name: "Administração" })).toBeInTheDocument();
    expect(await screen.findByText("Nenhum cliente cadastrado.")).toBeInTheDocument();
    expect(await screen.findByText("Sistema operacional")).toBeInTheDocument();
  });

  it("mostra sistema indisponível quando uma dependência falha", async () => {
    mockApi({
      "/api/v1/auth/me": { status: 200, body: ADMIN },
      "/api/v1/health/ready": { status: 503, body: { status: "falha", checks: {} } },
      "/api/v1/cadastros/clientes": VAZIO,
    });
    renderAt("/admin");
    expect(await screen.findByText("Sistema indisponível")).toBeInTheDocument();
  });

  it("sair encerra a sessão e volta ao login", async () => {
    let logado = true;
    mockApi({
      "/api/v1/auth/me": () => (logado ? { status: 200, body: ANALISTA } : SEM_SESSAO),
      "/api/v1/auth/logout": () => {
        logado = false;
        return { status: 204 };
      },
      "/api/v1/auth/providers": PROVEDORES,
      "/api/v1/health/ready": PRONTO,
    });
    renderAt("/requisicoes");
    fireEvent.click(await screen.findByRole("button", { name: "Sair" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Entrar" })).toBeInTheDocument());
  });
});
