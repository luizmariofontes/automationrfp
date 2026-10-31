import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getMe, login, logout, type Papel } from "./api";

export const ME_KEY = ["auth", "me"] as const;

export function useUsuario() {
  return useQuery({ queryKey: ME_KEY, queryFn: getMe, retry: false, staleTime: 60_000 });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ email, senha }: { email: string; senha: string }) => login(email, senha),
    onSuccess: (usuario) => qc.setQueryData(ME_KEY, usuario),
  });
}

export function useLogout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSettled: () => {
      qc.setQueryData(ME_KEY, null);
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== "auth" });
    },
  });
}

export const NOMES_PAPEIS: Record<Papel, string> = {
  admin: "Administrador",
  analista: "Analista",
  validador: "Validador",
  gestor_conhecimento: "Gestor de conhecimento",
};
