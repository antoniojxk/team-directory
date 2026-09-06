import { expect, test, type Page } from '@playwright/test'

async function login(page: Page, role: 'viewer' | 'hr') {
  await page.goto('/login')
  await page.getByRole('radio', { name: role === 'viewer' ? 'Viewer' : 'HR', exact: false }).check()
  await page.getByLabel('Demo password').fill(`${role}-browser-password`)
  await page.getByRole('button', { name: `Continue as ${role === 'hr' ? 'HR' : 'Viewer'}` }).click()
  await expect(page.getByRole('heading', { name: 'The people behind the work.' })).toBeVisible()
}

test('Viewer can search and paginate but cannot edit or reveal; direct API denial is audited', async ({
  page,
}) => {
  await login(page, 'viewer')
  await expect(page.getByText('Viewer · read only')).toBeVisible()
  await expect(page.locator('.person-card')).toHaveCount(9)
  await page.getByRole('button', { name: 'Next page' }).click()
  await expect(page.getByText('Page 2 of 2')).toBeVisible()
  await page.getByRole('textbox', { name: 'Search people by name' }).fill('Avery')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.locator('.person-card')).toHaveCount(1)
  await expect(page.getByRole('button', { name: 'Add person' })).toHaveCount(0)
  const confidentialRequests: string[] = []
  page.on('request', (request) => {
    if (request.url().endsWith('/confidential')) confidentialRequests.push(request.url())
  })
  await page.getByRole('link', { name: /Avery Chen/ }).click()
  await expect(page.getByRole('heading', { name: 'Avery Chen' })).toBeVisible()
  await expect(page.getByText('Available to HR only')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Reveal confidential details' })).toHaveCount(0)
  expect(confidentialRequests).toEqual([])
  const auth = await page.request.post('/api/auth/token', {
    form: { username: 'viewer', password: 'viewer-browser-password' },
  })
  const token = (await auth.json()).access_token
  const denied = await page.request.get('/api/people/1/confidential', {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(denied.status()).toBe(403)
  expect(await denied.text()).not.toContain('Synthetic demo note')
  await page.goto('/audit')
  // Browser refresh has intentionally discarded the in-memory session.
  await expect(page.getByRole('heading', { name: 'Meet your demo team' })).toBeVisible()
})

test('HR explicitly reveals, updates confidential notes, and sees the audit record', async ({
  page,
}) => {
  await login(page, 'hr')
  await expect(page.getByText('HR + Viewer · full access')).toBeVisible()
  await page.screenshot({ path: '../docs/directory-desktop.png', fullPage: true })
  const requests: string[] = []
  page.on('request', (request) => {
    if (request.url().endsWith('/confidential') && request.method() === 'GET')
      requests.push(request.url())
  })
  await page.getByRole('link', { name: /Avery Chen/ }).click()
  await expect(page.getByRole('button', { name: 'Edit profile' })).toBeVisible()
  await expect(page.getByText('Synthetic demo note:', { exact: false })).toHaveCount(0)
  expect(requests).toEqual([])
  await page.getByRole('button', { name: 'Reveal confidential details' }).click()
  await expect(page.getByText('Synthetic demo note:', { exact: false })).toBeVisible()
  expect(requests).toHaveLength(1)
  await expect(page.getByText('$55,000.00')).toBeVisible()
  await page
    .locator('.secret-block')
    .filter({ hasText: 'Private notes' })
    .getByRole('button', { name: 'Edit', exact: true })
    .click()
  await page
    .getByRole('textbox', { name: 'Private notes', exact: true })
    .fill('Synthetic browser test note.')
  await page.getByRole('button', { name: 'Save changes' }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByText('Synthetic browser test note.')).toHaveCount(0)
  await page.getByRole('button', { name: 'Reveal confidential details' }).click()
  await expect(page.getByText('Synthetic browser test note.')).toBeVisible()
  const viewerLogin = await page.request.post('/api/auth/token', {
    form: { username: 'viewer', password: 'viewer-browser-password' },
  })
  await page.request.get('/api/people/1/confidential', {
    headers: { Authorization: `Bearer ${(await viewerLogin.json()).access_token}` },
  })
  await page.getByRole('link', { name: 'Access history', exact: true }).click()
  await expect(page.getByRole('cell', { name: 'success', exact: true }).first()).toBeVisible()
  await expect(page.getByRole('cell', { name: 'denied', exact: true }).first()).toBeVisible()
  await expect(page.getByText('Synthetic browser test note.')).toHaveCount(0)
  const stored = await page.evaluate(() => ({
    local: Object.keys(localStorage),
    session: Object.keys(sessionStorage),
  }))
  expect(stored).toEqual({ local: [], session: [] })
})

test('HR forms create a profile, employment and training, and report duplicate validation', async ({
  page,
}) => {
  await login(page, 'hr')
  await expect(page.getByText('HR + Viewer · full access')).toBeVisible()
  await page.getByRole('button', { name: 'Add person' }).click()
  await page.getByLabel('Full name').fill('Taylor Demo')
  await page.getByLabel('Work email').fill('taylor.demo@example.com')
  await page.getByLabel('Department', { exact: true }).last().fill('Operations')
  await page.getByRole('button', { name: 'Create person' }).click()
  await expect(page.getByRole('heading', { name: 'Taylor Demo' })).toBeVisible()
  await page.getByRole('button', { name: 'Add employment' }).click()
  await page.getByLabel('Job title').fill('Demo Analyst')
  await page.getByLabel('Start date', { exact: true }).fill('2026-01-01')
  await page
    .getByRole('combobox', { name: 'Classification', exact: true })
    .selectOption({ label: 'employee' })
  await page.getByLabel('Annual salary (CAD, confidential)').fill('65000')
  await page.getByRole('button', { name: 'Save changes' }).click()
  await expect(page.getByRole('heading', { name: 'Demo Analyst' })).toBeVisible()
  await page.getByRole('button', { name: 'Add training' }).click()
  await page.getByLabel('Training requirement').fill('Demo onboarding')
  await page
    .getByRole('combobox', { name: 'Completion status', exact: true })
    .selectOption('completed')
  await page.getByLabel('Completion date', { exact: true }).fill('2026-01-02')
  await page.getByRole('button', { name: 'Save changes' }).click()
  await expect(page.getByRole('heading', { name: 'Demo onboarding' })).toBeVisible()
  await page.getByRole('button', { name: 'Edit profile' }).click()
  await page.getByLabel('Work email').fill('avery.chen@example.com')
  await page.getByRole('button', { name: 'Save profile' }).click()
  await expect(page.getByRole('alert')).toContainText('conflicts with an existing or linked record')
  await page.getByRole('button', { name: 'Close dialog' }).click()
  await expect(page.getByRole('heading', { name: 'Taylor Demo' })).toBeVisible()
})

test('Expired sessions and server errors are clear; mobile layout remains usable', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await login(page, 'viewer')
  await page.screenshot({ path: '../docs/directory-mobile.png', fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  )
  await page.route('**/api/people?**', (route) =>
    route.fulfill({
      status: 503,
      json: { detail: 'The database is temporarily unavailable. Please try again.' },
    }),
  )
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  // Change the query to issue a fresh request.
  await page.getByRole('textbox', { name: 'Search people by name' }).fill('offline')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('temporarily unavailable')
  await page.unroute('**/api/people?**')
  await page.route('**/api/people?**', (route) =>
    route.fulfill({ status: 401, json: { detail: 'Expired' } }),
  )
  await page.getByRole('button', { name: 'Try again' }).click()
  await expect(page.getByRole('heading', { name: 'Meet your demo team' })).toBeVisible()
  await expect(page.getByRole('status')).toContainText('session expired')
})
