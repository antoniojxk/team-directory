import { writeFileSync } from 'node:fs'

const required = (name) => {
  const value = process.env[name]
  if (!value || !/^[a-z0-9][a-z0-9-]*$/.test(value)) {
    throw new Error(`${name} must be a non-empty resource ID`)
  }
  return value
}
const site = required('FIREBASE_HOSTING_SITE_ID')
const api = new URL(process.env.VITE_API_BASE_URL ?? '')
if (
  api.protocol !== 'https:' ||
  api.username ||
  api.password ||
  api.pathname !== '/' ||
  api.search ||
  api.hash
) {
  throw new Error(
    'VITE_API_BASE_URL must be an HTTPS origin without credentials, path, query or fragment',
  )
}
const config = {
  hosting: {
    site,
    public: 'frontend/dist',
    ignore: ['firebase.json', '**/.*', '**/node_modules/**'],
    headers: [
      {
        source: '**',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'same-origin' },
          { key: 'Cache-Control', value: 'no-cache' },
          {
            key: 'Content-Security-Policy',
            value: `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self' ${api.origin}; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`,
          },
        ],
      },
      {
        source: '/assets/**',
        headers: [{ key: 'Cache-Control', value: 'public,max-age=31536000,immutable' }],
      },
    ],
    rewrites: [
      ...['/', '/login', '/people', '/people/*', '/audit', '/classifications'].map((source) => ({
        source,
        destination: '/index.html',
      })),
    ],
  },
}
writeFileSync('firebase.json', `${JSON.stringify(config, null, 2)}\n`)
