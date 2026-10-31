import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { EmBreve } from "./pages/EmBreve";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/requisicoes" replace />} />
        <Route
          path="/requisicoes"
          element={
            <EmBreve
              titulo="Requisições"
              descricao="Abertura de RFI/RFP, upload do questionário, revisão, chat e exportação."
              sprint={6}
            />
          }
        />
        <Route
          path="/tarefas"
          element={
            <EmBreve
              titulo="Minhas tarefas"
              descricao="Perguntas que sua equipe precisa validar, com prazos."
              sprint={7}
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
              sprint={8}
            />
          }
        />
        <Route
          path="/admin"
          element={
            <EmBreve
              titulo="Administração"
              descricao="Equipes, responsáveis, clientes (siglas) e regras de cobrança."
              sprint={2}
            />
          }
        />
        <Route
          path="*"
          element={
            <EmBreve titulo="Página não encontrada" descricao="Use o menu ao lado." sprint={1} />
          }
        />
      </Route>
    </Routes>
  );
}
