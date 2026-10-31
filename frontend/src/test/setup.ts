import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Desmonta os componentes entre os testes (sem `globals: true` não é automático).
afterEach(() => cleanup());
