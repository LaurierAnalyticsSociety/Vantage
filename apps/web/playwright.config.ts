import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: { baseURL: "http://127.0.0.1:3000", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    { command: "../../.venv/bin/python -m uvicorn services.api.app.main:app --app-dir ../.. --host 127.0.0.1 --port 8000", url: "http://127.0.0.1:8000/health", reuseExistingServer: !process.env.CI },
    { command: "npm run dev", url: "http://127.0.0.1:3000", reuseExistingServer: !process.env.CI },
  ],
});
