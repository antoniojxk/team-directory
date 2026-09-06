import { useEffect, useState } from 'react'
import { ArrowUpRight, Plus, Search, SlidersHorizontal, UsersRound } from 'lucide-react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth, useLoad } from './api'
import { PersonForm } from './Forms'
import type { Classification, Page, Person } from './types'
import { Avatar, Empty, ErrorBox, Loading, Pagination } from './ui'

export function Directory() {
  const { user } = useAuth()
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState(params.get('q') ?? '')
  const [adding, setAdding] = useState(false)
  const [revision, setRevision] = useState(0)
  const navigate = useNavigate()
  const page = Math.max(1, Number(params.get('page')) || 1)
  const department = params.get('department') ?? ''
  const status = params.get('status') ?? ''
  const classification = params.get('classification_id') ?? ''
  const query = new URLSearchParams({
    q: params.get('q') ?? '',
    page: String(page),
    page_size: '9',
  })
  if (department) query.set('department', department)
  if (status) query.set('status', status)
  if (classification) query.set('classification_id', classification)
  const result = useLoad<Page<Person>>(`/people?${query}`, revision)
  const departments = useLoad<string[]>('/departments', revision)
  const classes = useLoad<Classification[]>('/classifications', revision)
  // Sync the input when browser back/forward changes the directory URL.
  useEffect(() => {
    setSearch(params.get('q') ?? '')
  }, [params])
  function filter(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    next.delete('page')
    setParams(next)
  }
  const filtered = Boolean(params.get('q') || department || status || classification)
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">OUR WORKSPACE</p>
          <h1>
            The people behind the work<span className="accent-dot">.</span>
          </h1>
          <p className="muted">Find a familiar face. Get to know someone new.</p>
        </div>
        {user?.roles.includes('hr') && (
          <button className="button primary" onClick={() => setAdding(true)}>
            <Plus size={17} /> Add person
          </button>
        )}
      </div>
      <div className="directory-banner">
        <div className="banner-icon">
          <UsersRound size={25} />
        </div>
        <div>
          <h2>One team. Many perspectives.</h2>
          <p>Explore profiles, roles, and the details that bring us together.</p>
        </div>
        <span className="banner-label">THE TEAM DIRECTORY</span>
      </div>
      <section className="directory-section" aria-label="People directory">
        <div className="section-heading">
          <h2>
            People <span className="count">{result.data?.total ?? '—'}</span>
          </h2>
          <span className="muted small">
            {user?.roles.includes('hr') ? 'Manage with care' : 'Public profiles, at a glance'}
          </span>
        </div>
        <form
          className="filters"
          onSubmit={(e) => {
            e.preventDefault()
            filter('q', search)
          }}
        >
          <div className="search-field">
            <Search size={18} />
            <input
              aria-label="Search people by name"
              placeholder="Search people by name…"
              value={search}
              maxLength={120}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button type="submit">Search</button>
          </div>
          <label className="filter-select">
            <span className="sr-only">Department</span>
            <select
              aria-label="Department"
              value={department}
              onChange={(e) => filter('department', e.target.value)}
            >
              <option value="">All departments</option>
              {departments.data?.map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          </label>
          <label className="filter-select">
            <span className="sr-only">Employment status</span>
            <select
              aria-label="Employment status"
              value={status}
              onChange={(e) => filter('status', e.target.value)}
            >
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="on_leave">On leave</option>
              <option value="ended">Ended</option>
            </select>
          </label>
          <label className="filter-select">
            <span className="sr-only">Classification</span>
            <select
              aria-label="Classification"
              value={classification}
              onChange={(e) => filter('classification_id', e.target.value)}
            >
              <option value="">All classifications</option>
              {classes.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        </form>
        <ErrorBox message={departments.error || classes.error} />
        {filtered && (
          <div className="filter-summary">
            <SlidersHorizontal size={14} /> Filters applied{' '}
            <button className="text-button" onClick={() => setParams({})}>
              Clear all
            </button>
          </div>
        )}
        <ErrorBox message={result.error} />
        {result.error && (
          <button className="button" onClick={() => setRevision((v) => v + 1)}>
            Try again
          </button>
        )}
        {result.loading && <Loading />}
        {result.data && (
          <>
            {result.data.items.length ? (
              <div className="people-grid">
                {result.data.items.map((person) => (
                  <Link className="person-card" key={person.id} to={`/people/${person.id}`}>
                    <div className="card-top">
                      <Avatar name={person.name} />
                      <ArrowUpRight size={19} />
                    </div>
                    <h3>{person.name}</h3>
                    <p className="person-email">{person.work_email}</p>
                    <div className="card-bottom">
                      <span className="department-tag">{person.department}</span>
                      <span>View profile</span>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <Empty title="No people found">Try another name or clear your filters.</Empty>
            )}
            <Pagination
              page={page}
              size={9}
              total={result.data.total}
              onChange={(page) => {
                const next = new URLSearchParams(params)
                next.set('page', String(page))
                setParams(next)
              }}
            />
          </>
        )}
      </section>
      {adding && (
        <PersonForm
          onClose={() => setAdding(false)}
          onDone={(person) => navigate(`/people/${person.id}`)}
        />
      )}
    </>
  )
}
