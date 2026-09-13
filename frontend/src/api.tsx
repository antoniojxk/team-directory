import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import type { User } from './types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

async function request<T>(
  path: string,
  token: string | null,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof URLSearchParams))
    headers.set('Content-Type', 'application/json')
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/api${path}`, { ...options, headers, cache: 'no-store' })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, 'Unable to reach the server. Check your connection and try again.')
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const fields = body?.errors
      ?.map((e: { field: string }) => e.field.replace(/^body\./, '').replaceAll('_', ' '))
      .join(', ')
    throw new ApiError(
      response.status,
      `${typeof body?.detail === 'string' ? body.detail : 'The server could not complete this request.'}${fields ? ` Fields: ${fields}.` : ''}`,
    )
  }
  return response.status === 204 ? (undefined as T) : response.json()
}

type Auth = {
  user: User | null
  message: string
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  api: <T>(path: string, options?: RequestInit) => Promise<T>
}
const AuthContext = createContext<Auth | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [expiresAt, setExpiresAt] = useState<number | null>(null)
  const [message, setMessage] = useState('')
  const clear = useCallback((reason: string) => {
    setToken(null)
    setUser(null)
    setExpiresAt(null)
    setMessage(reason)
  }, [])
  useEffect(() => {
    if (!expiresAt) return
    const timer = window.setTimeout(
      () => clear('Your session expired. Sign in again to continue.'),
      Math.max(0, expiresAt - Date.now()),
    )
    return () => clearTimeout(timer)
  }, [expiresAt, clear])
  const api = useCallback(
    async <T,>(path: string, options?: RequestInit) => {
      try {
        return await request<T>(path, token, options)
      } catch (error) {
        if (error instanceof ApiError && error.status === 401)
          clear('Your session expired or is invalid. Sign in again to continue.')
        throw error
      }
    },
    [token, clear],
  )
  const login = async (username: string, password: string) => {
    const result = await request<{ access_token: string; expires_in: number }>(
      '/auth/token',
      null,
      {
        method: 'POST',
        body: new URLSearchParams({ username, password }),
      },
    )
    const currentUser = await request<User>('/auth/me', result.access_token)
    setToken(result.access_token)
    setUser(currentUser)
    setExpiresAt(Date.now() + result.expires_in * 1000)
    setMessage('')
  }
  return (
    <AuthContext.Provider
      value={{ user, message, login, logout: () => clear('You have signed out.'), api }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('AuthProvider is missing')
  return value
}

export function useLoad<T>(path: string, revision = 0) {
  const { api } = useAuth()
  const [state, setState] = useState<{ data?: T; error?: string; loading: boolean }>({
    loading: true,
  })
  useEffect(() => {
    const controller = new AbortController()
    setState({ loading: true })
    api<T>(path, { signal: controller.signal }).then(
      (data) => {
        if (!controller.signal.aborted) setState({ data, loading: false })
      },
      (error) => {
        if (!controller.signal.aborted) setState({ error: error.message, loading: false })
      },
    )
    return () => controller.abort()
  }, [path, revision, api])
  return state
}
