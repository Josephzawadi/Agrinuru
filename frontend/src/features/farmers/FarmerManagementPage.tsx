import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { ApiRequestError, farmerApi } from '../../api/client'
import type { ApiFieldErrors, FarmerInput, FarmerProfile } from '../../types/records'
import '../management.css'

const emptyFarmer: FarmerInput = {
  full_name: '',
  phone_number: '',
  email: '',
  county: '',
  sub_county: '',
  preferred_language: 'English',
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))
}

export function FarmerManagementPage() {
  const [farmers, setFarmers] = useState<FarmerProfile[]>([])
  const [form, setForm] = useState<FarmerInput>(emptyFarmer)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<ApiFieldErrors>({})
  const [notice, setNotice] = useState('')

  async function loadFarmers() {
    setLoading(true)
    setError('')
    try {
      setFarmers(await farmerApi.list())
    } catch {
      setError('Could not load farmer records. Check that the API is running and try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    farmerApi.list()
      .then((records) => {
        if (!cancelled) setFarmers(records)
      })
      .catch(() => {
        if (!cancelled) setError('Could not load farmer records. Check that the API is running and try again.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  function updateField(event: ChangeEvent<HTMLInputElement>) {
    const { name, value } = event.currentTarget
    setForm((current) => ({ ...current, [name]: value }))
    setFieldErrors((current) => ({ ...current, [name]: '' }))
  }

  function startEditing(farmer: FarmerProfile) {
    setEditingId(farmer.id)
    setForm({
      full_name: farmer.full_name,
      phone_number: farmer.phone_number,
      email: farmer.email,
      county: farmer.county,
      sub_county: farmer.sub_county,
      preferred_language: farmer.preferred_language,
    })
    setFieldErrors({})
    setError('')
    setNotice('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function resetForm() {
    setEditingId(null)
    setForm(emptyFarmer)
    setFieldErrors({})
    setError('')
    setNotice('')
  }

  async function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setNotice('')
    setFieldErrors({})

    const digits = form.phone_number.replace(/\D/g, '').length
    if (!/^\+?[0-9][0-9\s().-]*$/.test(form.phone_number.trim()) || digits < 7 || digits > 15) {
      setFieldErrors({ phone_number: 'Enter 7 to 15 digits; spaces, +, hyphens, and parentheses are accepted.' })
      return
    }

    setSaving(true)
    try {
      if (editingId === null) {
        await farmerApi.create(form)
        setNotice('Farmer registered successfully.')
      } else {
        await farmerApi.update(editingId, form)
        setNotice('Farmer details updated successfully.')
      }
      setEditingId(null)
      setForm(emptyFarmer)
      setFarmers(await farmerApi.list())
    } catch (requestError) {
      if (requestError instanceof ApiRequestError) {
        setError(requestError.message)
        setFieldErrors(requestError.fieldErrors)
      } else {
        setError('Could not save the farmer record. Check your connection and try again.')
      }
    } finally {
      setSaving(false)
    }
  }

  async function deleteFarmer(farmer: FarmerProfile) {
    if (!window.confirm(`Delete the farmer record for ${farmer.full_name}?`)) return
    setDeletingId(farmer.id)
    setError('')
    setNotice('')
    try {
      await farmerApi.remove(farmer.id)
      setFarmers((current) => current.filter((record) => record.id !== farmer.id))
      setNotice('Farmer record deleted.')
      if (editingId === farmer.id) resetForm()
    } catch (requestError) {
      setError(requestError instanceof ApiRequestError
        ? requestError.message
        : 'Could not delete the farmer record. Try again.')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section className="management-page" aria-labelledby="farmers-title">
      <div className="management-heading">
        <p className="eyebrow"><span /> Farmer records</p>
        <h1 id="farmers-title">Farmer management</h1>
        <p>Register farmers and keep their contact and location details current.</p>
      </div>

      <div className="management-layout">
        <form className="management-form" onSubmit={submitForm}>
          <div className="form-heading">
            <span className="form-index">{editingId === null ? '01' : 'EDIT'}</span>
            <h2>{editingId === null ? 'Register a farmer' : 'Update farmer details'}</h2>
          </div>

          {error && <p className="form-alert error-alert" role="alert">{error}</p>}
          {notice && <p className="form-alert success-alert" role="status">{notice}</p>}

          <div className="form-grid">
            <label className="form-field field-wide">
              <span>Full name <b aria-hidden="true">*</b></span>
              <input name="full_name" value={form.full_name} onChange={updateField} required maxLength={150} autoComplete="name" aria-invalid={Boolean(fieldErrors.full_name)} />
              {fieldErrors.full_name && <small>{fieldErrors.full_name}</small>}
            </label>
            <label className="form-field">
              <span>Phone number <b aria-hidden="true">*</b></span>
              <input name="phone_number" type="tel" value={form.phone_number} onChange={updateField} required maxLength={30} autoComplete="tel" placeholder="e.g. +254 712 345 678" aria-invalid={Boolean(fieldErrors.phone_number)} />
              {fieldErrors.phone_number && <small>{fieldErrors.phone_number}</small>}
            </label>
            <label className="form-field">
              <span>Email address <b aria-hidden="true">*</b></span>
              <input name="email" type="email" value={form.email} onChange={updateField} required maxLength={254} autoComplete="email" aria-invalid={Boolean(fieldErrors.email)} />
              {fieldErrors.email && <small>{fieldErrors.email}</small>}
            </label>
            <label className="form-field">
              <span>County <b aria-hidden="true">*</b></span>
              <input name="county" value={form.county} onChange={updateField} required maxLength={100} autoComplete="address-level1" aria-invalid={Boolean(fieldErrors.county)} />
              {fieldErrors.county && <small>{fieldErrors.county}</small>}
            </label>
            <label className="form-field">
              <span>Sub-county <b aria-hidden="true">*</b></span>
              <input name="sub_county" value={form.sub_county} onChange={updateField} required maxLength={100} autoComplete="address-level2" aria-invalid={Boolean(fieldErrors.sub_county)} />
              {fieldErrors.sub_county && <small>{fieldErrors.sub_county}</small>}
            </label>
            <label className="form-field field-wide">
              <span>Preferred language <b aria-hidden="true">*</b></span>
              <input name="preferred_language" value={form.preferred_language} onChange={updateField} required maxLength={50} aria-invalid={Boolean(fieldErrors.preferred_language)} />
              {fieldErrors.preferred_language && <small>{fieldErrors.preferred_language}</small>}
            </label>
          </div>

          <div className="form-actions">
            <button className="button-primary" type="submit" disabled={saving}>
              {saving ? 'Saving…' : editingId === null ? 'Register farmer' : 'Save changes'}
              <span aria-hidden="true">→</span>
            </button>
            {editingId !== null && <button className="button-secondary" type="button" onClick={resetForm}>Cancel</button>}
          </div>
        </form>

        <section className="records-panel" aria-labelledby="farmer-list-title">
          <div className="records-heading">
            <div>
              <p className="eyebrow"><span /> Directory</p>
              <h2 id="farmer-list-title">Registered farmers</h2>
            </div>
            <span className="record-count">{loading ? '…' : farmers.length}</span>
          </div>

          {loading ? (
            <p className="empty-state" role="status">Loading farmer records…</p>
          ) : farmers.length === 0 ? (
            <p className="empty-state">No farmers registered yet. Add the first record using the form.</p>
          ) : (
            <div className="record-list">
              {farmers.map((farmer) => (
                <article className="record-row" key={farmer.id}>
                  <div className="record-main">
                    <div className="record-avatar" aria-hidden="true">{farmer.full_name.trim().charAt(0).toUpperCase()}</div>
                    <div>
                      <h3>{farmer.full_name}</h3>
                      <p>{farmer.county} County · {farmer.sub_county}</p>
                      <p>{farmer.phone_number} · {farmer.email}</p>
                    </div>
                  </div>
                  <div className="record-meta">
                    <span>Registered {formatDate(farmer.date_registered)}</span>
                    <div className="record-actions">
                      <button type="button" onClick={() => startEditing(farmer)}>Edit</button>
                      <button type="button" className="delete-action" disabled={deletingId === farmer.id} onClick={() => void deleteFarmer(farmer)}>
                        {deletingId === farmer.id ? 'Deleting…' : 'Delete'}
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
          {!loading && error && farmers.length === 0 && (
            <button className="button-secondary retry-button" type="button" onClick={() => void loadFarmers()}>Retry loading</button>
          )}
        </section>
      </div>
    </section>
  )
}