import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests against a running stack (Docker Compose with LLM_PROVIDER=fake, so answers are
 * deterministic). Start it first, then: npm run e2e
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  // Generous because the browsers and the whole stack often share one machine (laptop or CI runner)
  expect: { timeout: 30_000 },
  fullyParallel: true,
  // Each worker is a full browser; too many starve the stack of CPU when both share one machine
  workers: process.env.CI ? 2 : 4,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:8090",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
