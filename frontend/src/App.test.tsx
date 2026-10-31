import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { NAV_ITEMS } from "./components/Layout";

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

function mockReadiness(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(body), { status })),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("App", () => {
  it("redireciona a raiz para Requisições e mostra o menu", async () => {
    mockReadiness(200, { status: "ok", checks: { postgres: "ok", redis: "ok" } });
    renderAt("/");
    expect(await screen.findByRole("heading", { name: "Requisições" })).toBeInTheDocument();
    for (const item of NAV_ITEMS) {
      expect(screen.getByRole("link", { name: item.label })).toBeInTheDocument();
    }
  });

  it("mostra sistema operacional quando a API está pronta", async () => {
    mockReadiness(200, { status: "ok", checks: { postgres: "ok", redis: "ok" } });
    renderAt("/admin");
    expect(await screen.findByText("Sistema operacional")).toBeInTheDocument();
  });

  it("mostra sistema indisponível quando uma dependência falha", async () => {
    mockReadiness(503, { status: "falha", checks: { postgres: "falha", redis: "ok" } });
    renderAt("/admin");
    expect(await screen.findByText("Sistema indisponível")).toBeInTheDocument();
  });
});
