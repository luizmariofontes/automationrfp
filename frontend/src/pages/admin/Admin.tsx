import { NavLink, Outlet } from "react-router-dom";

const ABAS = [
  { to: "clientes", label: "Clientes" },
  { to: "equipes", label: "Equipes" },
  { to: "escalonamento", label: "Escalonamento" },
  { to: "auditoria", label: "Auditoria" },
] as const;

/** Moldura da área de administração: título e navegação entre os cadastros. */
export function Admin() {
  return (
    <div className="flex max-w-6xl flex-col gap-6">
      <h1 className="text-2xl font-semibold">Administração</h1>
      <nav aria-label="Administração" className="flex gap-1 overflow-x-auto border-b border-borda">
        {ABAS.map((aba) => (
          <NavLink
            key={aba.to}
            to={aba.to}
            className={({ isActive }) =>
              `-mb-px whitespace-nowrap border-b-2 px-3 py-2 text-sm ${
                isActive
                  ? "border-marca font-medium text-marca"
                  : "border-transparent text-tinta-suave hover:text-tinta"
              }`
            }
          >
            {aba.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
