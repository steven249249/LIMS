import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright configuration.
 *
 * `webServer` automatically starts the Vite dev server before the suite and
 * tears it down afterwards. The Django backend must already be running on
 * port 8000 (in CI we start it as a separate job step; locally use the
 * provided helper script). Tests run serially against a fresh dev server
 * to avoid backend race conditions on the same DB.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    // CI runners default localhost → ::1 (IPv6) but Playwright probes
    // 127.0.0.1 (IPv4); pin Vite to IPv4 with --host to make them agree.
    command: 'npm run dev -- --port 5173 --host 127.0.0.1',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
})
