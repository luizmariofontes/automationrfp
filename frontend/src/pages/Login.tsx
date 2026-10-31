import { useQuery } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { ApiError, getProvedores } from "../lib/api";
import { useLogin, useUsuario } from "../lib/auth";

export function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const destino = (location.state as { de?: string } | null)?.de ?? "/";

  const { data: usuario } = useUsuario();
  const provedores = useQuery({ queryKey: ["auth", "providers"], queryFn: getProvedores });
  const entrar = useLogin();

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");

  if (usuario) return <Navigate to={destino} replace />;

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    entrar.mutate({ email, senha }, { onSuccess: () => navigate(destino, { replace: true }) });
  }

  const erro =
    entrar.error instanceof ApiError
      ? entrar.error.message
      : entrar.error
        ? "Não foi possível entrar. Tente novamente."
        : null;

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-xl border border-borda bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold">RFP Automation</h1>
        <p className="mt-1 text-sm text-tinta-suave">Entre para continuar.</p>

        {provedores.data?.local === false ? (
          <p className="mt-6 text-sm text-tinta-suave">
            O login local está desativado neste ambiente. Use o login da empresa (SSO).
          </p>
        ) : (
          <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4" noValidate>
            <label className="flex flex-col gap-1 text-sm font-medium">
              E-mail
              <input
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="rounded-md border border-borda px-3 py-2 font-normal outline-none focus:border-marca"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm font-medium">
              Senha
              <input
                type="password"
                autoComplete="current-password"
                required
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                className="rounded-md border border-borda px-3 py-2 font-normal outline-none focus:border-marca"
              />
            </label>
            {erro && (
              <p role="alert" className="text-sm text-falha">
                {erro}
              </p>
            )}
            <button
              type="submit"
              disabled={entrar.isPending || !email || !senha}
              className="rounded-md bg-marca px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {entrar.isPending ? "Entrando…" : "Entrar"}
            </button>
            <p className="rounded-md bg-marca-suave px-3 py-2 text-xs text-tinta-suave">
              Login local para testes. Em produção, o acesso é pelo SSO da empresa.
            </p>
          </form>
        )}

        {provedores.data?.oidc && (
          <a
            href="/api/v1/auth/oidc/login"
            className="mt-4 block rounded-md border border-borda px-4 py-2 text-center text-sm"
          >
            Entrar com a conta da empresa
          </a>
        )}
      </div>
    </main>
  );
}
