import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";

import App from "./App.tsx";

it("affiche le nom de l'app", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: "Marmotte" })).toBeInTheDocument();
});
