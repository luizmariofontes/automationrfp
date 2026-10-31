import { NavLink, Outlet } from "react-router-dom";

import { StatusApi } from "./StatusApi";

export const NAV_ITEMS = [
  { to: "/requisicoes", label: "Requisições" },
  { to: "/tarefas", label: "Minhas tarefas" },
  { to: "/conhecimento", label: "Base de conhecimento" },
  { to: "/biblioteca", label: "Biblioteca de respostas" },
  { to: "/admin", label: "Administração" },
] as const;

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="border-b border-borda bg-white md:w-60 md:shrink-0 md:border-r md:border-b-0">
        <div className="px-5 py-4 text-lg font-semibold">RFP Automation</div>
        <nav aria-label="Principal" className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col">
          {NAV_ITEMS.map((item) => (
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
      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-end border-b border-borda bg-white px-6 py-3">
          <StatusApi />
        </header>
        <main className="flex-1 px-6 py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
