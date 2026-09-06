import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { AlertCircle, ArrowLeft, ArrowRight, X } from 'lucide-react'

export const errorText = (error: unknown) =>
  error instanceof Error ? error.message : 'Something went wrong. Please try again.'
export const readable = (value: string) => value.replaceAll('_', ' ')
export const dateText = (value: string | null) =>
  value
    ? new Date(`${value}T12:00:00`).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    : '—'
export function ErrorBox({ message }: { message?: string }) {
  return message ? (
    <div className="error-box" role="alert">
      <AlertCircle size={18} />
      <span>{message}</span>
    </div>
  ) : null
}
export function Loading() {
  return (
    <div className="empty" role="status">
      <span className="spinner" /> Loading records…
    </div>
  )
}
export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  )
}
export function Badge({ value }: { value: string }) {
  return <span className={`badge badge-${value}`}>{readable(value)}</span>
}
export function Avatar({ name, large = false }: { name: string; large?: boolean }) {
  return (
    <span
      className={`avatar tone-${name.charCodeAt(0) % 4} ${large ? 'avatar-large' : ''}`}
      aria-hidden="true"
    >
      {name
        .split(' ')
        .map((x) => x[0])
        .slice(0, 2)
        .join('')}
    </span>
  )
}
export function Pagination({
  page,
  size,
  total,
  onChange,
}: {
  page: number
  size: number
  total: number
  onChange: (page: number) => void
}) {
  const pages = Math.max(1, Math.ceil(total / size))
  return (
    <div className="pagination">
      <span>
        {total
          ? `${(page - 1) * size + 1}-${Math.min(page * size, total)} of ${total}`
          : '0 results'}
      </span>
      <div>
        <button
          className="icon-button"
          aria-label="Previous page"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          <ArrowLeft size={17} />
        </button>
        <span>
          Page {page} of {pages}
        </span>
        <button
          className="icon-button"
          aria-label="Next page"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
        >
          <ArrowRight size={17} />
        </button>
      </div>
    </div>
  )
}
export function Modal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    ref.current?.showModal()
  }, [])
  return (
    <dialog ref={ref} onCancel={onClose} aria-labelledby="dialog-title">
      <div className="modal-heading">
        <h2 id="dialog-title">{title}</h2>
        <button className="icon-button" aria-label="Close dialog" onClick={onClose}>
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  )
}
export function SaveForm({
  children,
  onSave,
  onDone,
  label = 'Save changes',
}: {
  children: ReactNode
  onSave: (data: FormData) => Promise<unknown>
  onDone: () => void
  label?: string
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setBusy(true)
    const data = new FormData(event.currentTarget)
    try {
      await onSave(data)
      onDone()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  return (
    <form onSubmit={submit}>
      <fieldset disabled={busy}>{children}</fieldset>
      <ErrorBox message={error} />
      <div className="form-actions">
        <button className="button primary" disabled={busy}>
          {busy ? 'Saving…' : label}
        </button>
      </div>
    </form>
  )
}
export function Field({
  label,
  name,
  value,
  type = 'text',
  required = true,
  maxLength,
  min,
  step,
}: {
  label: string
  name: string
  value?: string | number | null
  type?: string
  required?: boolean
  maxLength?: number
  min?: string
  step?: string
}) {
  return (
    <label>
      {label}
      <input
        name={name}
        type={type}
        defaultValue={value ?? ''}
        required={required}
        maxLength={maxLength}
        min={min}
        step={step}
      />
    </label>
  )
}
export const text = (data: FormData, name: string) => String(data.get(name) ?? '').trim()
export const optionalDate = (data: FormData, name: string) => text(data, name) || null
