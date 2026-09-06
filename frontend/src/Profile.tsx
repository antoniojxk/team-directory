import { useEffect, useRef, useState } from 'react'
import {
  ArrowLeft,
  BriefcaseBusiness,
  CheckCheck,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  Pencil,
  Plus,
  ShieldCheck,
} from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { useAuth, useLoad } from './api'
import { ComplianceForm, EmploymentForm, PersonForm } from './Forms'
import type { Classification, Compliance, Confidential, Employment, Profile } from './types'
import {
  Avatar,
  Badge,
  dateText,
  Empty,
  ErrorBox,
  errorText,
  Field,
  Loading,
  Modal,
  SaveForm,
  text,
} from './ui'

export function ProfilePage() {
  const { id } = useParams()
  // Key the profile to clear confidential state immediately when the route changes.
  return <ProfileContent key={id} id={id ?? ''} />
}

function ProfileContent({ id }: { id: string }) {
  const { user, api } = useAuth()
  const [revision, setRevision] = useState(0)
  const result = useLoad<Profile>(`/people/${id}`, revision)
  const classes = useLoad<Classification[]>('/classifications', revision)
  const [editPerson, setEditPerson] = useState(false)
  const [employment, setEmployment] = useState<Employment | 'new' | null>(null)
  const [compliance, setCompliance] = useState<Compliance | 'new' | null>(null)
  const [secret, setSecret] = useState<Confidential | null>(null)
  const [secretError, setSecretError] = useState('')
  const [revealing, setRevealing] = useState(false)
  const [editNotes, setEditNotes] = useState(false)
  const [editSalary, setEditSalary] = useState<Confidential['employments'][number] | null>(null)
  const revealRequest = useRef<AbortController | null>(null)
  useEffect(() => () => revealRequest.current?.abort(), [])
  const hr = user?.roles.includes('hr')
  function done() {
    setEmployment(null)
    setCompliance(null)
    setEditPerson(false)
    setRevision((v) => v + 1)
  }
  function secretDone() {
    setEditNotes(false)
    setEditSalary(null)
    setSecret(null)
  }
  async function reveal() {
    const controller = new AbortController()
    revealRequest.current = controller
    setSecretError('')
    setRevealing(true)
    try {
      const value = await api<Confidential>(`/people/${id}/confidential`, {
        signal: controller.signal,
      })
      if (!controller.signal.aborted) setSecret(value)
    } catch (e) {
      if (!controller.signal.aborted) setSecretError(errorText(e))
    } finally {
      if (!controller.signal.aborted) setRevealing(false)
    }
  }
  const person = result.data
  return (
    <>
      <Link className="back-link" to="/people">
        <ArrowLeft size={16} /> Back to people
      </Link>
      <ErrorBox message={result.error} />
      {result.error && (
        <button className="button" onClick={() => setRevision((v) => v + 1)}>
          Try again
        </button>
      )}
      {result.loading && <Loading />}
      {person && (
        <>
          <section className="profile-heading">
            <Avatar name={person.name} large />
            <div>
              <p className="eyebrow">{person.department}</p>
              <h1>{person.name}</h1>
              <a className="muted profile-email" href={`mailto:${person.work_email}`}>
                <Mail size={16} />
                {person.work_email}
              </a>
            </div>
            {hr && (
              <button className="button" onClick={() => setEditPerson(true)}>
                <Pencil size={15} /> Edit profile
              </button>
            )}
          </section>
          <div className="profile-layout">
            <div>
              <section className="panel">
                <div className="section-heading">
                  <h2>
                    <BriefcaseBusiness size={20} /> Employment
                  </h2>
                  {hr && (
                    <button className="text-button" onClick={() => setEmployment('new')}>
                      <Plus size={16} /> Add employment
                    </button>
                  )}
                </div>
                <ErrorBox message={classes.error} />
                {person.employments.length ? (
                  person.employments.map((e) => (
                    <article key={e.id} className="record">
                      <div className="record-heading">
                        <div>
                          <h3>{e.job_title}</h3>
                          <p className="muted small">
                            {dateText(e.start_date)} –{' '}
                            {e.end_date ? dateText(e.end_date) : 'Present'}
                          </p>
                        </div>
                        <Badge value={e.status} />
                      </div>
                      <div className="record-footer">
                        <span>
                          Classification <strong>{e.classification.name}</strong>
                        </span>
                        {hr && (
                          <button
                            className="text-button"
                            aria-label={`Edit employment ${e.job_title}`}
                            onClick={() => setEmployment(e)}
                          >
                            <Pencil size={14} /> Edit
                          </button>
                        )}
                      </div>
                    </article>
                  ))
                ) : (
                  <Empty title="No employment records">
                    {hr ? 'Add the first role for this person.' : 'No roles have been added yet.'}
                  </Empty>
                )}
              </section>
              <section className="panel">
                <div className="section-heading">
                  <h2>
                    <CheckCheck size={20} /> Compliance & training
                  </h2>
                  {hr && (
                    <button className="text-button" onClick={() => setCompliance('new')}>
                      <Plus size={16} /> Add training
                    </button>
                  )}
                </div>
                {person.compliance_records.length ? (
                  person.compliance_records.map((c) => (
                    <article key={c.id} className="record">
                      <div className="record-heading">
                        <h3>{c.requirement}</h3>
                        <Badge value={c.status} />
                      </div>
                      <div className="training-dates">
                        <span>
                          Completed<strong>{dateText(c.completion_date)}</strong>
                        </span>
                        <span>
                          Expires<strong>{dateText(c.expiry_date)}</strong>
                        </span>
                        {hr && (
                          <button
                            className="text-button"
                            aria-label={`Edit training ${c.requirement}`}
                            onClick={() => setCompliance(c)}
                          >
                            <Pencil size={14} /> Edit
                          </button>
                        )}
                      </div>
                    </article>
                  ))
                ) : (
                  <Empty title="No training records">Training requirements will appear here.</Empty>
                )}
              </section>
            </div>
            <aside>
              <section className="confidential-panel">
                <div className="lock-icon">
                  <LockKeyhole size={24} />
                </div>
                <p className="eyebrow">HANDLE WITH CARE</p>
                <h2>Confidential details</h2>
                <p className="muted">
                  Private notes and salary are kept separate from the public profile.
                </p>
                {hr ? (
                  <>
                    <p className="audit-explainer">
                      <ShieldCheck size={16} /> Every reveal is recorded in access history.
                    </p>
                    <ErrorBox message={secretError} />
                    {secret ? (
                      <>
                        <div className="secret-block">
                          <div className="section-heading">
                            <h3>Private notes</h3>
                            <button className="text-button" onClick={() => setEditNotes(true)}>
                              Edit
                            </button>
                          </div>
                          <p className="private-note">
                            {secret.private_notes || 'No private notes.'}
                          </p>
                        </div>
                        <div className="secret-block">
                          <h3>Annual salary · CAD</h3>
                          {secret.employments.length ? (
                            secret.employments.map((e) => (
                              <div className="salary-row" key={e.employment_id}>
                                <span>
                                  {e.job_title}
                                  <strong>
                                    {new Intl.NumberFormat('en-CA', {
                                      style: 'currency',
                                      currency: 'CAD',
                                    }).format(Number(e.salary))}
                                  </strong>
                                </span>
                                <button
                                  className="text-button"
                                  aria-label={`Edit salary for ${e.job_title}`}
                                  onClick={() => setEditSalary(e)}
                                >
                                  Edit
                                </button>
                              </div>
                            ))
                          ) : (
                            <p>No employment records.</p>
                          )}
                        </div>
                        <button className="button full" onClick={() => setSecret(null)}>
                          <EyeOff size={16} /> Hide confidential details
                        </button>
                      </>
                    ) : (
                      <button className="button primary full" disabled={revealing} onClick={reveal}>
                        <Eye size={16} />
                        {revealing ? 'Recording access…' : 'Reveal confidential details'}
                      </button>
                    )}
                  </>
                ) : (
                  <div className="restricted">
                    <LockKeyhole size={16} /> Available to HR only
                  </div>
                )}
              </section>
              <p className="profile-note">
                This is a fictional profile. All personal and confidential details are synthetic.
              </p>
            </aside>
          </div>
          {editPerson && (
            <PersonForm person={person} onClose={() => setEditPerson(false)} onDone={done} />
          )}
          {employment && (
            <EmploymentForm
              personId={person.id}
              employment={employment === 'new' ? undefined : employment}
              classes={classes.data ?? []}
              onClose={() => setEmployment(null)}
              onDone={done}
            />
          )}
          {compliance && (
            <ComplianceForm
              personId={person.id}
              record={compliance === 'new' ? undefined : compliance}
              onClose={() => setCompliance(null)}
              onDone={done}
            />
          )}
          {editNotes && secret && (
            <Modal title="Edit private notes" onClose={() => setEditNotes(false)}>
              <SaveForm
                onDone={secretDone}
                onSave={(data) =>
                  api(`/people/${id}/confidential`, {
                    method: 'PATCH',
                    body: JSON.stringify({ private_notes: text(data, 'private_notes') }),
                  })
                }
              >
                <label>
                  Private notes
                  <textarea
                    name="private_notes"
                    rows={6}
                    maxLength={5000}
                    defaultValue={secret.private_notes}
                  />
                </label>
                <p className="hint">
                  Saving hides these details. Reveal again to view the updated value.
                </p>
              </SaveForm>
            </Modal>
          )}
          {editSalary && (
            <Modal title="Edit confidential salary" onClose={() => setEditSalary(null)}>
              <SaveForm
                onDone={secretDone}
                onSave={(data) =>
                  api(`/people/${id}/employments/${editSalary.employment_id}/salary`, {
                    method: 'PATCH',
                    body: JSON.stringify({ salary: text(data, 'salary') }),
                  })
                }
              >
                <Field
                  label="Annual salary (CAD)"
                  name="salary"
                  type="number"
                  value={editSalary.salary}
                  min="0"
                  step="0.01"
                />
                <p className="hint">
                  Saving hides these details. Reveal again to view the updated value.
                </p>
              </SaveForm>
            </Modal>
          )}
        </>
      )}
    </>
  )
}
