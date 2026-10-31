import { NavLink, Outlet, useNavigate } from "react-router-dom";

import type { Papel } from "../lib/api";
import { NOMES_PAPEIS, useLogout, useUsuario } from "../lib/auth";
import { StatusApi } from "./StatusApi";

type NavItem = { to: string; label: string; papeis?: Papel[] };

export const NAV_ITEMS: readonly NavItem[] = [
  { to: "/requisicoes", label: "Requisições" },
  { to: "/tarefas", label: "Minhas tarefas" },
  { to: "/conhecimento", label: "Base de conhecimento" },
  { to: "/biblioteca", label: "Biblioteca de respostas" },
  { to: "/admin", label: "Administração", papeis: ["admin"] },
];

export function podeVer(item: NavItem, papeis: Papel[]): boolean {
  return !item.papeis || papeis.includes("admin") || item.papeis.some((p) => papeis.includes(p));
}

export function Layout() {
  const { data: usuario } = useUsuario();
  const sair = useLogout();
  const navigate = useNavigate();
  const papeis = usuario?.papeis ?? [];

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="border-b border-borda bg-white md:w-60 md:shrink-0 md:border-r md:border-b-0">
        <div className="px-5 py-4 text-lg font-semibold">RFP Automation</div>
        <nav aria-label="Principal" className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col">
          {NAV_ITEMS.filter((item) => podeVer(item, papeis)).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `whitespace-nowrap rounded-md px-3 py-2 text-sm ${
                  isActive
                    ? "bg-marca-suave font-medium text-marca"
                    : "text-tinta-suave hover:bg-fundo"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-borda bg-white px-6 py-3">
          <StatusApi />
          {usuario && (
            <div className="flex items-center gap-3 text-sm">
              <span className="text-right leading-tight">
                <span className="block font-medium">{usuario.nome}</span>
                <span className="block text-xs text-tinta-suave">
                  {usuario.papeis.map((p) => NOMES_PAPEIS[p]).join(", ")}
                </span>
              </span>
              <button
                type="button"
                onClick={() =>
                  sair.mutate(undefined, { onSettled: () => navigate("/login", { replace: true }) })
                }
                className="rounded-md border border-borda px-3 py-1.5 hover:bg-fundo"
              >
                Sair
              </button>
            </div>
          )}
        </header>
        <main className="flex-1 px-6 py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
