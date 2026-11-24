import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Vitest runs without globals: Testing Library cannot register its automatic cleanup,
// so each test would otherwise start with the elements rendered by the previous ones.
afterEach(() => {
  cleanup();
});
