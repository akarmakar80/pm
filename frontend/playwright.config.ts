import { defineConfig, devices } from "@playwright/test";

// Requires the full stack to be running: docker-compose up --build -d
// Backend at http://localhost:8000 proxies all routes including the frontend.
export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: "http://localhost:8000",
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
