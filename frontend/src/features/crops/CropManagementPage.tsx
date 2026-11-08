import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { ApiRequestError, apiErrorMessage, cropApi, farmApi } from '../../api/client'
import type {
  ApiFieldErrors,
  Crop,
  CropGrowthStage,
  CropInput,
  Farm,
  HarvestQuantityUnit,
} from '../../types/records'
import { cropGrowthStages } from '../../types/records'
import '../management.css'

type CropFormState = Omit<CropInput, 'farm' | 'expected_harvest_quantity'> & {
  farm: string
  expected_harvest_quantity: string
}

const emptyCrop: CropFormState = {
  crop_name: '',
  variety: '',
  farm: '',
  planting_date: '',
  expected_harvest_date: '',
  cultivated_area_acres: '',
  growth_stage: 'planned',
  expected_harvest_quantity: '',
  harvest_quantity_unit: '',
}

const stageLabels: Record<CropGrowthStage, string> = {
  planned: 'Planned',
  planted: 'Planted',
  germinating: 'Germinating',
  vegetative: 'Vegetative',
  flowering: 'Flowering',
  fruiting: 'Fruiting',
  maturing: 'Maturing',
  harvested: 'Harvested',
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))
}

export function CropManagementPage() {
  const [crops, setCrops] = useState<Crop[]>([])
  const [farms, setFarms] = useState<Farm[]>([])
  const [form, setForm] = useState<CropFormState>(emptyCrop)
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
      const [cropRecords, farmRecords] = await Promise.all([
        cropApi.list(),
        farmApi.list(),
      ])
      setCrops(cropRecords)
      setFarms(farmRecords)
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Could not load crops and farm choices.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    Promise.all([cropApi.list(), farmApi.list()])
      .then(([cropRecords, farmRecords]) => {
        if (!cancelled) {
          setCrops(cropRecords)
          setFarms(farmRecords)
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) setError(apiErrorMessage(requestError, 'Could not load crops and farm choices.'))
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
    setForm(emptyCrop)
    setFieldErrors({})
    setError('')
    setNotice('')
  }

  function startEditing(crop: Crop) {
    setEditingId(crop.id)
    setForm({
      crop_name: crop.crop_name,
      variety: crop.variety,
      farm: String(crop.farm),
      planting_date: crop.planting_date,
      expected_harvest_date: crop.expected_harvest_date,
      cultivated_area_acres: crop.cultivated_area_acres,
      growth_stage: crop.growth_stage,
      expected_harvest_quantity: crop.expected_harvest_quantity ?? '',
      harvest_quantity_unit: crop.harvest_quantity_unit,
    })
    setFieldErrors({})
    setError('')
    setNotice('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function validateForm() {
    const nextErrors: ApiFieldErrors = {}
    const selectedFarm = farms.find((farm) => farm.id === Number(form.farm))
    const area = Number(form.cultivated_area_acres)
    const hasQuantity = form.expected_harvest_quantity.trim() !== ''
    const quantity = hasQuantity ? Number(form.expected_harvest_quantity) : null

    if (!selectedFarm) {
      nextErrors.farm = 'Select an existing farm.'
    }
    if (!Number.isFinite(area) || area <= 0) {
      nextErrors.cultivated_area_acres = 'Cultivated area must be greater than zero.'
    } else if (selectedFarm) {
      const otherAllocatedArea = crops
        .filter((crop) => crop.farm === selectedFarm.id && crop.id !== editingId)
        .reduce((total, crop) => total + Number(crop.cultivated_area_acres), 0)
      if (otherAllocatedArea + area > Number(selectedFarm.approximate_size_acres)) {
        nextErrors.cultivated_area_acres = `Only ${(Number(selectedFarm.approximate_size_acres) - otherAllocatedArea).toFixed(2)} acres remain unallocated on this farm.`
      }
    }
    if (form.planting_date && form.expected_harvest_date < form.planting_date) {
      nextErrors.expected_harvest_date = 'Expected harvest date cannot be before planting date.'
    }
    if (quantity !== null && (!Number.isFinite(quantity) || quantity < 0)) {
      nextErrors.expected_harvest_quantity = 'Expected harvest quantity cannot be negative.'
    }
    if (hasQuantity && !form.harvest_quantity_unit) {
      nextErrors.harvest_quantity_unit = 'Select a unit for the expected harvest quantity.'
    }
    if (!hasQuantity && form.harvest_quantity_unit) {
      nextErrors.harvest_quantity_unit = 'Clear the unit or provide an expected harvest quantity.'
    }

    return nextErrors
  }

  async function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setNotice('')
    const nextErrors = validateForm()
    setFieldErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) return

    const payload: CropInput = {
      crop_name: form.crop_name.trim(),
      variety: form.variety.trim(),
      farm: Number(form.farm),
      planting_date: form.planting_date,
      expected_harvest_date: form.expected_harvest_date,
      cultivated_area_acres: form.cultivated_area_acres,
      growth_stage: form.growth_stage,
      expected_harvest_quantity: form.expected_harvest_quantity.trim()
        ? form.expected_harvest_quantity
        : null,
      harvest_quantity_unit: form.expected_harvest_quantity.trim()
        ? form.harvest_quantity_unit as HarvestQuantityUnit
        : '',
    }

    setSaving(true)
    try {
      if (editingId === null) {
        await cropApi.create(payload)
        setNotice('Crop record registered successfully.')
      } else {
        await cropApi.update(editingId, payload)
        setNotice('Crop record updated successfully.')
      }
      setForm(emptyCrop)
      setEditingId(null)
      setCrops(await cropApi.list())
    } catch (requestError) {
      if (requestError instanceof ApiRequestError) {
        setError(requestError.message)
        setFieldErrors(requestError.fieldErrors)
      } else {
        setError(apiErrorMessage(requestError, 'Could not save the crop record.'))
      }
    } finally {
      setSaving(false)
    }
  }

  async function deleteCrop(crop: Crop) {
    if (!window.confirm(`Delete the ${crop.crop_name} crop record?`)) return
    setDeletingId(crop.id)
    setError('')
    setNotice('')
    try {
      await cropApi.remove(crop.id)
      setCrops((current) => current.filter((record) => record.id !== crop.id))
      setNotice('Crop record deleted.')
      if (editingId === crop.id) resetForm()
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Could not delete the crop record.'))
    } finally {
      setDeletingId(null)
    }
  }

  const selectedFarm = farms.find((farm) => farm.id === Number(form.farm))

  return (
    <section className="management-page" aria-labelledby="crops-title">
      <div className="management-heading">
        <p className="eyebrow"><span /> Crop records</p>
        <h1 id="crops-title">Crop management</h1>
        <p>Track crop plans by farm, planting dates, allocated area, and expected harvest.</p>
      </div>

      <div className="management-layout">
        <form className="management-form" onSubmit={submitForm}>
          <div className="form-heading">
            <span className="form-index">{editingId === null ? '01' : 'EDIT'}</span>
            <h2>{editingId === null ? 'Register a crop' : 'Update crop details'}</h2>
          </div>

          {error && <p className="form-alert error-alert" role="alert">{error}</p>}
          {notice && <p className="form-alert success-alert" role="status">{notice}</p>}
          <p className="form-alert info-alert">Growth stage is farmer-recorded and is not automatically verified.</p>
          {!loading && farms.length === 0 && (
            <p className="form-alert error-alert" role="status">Register a farm before adding a crop.</p>
          )}

          <div className="form-grid">
            <label className="form-field field-wide">
              <span>Crop name <b aria-hidden="true">*</b></span>
              <input name="crop_name" value={form.crop_name} onChange={updateField} required maxLength={120} aria-invalid={Boolean(fieldErrors.crop_name)} />
              {fieldErrors.crop_name && <small>{fieldErrors.crop_name}</small>}
            </label>
            <label className="form-field field-wide">
              <span>Variety <i>Optional</i></span>
              <input name="variety" value={form.variety} onChange={updateField} maxLength={120} />
              {fieldErrors.variety && <small>{fieldErrors.variety}</small>}
            </label>
            <label className="form-field field-wide">
              <span>Farm <b aria-hidden="true">*</b></span>
              <select name="farm" value={form.farm} onChange={updateField} required disabled={loading || farms.length === 0} aria-invalid={Boolean(fieldErrors.farm)}>
                <option value="">Select a registered farm</option>
                {farms.map((farm) => <option value={farm.id} key={farm.id}>{farm.farm_name} · {farm.location} · {farm.approximate_size_acres} acres</option>)}
              </select>
              {fieldErrors.farm && <small>{fieldErrors.farm}</small>}
            </label>
            {selectedFarm && (
              <p className="crop-capacity field-wide" role="status">
                Farm capacity: {selectedFarm.approximate_size_acres} acres
                {editingId === null && ` · ${crops.filter((crop) => crop.farm === selectedFarm.id).reduce((total, crop) => total + Number(crop.cultivated_area_acres), 0).toFixed(2)} acres already allocated`}
              </p>
            )}
            <label className="form-field">
              <span>Planting date <b aria-hidden="true">*</b></span>
              <input name="planting_date" type="date" value={form.planting_date} onChange={updateField} required aria-invalid={Boolean(fieldErrors.planting_date)} />
              {fieldErrors.planting_date && <small>{fieldErrors.planting_date}</small>}
            </label>
            <label className="form-field">
              <span>Expected harvest <b aria-hidden="true">*</b></span>
              <input name="expected_harvest_date" type="date" min={form.planting_date || undefined} value={form.expected_harvest_date} onChange={updateField} required aria-invalid={Boolean(fieldErrors.expected_harvest_date)} />
              {fieldErrors.expected_harvest_date && <small>{fieldErrors.expected_harvest_date}</small>}
            </label>
            <label className="form-field">
              <span>Cultivated area (acres) <b aria-hidden="true">*</b></span>
              <input name="cultivated_area_acres" type="number" min="0.01" step="0.01" inputMode="decimal" value={form.cultivated_area_acres} onChange={updateField} required aria-invalid={Boolean(fieldErrors.cultivated_area_acres)} />
              {fieldErrors.cultivated_area_acres && <small>{fieldErrors.cultivated_area_acres}</small>}
            </label>
            <label className="form-field">
              <span>Growth stage <b aria-hidden="true">*</b></span>
              <select name="growth_stage" value={form.growth_stage} onChange={updateField} required aria-invalid={Boolean(fieldErrors.growth_stage)}>
                {cropGrowthStages.map((stage) => <option value={stage} key={stage}>{stageLabels[stage]}</option>)}
              </select>
              {fieldErrors.growth_stage && <small>{fieldErrors.growth_stage}</small>}
            </label>
            <label className="form-field">
              <span>Expected harvest quantity <i>Optional</i></span>
              <input name="expected_harvest_quantity" type="number" min="0" step="0.01" inputMode="decimal" value={form.expected_harvest_quantity} onChange={updateField} aria-invalid={Boolean(fieldErrors.expected_harvest_quantity)} />
              {fieldErrors.expected_harvest_quantity && <small>{fieldErrors.expected_harvest_quantity}</small>}
            </label>
            <label className="form-field">
              <span>Quantity unit {form.expected_harvest_quantity && <b aria-hidden="true">*</b>}</span>
              <select name="harvest_quantity_unit" value={form.harvest_quantity_unit} onChange={updateField} aria-required={Boolean(form.expected_harvest_quantity)} aria-invalid={Boolean(fieldErrors.harvest_quantity_unit)}>
                <option value="">No quantity</option>
                <option value="kg">Kilograms</option>
                <option value="tonne">Tonnes</option>
              </select>
              {fieldErrors.harvest_quantity_unit && <small>{fieldErrors.harvest_quantity_unit}</small>}
            </label>
          </div>

          <div className="form-actions">
            <button className="button-primary" type="submit" disabled={saving || loading || farms.length === 0}>
              {saving ? 'Saving…' : editingId === null ? 'Register crop' : 'Save changes'}
              <span aria-hidden="true">→</span>
            </button>
            {editingId !== null && <button className="button-secondary" type="button" onClick={resetForm}>Cancel</button>}
          </div>
        </form>

        <section className="records-panel" aria-labelledby="crop-list-title">
          <div className="records-heading">
            <div>
              <p className="eyebrow"><span /> Directory</p>
              <h2 id="crop-list-title">Registered crops</h2>
            </div>
            <span className="record-count">{loading ? '…' : crops.length}</span>
          </div>

          {loading ? (
            <p className="empty-state" role="status">Loading crop records…</p>
          ) : crops.length === 0 ? (
            <p className="empty-state">No crops registered yet. Add the first crop using the form.</p>
          ) : (
            <div className="record-list">
              {crops.map((crop) => (
                <article className="record-row crop-record" key={crop.id}>
                  <div className="record-main">
                    <div className="record-avatar" aria-hidden="true">{crop.crop_name.trim().charAt(0).toUpperCase()}</div>
                    <div>
                      <h3>{crop.crop_name}{crop.variety && ` · ${crop.variety}`}</h3>
                      <p>{crop.farm_name} · {crop.cultivated_area_acres} acres</p>
                      <p>{formatDate(crop.planting_date)} to {formatDate(crop.expected_harvest_date)}</p>
                      <p>Stage: {stageLabels[crop.growth_stage]} · farmer-recorded</p>
                      {crop.expected_harvest_quantity !== null && (
                        <p>Expected: {crop.expected_harvest_quantity} {crop.harvest_quantity_unit === 'kg' ? 'kg' : 'tonnes'}</p>
                      )}
                    </div>
                  </div>
                  <div className="record-meta">
                    <span>Updated {formatDate(crop.updated_at.slice(0, 10))}</span>
                    <div className="record-actions">
                      <button type="button" onClick={() => startEditing(crop)}>Edit</button>
                      <button type="button" className="delete-action" disabled={deletingId === crop.id} onClick={() => void deleteCrop(crop)}>
                        {deletingId === crop.id ? 'Deleting…' : 'Delete'}
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
          {!loading && error && crops.length === 0 && (
            <button className="button-secondary retry-button" type="button" onClick={() => void loadRecords()}>Retry loading</button>
          )}
        </section>
      </div>
    </section>
  )
}