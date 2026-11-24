import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import App from "./App.tsx";

it("affiche le nom de l'app", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "Marmotte" })).toBeInTheDocument();
});

it("repart d'une page vide à chaque test", () => {
  render(<App />);
  expect(screen.getAllByRole("heading", { name: "Marmotte" })).toHaveLength(1);
});
