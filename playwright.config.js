// @ts-check
const { defineConfig, devices } = require('@playwright/test');

const CALDERA_URL = process.env.CALDERA_URL || 'http://localhost:8888';

module.exports = defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['list']],
  timeout: 60_000,
  use: {
    baseURL: CALDERA_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    headless: true,
    httpCredentials: {
      username: process.env.CALDERA_USER || 'admin',
      password: process.env.CALDERA_PASS || 'admin',
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
