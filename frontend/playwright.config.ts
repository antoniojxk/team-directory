import { defineConfig, devices } from '@playwright/test'

const database = process.env.TEST_DATABASE_URL
if (!database)
  throw new Error('Set TEST_DATABASE_URL to a dedicated PostgreSQL database ending in _test')

const apiPort = Number(process.env.E2E_API_PORT ?? 8001)
const webPort = Number(process.env.E2E_WEB_PORT ?? 5174)
const apiOrigin = `http://127.0.0.1:${apiPort}`
const webOrigin = `http://127.0.0.1:${webPort}`

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: { baseURL: webOrigin, trace: 'off', screenshot: 'only-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `../backend/.venv/bin/python ../scripts/prepare_e2e.py && ../backend/.venv/bin/uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port ${apiPort}`,
      url: `${apiOrigin}/health`,
      reuseExistingServer: false,
      env: {
        DATABASE_URL: database,
        DIRECT_DATABASE_URL: '',
        JWT_SECRET: 'browser-tests-only-secret-with-more-than-32-characters',
        DEMO_VIEWER_PASSWORD: 'viewer-browser-password',
        DEMO_HR_PASSWORD: 'hr-browser-password',
        ACCESS_TOKEN_MINUTES: '30',
        FRONTEND_ORIGINS: JSON.stringify([webOrigin]),
      },
    },
    {
      command: `npm run dev -- --port ${webPort} --strictPort`,
      url: webOrigin,
      reuseExistingServer: false,
      env: { VITE_API_BASE_URL: apiOrigin, API_PROXY_TARGET: apiOrigin },
    },
  ],
})
