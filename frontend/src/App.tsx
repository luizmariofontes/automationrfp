import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { RequireAuth, RequireRole } from "./components/RequireAuth";
import { Admin } from "./pages/admin/Admin";
import { Auditoria } from "./pages/admin/Auditoria";
import { Clientes } from "./pages/admin/Clientes";
import { Equipes } from "./pages/admin/Equipes";
import { Regras } from "./pages/admin/Regras";
import { EmBreve } from "./pages/EmBreve";
import { Login } from "./pages/Login";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/requisicoes" replace />} />
          <Route
            path="/requisicoes"
            element={
              <EmBreve
                titulo="Requisições"
                descricao="Abertura de RFI/RFP, upload do questionário, revisão, chat e exportação."
                sprint={7}
              />
            }
          />
          <Route
            path="/tarefas"
            element={
              <EmBreve
                titulo="Minhas tarefas"
                descricao="Perguntas que sua equipe precisa validar, com prazos."
                sprint={8}
              />
            }
          />
          <Route
            path="/conhecimento"
            element={
              <EmBreve
                titulo="Base de conhecimento"
                descricao="Documentos que alimentam as respostas, com versão, dono e validade."
                sprint={3}
              />
            }
          />
          <Route
            path="/biblioteca"
            element={
              <EmBreve
                titulo="Biblioteca de respostas"
                descricao="Respostas aprovadas e anonimizadas, reaproveitadas em novas requisições."
                sprint={9}
              />
            }
          />
          <Route element={<RequireRole papeis={["admin"]} />}>
            <Route path="/admin" element={<Admin />}>
              <Route index element={<Navigate to="clientes" replace />} />
              <Route path="clientes" element={<Clientes />} />
              <Route path="equipes" element={<Equipes />} />
              <Route path="escalonamento" element={<Regras />} />
              <Route path="auditoria" element={<Auditoria />} />
            </Route>
          </Route>
          <Route
            path="*"
            element={
              <EmBreve titulo="Página não encontrada" descricao="Use o menu ao lado." sprint={1} />
            }
          />
        </Route>
      </Route>
    </Routes>
  );
}
