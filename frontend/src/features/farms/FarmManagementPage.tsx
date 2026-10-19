import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { ApiRequestError, farmApi, farmerApi } from '../../api/client'
import type { ApiFieldErrors, Farm, FarmInput, FarmerProfile } from '../../types/records'
import '../management.css'

const emptyFarm = {
  farmer: '',
  farm_name: '',
  location: '',
  approximate_size_acres: '',
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))
}

export function FarmManagementPage() {
  const [farms, setFarms] = useState<Farm[]>([])
  const [farmers, setFarmers] = useState<FarmerProfile[]>([])
  const [form, setForm] = useState(emptyFarm)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<ApiFieldErrors>({})
  const [notice, setNotice] = useState('')

  async function loadRecords() {
    setLoading(true)
    setError('')
    try {
      const [farmerRecords, farmRecords] = await Promise.all([
        farmerApi.list(),
        farmApi.list(),
      ])
      setFarmers(farmerRecords)
      setFarms(farmRecords)
    } catch {
      setError('Could not load farms and farmer choices. Check that the API is running and try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    Promise.all([farmerApi.list(), farmApi.list()])
      .then(([farmerRecords, farmRecords]) => {
        if (!cancelled) {
          setFarmers(farmerRecords)
          setFarms(farmRecords)
        }
      })
      .catch(() => {
        if (!cancelled) setError('Could not load farms and farmer choices. Check that the API is running and try again.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  function updateField(event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const { name, value } = event.currentTarget
    setForm((current) => ({ ...current, [name]: value }))
    setFieldErrors((current) => ({ ...current, [name]: '' }))
  }

  function resetForm() {
    setEditingId(null)
    setForm(emptyFarm)
    setFieldErrors({})
    setError('')
    setNotice('')
  }

  function startEditing(farm: Farm) {
    setEditingId(farm.id)
    setForm({
      farmer: String(farm.farmer),
      farm_name: farm.farm_name,
      location: farm.location,
      approximate_size_acres: farm.approximate_size_acres,
    })
    setFieldErrors({})
    setError('')
    setNotice('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setNotice('')
    setFieldErrors({})

    const size = Number(form.approximate_size_acres)
    if (!form.farmer || !farmers.some((farmer) => farmer.id === Number(form.farmer))) {
      setFieldErrors({ farmer: 'Select a registered farmer.' })
      return
    }
    if (!Number.isFinite(size) || size <= 0) {
      setFieldErrors({ approximate_size_acres: 'Enter a farm size greater than zero.' })
      return
    }

    const payload: FarmInput = {
      farmer: Number(form.farmer),
      farm_name: form.farm_name.trim(),
      location: form.location.trim(),
      approximate_size_acres: form.approximate_size_acres,
    }

    setSaving(true)
    try {
      if (editingId === null) {
        await farmApi.create(payload)
        setNotice('Farm registered successfully.')
      } else {
        await farmApi.update(editingId, payload)
        setNotice('Farm details updated successfully.')
      }
      setForm(emptyFarm)
      setEditingId(null)
      setFarms(await farmApi.list())
    } catch (requestError) {
      if (requestError instanceof ApiRequestError) {
        setError(requestError.message)
        setFieldErrors(requestError.fieldErrors)
      } else {
        setError('Could not save the farm record. Check your connection and try again.')
      }
    } finally {
      setSaving(false)
    }
  }

  async function deleteFarm(farm: Farm) {
    if (!window.confirm(`Delete the farm record for ${farm.farm_name}?`)) return
    setDeletingId(farm.id)
    setError('')
    setNotice('')
    try {
      await farmApi.remove(farm.id)
      setFarms((current) => current.filter((record) => record.id !== farm.id))
      setNotice('Farm record deleted.')
      if (editingId === farm.id) resetForm()
    } catch (requestError) {
      setError(requestError instanceof ApiRequestError
        ? requestError.message
        : 'Could not delete the farm record. Try again.')
    } finally {
      setDeletingId(null)
    }
  }

  const farmerNames = new Map(farmers.map((farmer) => [farmer.id, farmer.full_name]))

  return (
    <section className="management-page" aria-labelledby="farms-title">
      <div className="management-heading">
        <p className="eyebrow"><span /> Farm records</p>
        <h1 id="farms-title">Farm management</h1>
        <p>Register farms, record approximate land size, and link each farm to its registered farmer.</p>
      </div>

      <div className="management-layout">
        <form className="management-form" onSubmit={submitForm}>
          <div className="form-heading">
            <span className="form-index">{editingId === null ? '01' : 'EDIT'}</span>
            <h2>{editingId === null ? 'Register a farm' : 'Update farm details'}</h2>
          </div>

          {error && <p className="form-alert error-alert" role="alert">{error}</p>}
          {notice && <p className="form-alert success-alert" role="status">{notice}</p>}
          {!loading && farmers.length === 0 && (
            <p className="form-alert error-alert" role="status">Register a farmer before adding a farm.</p>
          )}

          <div className="form-grid">
            <label className="form-field field-wide">
              <span>Registered farmer <b aria-hidden="true">*</b></span>
              <select name="farmer" value={form.farmer} onChange={updateField} required disabled={loading || farmers.length === 0} aria-invalid={Boolean(fieldErrors.farmer)}>
                <option value="">Select a farmer</option>
                {farmers.map((farmer) => <option value={farmer.id} key={farmer.id}>{farmer.full_name} · {farmer.county}</option>)}
              </select>
              {fieldErrors.farmer && <small>{fieldErrors.farmer}</small>}
            </label>
            <label className="form-field field-wide">
              <span>Farm name <b aria-hidden="true">*</b></span>
              <input name="farm_name" value={form.farm_name} onChange={updateField} required maxLength={150} aria-invalid={Boolean(fieldErrors.farm_name)} />
              {fieldErrors.farm_name && <small>{fieldErrors.farm_name}</small>}
            </label>
            <label className="form-field field-wide">
              <span>Location <b aria-hidden="true">*</b></span>
              <input name="location" value={form.location} onChange={updateField} required maxLength={255} placeholder="Village, ward, or nearby landmark" aria-invalid={Boolean(fieldErrors.location)} />
              {fieldErrors.location && <small>{fieldErrors.location}</small>}
            </label>
            <label className="form-field field-wide">
              <span>Approximate size (acres) <b aria-hidden="true">*</b></span>
              <input name="approximate_size_acres" type="number" value={form.approximate_size_acres} onChange={updateField} required min="0.01" step="0.01" inputMode="decimal" aria-invalid={Boolean(fieldErrors.approximate_size_acres)} />
              {fieldErrors.approximate_size_acres && <small>{fieldErrors.approximate_size_acres}</small>}
            </label>
          </div>

          <div className="form-actions">
            <button className="button-primary" type="submit" disabled={saving || loading || farmers.length === 0}>
              {saving ? 'Saving…' : editingId === null ? 'Register farm' : 'Save changes'}
              <span aria-hidden="true">→</span>
            </button>
            {editingId !== null && <button className="button-secondary" type="button" onClick={resetForm}>Cancel</button>}
          </div>
        </form>

        <section className="records-panel" aria-labelledby="farm-list-title">
          <div className="records-heading">
            <div>
              <p className="eyebrow"><span /> Directory</p>
              <h2 id="farm-list-title">Registered farms</h2>
            </div>
            <span className="record-count">{loading ? '…' : farms.length}</span>
          </div>

          {loading ? (
            <p className="empty-state" role="status">Loading farm records…</p>
          ) : farms.length === 0 ? (
            <p className="empty-state">No farms registered yet. Add the first record using the form.</p>
          ) : (
            <div className="record-list">
              {farms.map((farm) => (
                <article className="record-row" key={farm.id}>
                  <div className="record-main">
                    <div className="record-avatar" aria-hidden="true">{farm.farm_name.trim().charAt(0).toUpperCase()}</div>
                    <div>
                      <h3>{farm.farm_name}</h3>
                      <p>{farmerNames.get(farm.farmer) ?? 'Farmer record unavailable'}</p>
                      <p>{farm.location} · {farm.approximate_size_acres} acres</p>
                    </div>
                  </div>
                  <div className="record-meta">
                    <span>Added {formatDate(farm.date_created)}</span>
                    <div className="record-actions">
                      <button type="button" onClick={() => startEditing(farm)}>Edit</button>
                      <button type="button" className="delete-action" disabled={deletingId === farm.id} onClick={() => void deleteFarm(farm)}>
                        {deletingId === farm.id ? 'Deleting…' : 'Delete'}
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
          {!loading && error && farms.length === 0 && (
            <button className="button-secondary retry-button" type="button" onClick={() => void loadRecords()}>Retry loading</button>
          )}
        </section>
      </div>
    </section>
  )
}