import { useState } from 'react'
import { Fingerprint, Pencil, Plus, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth, useLoad } from './api'
import type { Audit, Classification, Page } from './types'
import { Badge, Empty, ErrorBox, Field, Loading, Modal, Pagination, SaveForm, text } from './ui'

export function ClassificationsPage() {
  const { api } = useAuth()
  const [revision, setRevision] = useState(0)
  const [editing, setEditing] = useState<Classification | 'new' | null>(null)
  const result = useLoad<Classification[]>('/classifications', revision)
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">A SHARED VOCABULARY</p>
          <h1>
            Classifications<span className="accent-dot">.</span>
          </h1>
          <p className="muted">Reusable categories that give every role a little context.</p>
        </div>
        <button className="button primary" onClick={() => setEditing('new')}>
          <Plus size={17} /> Add classification
        </button>
      </div>
      <ErrorBox message={result.error} />
      {result.error && (
        <button className="button" onClick={() => setRevision((v) => v + 1)}>
          Try again
        </button>
      )}
      {result.loading && <Loading />}
      {result.data && (
        <section className="panel classification-list">
          {result.data.length ? (
            result.data.map((c) => (
              <div className="classification-row" key={c.id}>
                <div>
                  <h3>{c.name}</h3>
                  <span className="muted small">Available to all employment records</span>
                </div>
                <button
                  className="button"
                  onClick={() => setEditing(c)}
                  aria-label={`Edit classification ${c.name}`}
                >
                  <Pencil size={15} /> Edit
                </button>
              </div>
            ))
          ) : (
            <Empty title="No classifications yet">
              Add a category before creating employment records.
            </Empty>
          )}
        </section>
      )}
      {editing && (
        <Modal
          title={editing === 'new' ? 'Add classification' : 'Edit classification'}
          onClose={() => setEditing(null)}
        >
          <SaveForm
            onDone={() => {
              setEditing(null)
              setRevision((v) => v + 1)
            }}
            onSave={(data) =>
              api(`/classifications${editing === 'new' ? '' : `/${editing.id}`}`, {
                method: editing === 'new' ? 'POST' : 'PUT',
                body: JSON.stringify({ name: text(data, 'name') }),
              })
            }
          >
            <Field
              label="Classification name"
              name="name"
              value={editing === 'new' ? '' : editing.name}
              maxLength={80}
            />
            <p className="hint">
              Names are stored in lowercase. Renaming updates the label on linked employment
              records.
            </p>
          </SaveForm>
        </Modal>
      )}
    </>
  )
}

export function AuditPage() {
  const [page, setPage] = useState(1)
  const [revision, setRevision] = useState(0)
  const result = useLoad<Page<Audit>>(`/audit?page=${page}&page_size=20`, revision)
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">ACCOUNTABLE BY DESIGN</p>
          <h1>
            Access history<span className="accent-dot">.</span>
          </h1>
          <p className="muted">A clear record of who requested confidential details, and when.</p>
        </div>
        <button className="button" onClick={() => setRevision((v) => v + 1)}>
          Refresh history
        </button>
      </div>
      <div className="audit-banner">
        <ShieldCheck size={23} />
        <p>
          Successful reveals and denied attempts are recorded. This history contains field names,
          never the confidential values themselves.
        </p>
      </div>
      <ErrorBox message={result.error} />
      {result.loading && <Loading />}
      {result.data && (
        <section className="panel audit-panel">
          <div className="section-heading">
            <h2>
              <Fingerprint size={20} /> Confidential access{' '}
              <span className="count">{result.data.total}</span>
            </h2>
            <span className="muted small">Newest first · your local time</span>
          </div>
          {result.data.items.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Actor</th>
                    <th>Person</th>
                    <th>Fields requested</th>
                    <th>Outcome</th>
                  </tr>
                </thead>
                <tbody>
                  {result.data.items.map((event) => (
                    <tr key={event.id}>
                      <td className="nowrap">{new Date(event.timestamp).toLocaleString()}</td>
                      <td>
                        <strong>{event.actor}</strong>
                      </td>
                      <td>
                        {event.target_person_id ? (
                          <Link className="text-link" to={`/people/${event.target_person_id}`}>
                            Person #{event.target_person_id}
                          </Link>
                        ) : (
                          `Missing #${event.requested_person_id}`
                        )}
                      </td>
                      <td>
                        {event.field_names.map((field) => (
                          <code className="field-tag" key={field}>
                            {field}
                          </code>
                        ))}
                      </td>
                      <td>
                        <Badge value={event.outcome} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty title="No confidential access yet">
              Open a profile as HR and choose “Reveal confidential details” to create the first
              record.
            </Empty>
          )}
          <Pagination page={page} size={20} total={result.data.total} onChange={setPage} />
        </section>
      )}
    </>
  )
}
