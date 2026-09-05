import { useState, type FormEvent } from 'react'
import {
  BookOpen,
  ChevronRight,
  Fingerprint,
  Layers3,
  LogOut,
  ShieldCheck,
  UsersRound,
} from 'lucide-react'
import { Link, Navigate, NavLink, Outlet, Route, Routes, useNavigate } from 'react-router-dom'
import { useAuth } from './api'
import { ErrorBox, errorText } from './ui'
import { Directory } from './Directory'
import { ProfilePage } from './Profile'
import { AuditPage, ClassificationsPage } from './Records'

function Login() {
  const { user, login, message } = useAuth()
  const [role, setRole] = useState('viewer')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()
  if (user) return <Navigate to="/people" replace />
  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(role, password)
      setPassword('')
      navigate('/people')
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  return (
    <main className="login-page">
      <section className="login-story">
        <Link className="brand" to="/">
          <span className="brand-mark">
            <UsersRound size={24} />
          </span>
          Team Directory<span className="brand-dot">.</span>
        </Link>
        <div>
          <p className="eyebrow light">A SMALL TEAM. A CLEARER PICTURE.</p>
          <h1>
            Good work starts
            <br />
            with people.
          </h1>
          <p className="story-copy">
            A simple place to get to know the team, keep records organized, and handle sensitive
            details with care.
          </p>
          <div className="story-tags">
            <span>
              <UsersRound size={16} /> One shared directory
            </span>
            <span>
              <ShieldCheck size={16} /> Thoughtful permissions
            </span>
            <span>
              <Fingerprint size={16} /> Accountable access
            </span>
          </div>
        </div>
        <p className="story-footer">A portfolio demo · Every person and record is fictional</p>
      </section>
      <section className="login-form">
        <div className="login-card">
          <p className="eyebrow">TAKE A LOOK AROUND</p>
          <h2>Meet your demo team</h2>
          <p className="muted">Choose a role to explore its perspective.</p>
          {message && (
            <p className="notice" role="status">
              {message}
            </p>
          )}
          <form onSubmit={submit}>
            <fieldset disabled={busy}>
              <legend className="sr-only">Choose demo role</legend>
              <div className="role-options">
                {['viewer', 'hr'].map((r) => (
                  <label key={r} className={`role-option ${role === r ? 'selected' : ''}`}>
                    <input
                      type="radio"
                      name="role"
                      value={r}
                      checked={role === r}
                      onChange={() => {
                        setRole(r)
                        setPassword('')
                        setError('')
                      }}
                    />
                    <strong>{r === 'hr' ? 'HR' : 'Viewer'}</strong>
                    <small>{r === 'hr' ? 'Manage & review' : 'Browse & discover'}</small>
                  </label>
                ))}
              </div>
              <p className="role-description">
                {role === 'viewer'
                  ? 'Explore public profiles, employment history and training records.'
                  : 'Manage people and classifications, reveal confidential details, and review access history.'}
              </p>
              <label>
                Demo password
                <input
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  maxLength={1024}
                />
              </label>
            </fieldset>
            <ErrorBox message={error} />
            <button className="button primary full" disabled={busy}>
              {busy ? 'Signing in…' : `Continue as ${role === 'hr' ? 'HR' : 'Viewer'}`}
              <ChevronRight size={18} />
            </button>
          </form>
          <p className="login-help">
            Use the demo password supplied by the project owner. For local setup, find it in your{' '}
            <code>.env</code> file.
          </p>
          <a className="text-link" href="/docs" target="_blank" rel="noreferrer">
            <BookOpen size={16} /> Explore the API documentation
          </a>
        </div>
      </section>
    </main>
  )
}

function Layout() {
  const { user, logout } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  const hr = user.role === 'hr'
  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <aside className="sidebar">
        <Link className="brand" to="/people">
          <span className="brand-mark">
            <UsersRound size={21} />
          </span>
          <span>
            Team <br />
            Directory<span className="brand-dot">.</span>
          </span>
        </Link>
        <div className="nav-heading">WORKSPACE</div>
        <nav aria-label="Main navigation">
          <NavLink to="/people">
            <UsersRound size={19} /> People
          </NavLink>
          {hr && (
            <>
              <NavLink to="/classifications">
                <Layers3 size={19} /> Classifications
              </NavLink>
              <NavLink to="/audit">
                <Fingerprint size={19} /> Access history
              </NavLink>
            </>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="demo-note">
            <ShieldCheck size={20} />
            <strong>A little demo, with care.</strong>
            <p>Synthetic data. Real permission checks. Confidential access leaves a record.</p>
            <a href="/docs" target="_blank" rel="noreferrer">
              API documentation ↗
            </a>
          </div>
          <div className="session">
            <span className="session-avatar">{hr ? 'HR' : 'V'}</span>
            <div>
              <strong>{hr ? 'HR' : 'Viewer'} account</strong>
              <small>Demo workspace</small>
            </div>
            <button className="icon-button" onClick={logout} aria-label="Sign out">
              <LogOut size={18} />
            </button>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>
            Workspace <ChevronRight size={14} /> <strong>Team Directory</strong>
          </span>
          <span className={`role-pill ${hr ? 'hr' : ''}`}>
            <ShieldCheck size={14} /> {hr ? 'HR · full access' : 'Viewer · read only'}
          </span>
        </header>
        <main id="main" className="content">
          <Outlet />
        </main>
        <footer className="app-footer">
          Built for people. Designed for trust.<span>Portfolio project · Synthetic data only</span>
        </footer>
      </div>
    </div>
  )
}

function HrOnly({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  return user?.role === 'hr' ? (
    children
  ) : (
    <ErrorBox message="You do not have permission to view this page. Switch to the HR account to continue." />
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/people" replace />} />
        <Route path="/people" element={<Directory />} />
        <Route path="/people/:id" element={<ProfilePage />} />
        <Route
          path="/audit"
          element={
            <HrOnly>
              <AuditPage />
            </HrOnly>
          }
        />
        <Route
          path="/classifications"
          element={
            <HrOnly>
              <ClassificationsPage />
            </HrOnly>
          }
        />
        <Route
          path="*"
          element={
            <>
              <h1>Page not found</h1>
              <Link to="/people">Return to the directory</Link>
            </>
          }
        />
      </Route>
    </Routes>
  )
}
