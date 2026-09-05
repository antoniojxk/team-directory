import { defineConfig, devices } from '@playwright/test'

const database = process.env.TEST_DATABASE_URL
if (!database)
  throw new Error('Set TEST_DATABASE_URL to a dedicated PostgreSQL database ending in _test')

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:5174', trace: 'off', screenshot: 'only-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command:
        '../backend/.venv/bin/python ../scripts/prepare_e2e.py && ../backend/.venv/bin/uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8001',
      url: 'http://127.0.0.1:8001/health',
      reuseExistingServer: false,
      env: {
        DATABASE_URL: database,
        DIRECT_DATABASE_URL: '',
        JWT_SECRET: 'browser-tests-only-secret-with-more-than-32-characters',
        DEMO_VIEWER_PASSWORD: 'viewer-browser-password',
        DEMO_HR_PASSWORD: 'hr-browser-password',
        ACCESS_TOKEN_MINUTES: '30',
      },
    },
    {
      command: 'npm run dev -- --port 5174 --strictPort',
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: false,
      env: { API_PROXY_TARGET: 'http://127.0.0.1:8001' },
    },
  ],
})
