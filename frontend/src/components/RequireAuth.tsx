import { Navigate, Outlet, useLocation } from "react-router-dom";

import type { Papel } from "../lib/api";
import { useUsuario } from "../lib/auth";

/** Protege as rotas internas: sem sessão, manda para /login e volta depois. */
export function RequireAuth() {
  const { data: usuario, isPending, isError } = useUsuario();
  const location = useLocation();

  if (isPending) {
    return <p className="p-8 text-tinta-suave">Carregando…</p>;
  }
  if (isError) {
    return (
      <p role="alert" className="p-8 text-falha">
        Não foi possível falar com a API. Verifique se os serviços estão no ar.
      </p>
    );
  }
  if (!usuario) {
    return <Navigate to="/login" replace state={{ de: location.pathname }} />;
  }
  return <Outlet />;
}

/** Exige um dos papéis (administrador sempre passa). O backend também verifica. */
export function RequireRole({ papeis }: { papeis: Papel[] }) {
  const { data: usuario } = useUsuario();
  const atuais = usuario?.papeis ?? [];
  const permitido = atuais.includes("admin") || papeis.some((p) => atuais.includes(p));
  if (!permitido) {
    return (
      <section className="max-w-2xl">
        <h1 className="text-2xl font-semibold">Sem permissão</h1>
        <p className="mt-2 text-tinta-suave">
          Seu perfil não dá acesso a esta área. Fale com um administrador se precisar.
        </p>
      </section>
    );
  }
  return <Outlet />;
}
