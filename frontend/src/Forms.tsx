import { useState } from 'react'
import { useAuth } from './api'
import type { Classification, Compliance, Employment, Person } from './types'
import { Field, Modal, optionalDate, SaveForm, text } from './ui'

export function PersonForm({
  person,
  onClose,
  onDone,
}: {
  person?: Person
  onClose: () => void
  onDone: (person: Person) => void
}) {
  const { api } = useAuth()
  let saved: Person
  return (
    <Modal title={person ? 'Edit profile' : 'Add a person'} onClose={onClose}>
      <p className="muted">
        Use fictional details only. Public profile fields are visible to both roles.
      </p>
      <SaveForm
        label={person ? 'Save profile' : 'Create person'}
        onDone={() => onDone(saved)}
        onSave={async (data) => {
          saved = await api<Person>(person ? `/people/${person.id}` : '/people', {
            method: person ? 'PUT' : 'POST',
            body: JSON.stringify({
              name: text(data, 'name'),
              work_email: text(data, 'work_email'),
              department: text(data, 'department'),
            }),
          })
        }}
      >
        <Field label="Full name" name="name" value={person?.name} maxLength={120} />
        <Field
          label="Work email"
          name="work_email"
          type="email"
          value={person?.work_email}
          maxLength={254}
        />
        <Field label="Department" name="department" value={person?.department} maxLength={80} />
      </SaveForm>
    </Modal>
  )
}

export function EmploymentForm({
  personId,
  employment,
  classes,
  onClose,
  onDone,
}: {
  personId: number
  employment?: Employment
  classes: Classification[]
  onClose: () => void
  onDone: () => void
}) {
  const { api } = useAuth()
  const [start, setStart] = useState(employment?.start_date ?? '')
  return (
    <Modal title={employment ? 'Edit employment' : 'Add employment'} onClose={onClose}>
      <SaveForm
        onDone={onDone}
        onSave={(data) =>
          api(`/people/${personId}/employments${employment ? `/${employment.id}` : ''}`, {
            method: employment ? 'PUT' : 'POST',
            body: JSON.stringify({
              job_title: text(data, 'job_title'),
              start_date: text(data, 'start_date'),
              end_date: optionalDate(data, 'end_date'),
              status: text(data, 'status'),
              classification_id: Number(data.get('classification_id')),
              ...(!employment ? { salary: text(data, 'salary') } : {}),
            }),
          })
        }
      >
        <Field label="Job title" name="job_title" value={employment?.job_title} maxLength={120} />
        <div className="form-grid">
          <label>
            Start date
            <input
              type="date"
              name="start_date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              required
            />
          </label>
          <Field
            label="End date (optional)"
            name="end_date"
            type="date"
            value={employment?.end_date}
            required={false}
            min={start}
          />
        </div>
        <div className="form-grid">
          <label>
            Employment status
            <select name="status" defaultValue={employment?.status ?? 'active'}>
              <option value="active">Active</option>
              <option value="on_leave">On leave</option>
              <option value="ended">Ended</option>
            </select>
          </label>
          <label>
            Classification
            <select
              name="classification_id"
              defaultValue={employment?.classification.id ?? ''}
              required
            >
              <option value="" disabled>
                Select classification
              </option>
              {classes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        {!employment && (
          <>
            <Field
              label="Annual salary (CAD, confidential)"
              name="salary"
              type="number"
              min="0"
              step="0.01"
            />
            <p className="hint">Synthetic annualized amount, including contractors and interns.</p>
          </>
        )}
        {employment && (
          <p className="hint">To change salary, reveal confidential details on the profile.</p>
        )}
      </SaveForm>
    </Modal>
  )
}

export function ComplianceForm({
  personId,
  record,
  onClose,
  onDone,
}: {
  personId: number
  record?: Compliance
  onClose: () => void
  onDone: () => void
}) {
  const { api } = useAuth()
  const [status, setStatus] = useState(record?.status ?? 'pending')
  const [completed, setCompleted] = useState(record?.completion_date ?? '')
  return (
    <Modal title={record ? 'Edit training record' : 'Add training record'} onClose={onClose}>
      <SaveForm
        onDone={onDone}
        onSave={(data) =>
          api(`/people/${personId}/compliance${record ? `/${record.id}` : ''}`, {
            method: record ? 'PUT' : 'POST',
            body: JSON.stringify({
              requirement: text(data, 'requirement'),
              status,
              completion_date:
                status === 'completed' ? optionalDate(data, 'completion_date') : null,
              expiry_date: status === 'completed' ? optionalDate(data, 'expiry_date') : null,
            }),
          })
        }
      >
        <Field
          label="Training requirement"
          name="requirement"
          value={record?.requirement}
          maxLength={160}
        />
        <label>
          Completion status
          <select name="status" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="pending">Pending</option>
            <option value="completed">Completed</option>
          </select>
        </label>
        {status === 'completed' && (
          <div className="form-grid">
            <label>
              Completion date
              <input
                type="date"
                name="completion_date"
                required
                value={completed}
                onChange={(e) => setCompleted(e.target.value)}
              />
            </label>
            <Field
              label="Expiry date (optional)"
              name="expiry_date"
              type="date"
              value={record?.expiry_date}
              min={completed}
              required={false}
            />
          </div>
        )}
      </SaveForm>
    </Modal>
  )
}
