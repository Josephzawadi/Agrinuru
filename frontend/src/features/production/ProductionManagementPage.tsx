import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import {
  ApiRequestError,
  apiErrorMessage,
  cropApi,
  farmerApi,
  farmApi,
  harvestRecordApi,
  inputUsageApi,
  productionActivityApi,
  productionExpenseApi,
  productionSummaryApi,
} from '../../api/client'
import type {
  ApiFieldErrors,
  Crop,
  ExpenseCategory,
  HarvestRecord,
  HarvestQuantityUnit,
  InputUsage,
  ProductionActivity,
  ProductionActivityType,
  ProductionExpense,
  ProductionFilters,
  ProductionSummary,
  FarmerProfile,
  Farm,
} from '../../types/records'
import '../management.css'

type Section = 'activities' | 'inputs' | 'expenses' | 'harvests' | 'summary'
type FormValues = Record<string, string>
type ProductionRecord = ProductionActivity | InputUsage | ProductionExpense | HarvestRecord

const sections: Array<{ id: Section; label: string }> = [
  { id: 'activities', label: 'Activities' },
  { id: 'inputs', label: 'Inputs' },
  { id: 'expenses', label: 'Expenses' },
  { id: 'harvests', label: 'Harvests' },
  { id: 'summary', label: 'Summary' },
]

const activityTypes: Array<{ value: ProductionActivityType; label: string }> = [
  { value: 'planting', label: 'Planting' },
  { value: 'weeding', label: 'Weeding' },
  { value: 'irrigation', label: 'Irrigation' },
  { value: 'fertilizer_application', label: 'Fertilizer application' },
  { value: 'pest_control', label: 'Pest control' },
  { value: 'pruning', label: 'Pruning' },
  { value: 'soil_preparation', label: 'Soil preparation' },
  { value: 'scouting', label: 'Crop scouting' },
  { value: 'other', label: 'Other' },
]

const inputTypes = [
  ['seed', 'Seed'], ['fertilizer', 'Fertilizer'], ['pesticide', 'Pesticide'],
  ['herbicide', 'Herbicide'], ['other', 'Other'],
] as const
const inputUnits = [
  ['g', 'Grams'], ['kg', 'Kilograms'], ['tonne', 'Tonnes'], ['ml', 'Millilitres'],
  ['l', 'Litres'], ['piece', 'Pieces'], ['packet', 'Packets'], ['bag', 'Bags'],
] as const
const expenseCategories: Array<{ value: ExpenseCategory; label: string }> = [
  { value: 'labour', label: 'Labour' },
  { value: 'land_preparation', label: 'Land preparation' },
  { value: 'irrigation', label: 'Irrigation' },
  { value: 'machinery', label: 'Machinery' },
  { value: 'transport', label: 'Transport' },
  { value: 'storage', label: 'Storage' },
  { value: 'other', label: 'Other' },
]

function blankForm(section: Section): FormValues {
  if (section === 'activities') return { crop: '', activity_type: 'weeding', activity_date: '', description: '', notes: '' }
  if (section === 'inputs') return { crop: '', input_type: 'seed', product_name: '', usage_date: '', quantity: '', quantity_unit: 'kg', purchase_cost: '', currency_code: 'KES', notes: '' }
  if (section === 'expenses') return { crop: '', category: 'labour', description: '', expense_date: '', amount: '', currency_code: 'KES', notes: '' }
  return { crop: '', harvest_date: '', quantity: '0', quantity_unit: 'kg', notes: '' }
}

function today() {
  return new Date().toISOString().slice(0, 10)
}

function displayDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))
}

function displayStage(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function comparisonLabel(status: ProductionSummary['crops'][number]['comparison']['status']) {
  const labels = {
    comparable: 'Compared in kilograms',
    period_limited: 'Selected period only',
    no_harvest_recorded: 'No harvest recorded',
    expected_not_recorded_or_unit_incompatible: 'Expected quantity missing or units incompatible',
  }
  return labels[status]
}

function asInputValue(record: ProductionRecord, section: Section): FormValues {
  if (section === 'activities') {
    const activity = record as ProductionActivity
    return {
      crop: String(activity.crop),
      activity_type: activity.activity_type,
      activity_date: activity.activity_date,
      description: activity.description,
      notes: activity.notes,
    }
  }
  if (section === 'inputs') {
    const input = record as InputUsage
    return {
      crop: String(input.crop),
      input_type: input.input_type,
      product_name: input.product_name,
      usage_date: input.usage_date,
      quantity: input.quantity,
      quantity_unit: input.quantity_unit,
      purchase_cost: input.purchase_cost ?? '',
      currency_code: input.currency_code,
      notes: input.notes,
    }
  }
  if (section === 'expenses') {
    const expense = record as ProductionExpense
    return {
      crop: String(expense.crop),
      category: expense.category,
      description: expense.description,
      expense_date: expense.expense_date,
      amount: expense.amount,
      currency_code: expense.currency_code,
      notes: expense.notes,
    }
  }
  const harvest = record as HarvestRecord
  return {
    crop: String(harvest.crop),
    harvest_date: harvest.harvest_date,
    quantity: harvest.quantity,
    quantity_unit: harvest.quantity_unit,
    notes: harvest.notes,
  }
}

export function ProductionManagementPage() {
  const [section, setSection] = useState<Section>('activities')
  const [crops, setCrops] = useState<Crop[]>([])
  const [farms, setFarms] = useState<Farm[]>([])
  const [farmers, setFarmers] = useState<FarmerProfile[]>([])
  const [filters, setFilters] = useState({ crop: '', farm: '', farmer: '', date_from: '', date_to: '', include_voided: false })
  const [records, setRecords] = useState<ProductionRecord[]>([])
  const [summary, setSummary] = useState<ProductionSummary | null>(null)
  const [form, setForm] = useState<FormValues>(() => blankForm('activities'))
  const [editingId, setEditingId] = useState<number | null>(null)
  const [loadingReferences, setLoadingReferences] = useState(true)
  const [loadingRecords, setLoadingRecords] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<ApiFieldErrors>({})
  const [notice, setNotice] = useState('')
  const [refreshToken, setRefreshToken] = useState(0)

  useEffect(() => {
    let cancelled = false
    Promise.all([cropApi.list(), farmApi.list(), farmerApi.list()])
      .then(([cropRecords, farmRecords, farmerRecords]) => {
        if (!cancelled) {
          setCrops(cropRecords)
          setFarms(farmRecords)
          setFarmers(farmerRecords)
        }
      })
      .catch((requestError: unknown) => {
        if (!cancelled) setError(apiErrorMessage(requestError, 'Could not load crop and farm records.'))
      })
      .finally(() => {
        if (!cancelled) setLoadingReferences(false)
      })

    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    const queryFilters: ProductionFilters = {
      ...(filters.crop ? { crop: Number(filters.crop) } : {}),
      ...(filters.farm ? { farm: Number(filters.farm) } : {}),
      ...(filters.farmer ? { farmer: Number(filters.farmer) } : {}),
      ...(filters.date_from ? { date_from: filters.date_from } : {}),
      ...(filters.date_to ? { date_to: filters.date_to } : {}),
      include_voided: filters.include_voided,
    }

    const request = section === 'summary'
      ? productionSummaryApi.get({
          crop: queryFilters.crop,
          farm: queryFilters.farm,
          farmer: queryFilters.farmer,
          date_from: queryFilters.date_from,
          date_to: queryFilters.date_to,
        })
      : section === 'activities'
        ? productionActivityApi.list(queryFilters)
        : section === 'inputs'
          ? inputUsageApi.list(queryFilters)
          : section === 'expenses'
            ? productionExpenseApi.list(queryFilters)
            : harvestRecordApi.list(queryFilters)

    request
      .then((data) => {
        if (cancelled) return
        setError('')
        if (section === 'summary') {
          setSummary(data as ProductionSummary)
        } else {
          setRecords(data as ProductionRecord[])
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(apiErrorMessage(requestError, 'Could not load production records.'))
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingRecords(false)
      })

    return () => { cancelled = true }
  }, [section, filters, refreshToken])

  function changeSection(nextSection: Section) {
    if (nextSection === section) return
    setSection(nextSection)
    setForm(blankForm(nextSection))
    setEditingId(null)
    setFieldErrors({})
    setError('')
    setNotice('')
    setLoadingRecords(true)
  }

  function updateFilter(event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    const { name, value, type } = event.currentTarget
    setLoadingRecords(true)
    setFilters((current) => ({
      ...current,
      [name]: type === 'checkbox' ? (event.currentTarget as HTMLInputElement).checked : value,
    }))
  }

  function updateForm(event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) {
    const { name, value } = event.currentTarget
    setForm((current) => ({ ...current, [name]: value }))
    setFieldErrors((current) => ({ ...current, [name]: '' }))
  }

  function clearForm() {
    setForm(blankForm(section))
    setEditingId(null)
    setFieldErrors({})
    setError('')
    setNotice('')
  }

  function editRecord(record: ProductionRecord) {
    setForm(asInputValue(record, section))
    setEditingId(record.id)
    setFieldErrors({})
    setError('')
    setNotice('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function validateForm() {
    const errors: ApiFieldErrors = {}
    const selectedCrop = crops.find((crop) => crop.id === Number(form.crop))
    if (!selectedCrop) errors.crop = 'Select an existing crop.'

    const dateField = section === 'activities' ? 'activity_date'
      : section === 'inputs' ? 'usage_date'
        : section === 'expenses' ? 'expense_date' : 'harvest_date'
    if (form[dateField] && form[dateField] > today()) {
      errors[dateField] = 'Completed production records cannot be future-dated.'
    }
    if (section === 'harvests' && selectedCrop && form.harvest_date < selectedCrop.planting_date) {
      errors.harvest_date = 'Harvest date cannot precede the crop planting date.'
    }
    if (section === 'inputs') {
      const quantity = Number(form.quantity)
      if (!Number.isFinite(quantity) || quantity <= 0) errors.quantity = 'Input quantity must be greater than zero.'
      if (form.purchase_cost && (!Number.isFinite(Number(form.purchase_cost)) || Number(form.purchase_cost) < 0)) {
        errors.purchase_cost = 'Purchase cost cannot be negative.'
      }
    }
    if (section === 'expenses' && (!Number.isFinite(Number(form.amount)) || Number(form.amount) < 0)) {
      errors.amount = 'Expense amount cannot be negative.'
    }
    if (section === 'harvests' && (!Number.isFinite(Number(form.quantity)) || Number(form.quantity) < 0)) {
      errors.quantity = 'Harvest quantity cannot be negative.'
    }
    if ((section === 'inputs' && form.purchase_cost) || section === 'expenses') {
      const currency = form.currency_code.trim()
      if (!/^[A-Z]{3}$/.test(currency)) errors.currency_code = 'Use a three-letter uppercase currency code, such as KES.'
    }
    return errors
  }

  async function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setNotice('')
    const errors = validateForm()
    setFieldErrors(errors)
    if (Object.keys(errors).length > 0) return

    const base = { crop: Number(form.crop), notes: form.notes.trim() }
    let operation: Promise<unknown>
    let successMessage: string
    if (section === 'activities') {
      const data = {
        ...base,
        activity_type: form.activity_type as ProductionActivityType,
        activity_date: form.activity_date,
        description: form.description.trim(),
      }
      operation = editingId === null ? productionActivityApi.create(data) : productionActivityApi.update(editingId, data)
      successMessage = editingId === null ? 'Activity recorded.' : 'Activity updated.'
    } else if (section === 'inputs') {
      const data = {
        ...base,
        input_type: form.input_type as InputUsage['input_type'],
        product_name: form.product_name.trim(),
        usage_date: form.usage_date,
        quantity: form.quantity,
        quantity_unit: form.quantity_unit as InputUsage['quantity_unit'],
        purchase_cost: form.purchase_cost.trim() ? form.purchase_cost : null,
        currency_code: form.currency_code.trim() || 'KES',
      }
      operation = editingId === null ? inputUsageApi.create(data) : inputUsageApi.update(editingId, data)
      successMessage = editingId === null ? 'Input usage recorded.' : 'Input usage updated.'
    } else if (section === 'expenses') {
      const data = {
        ...base,
        category: form.category as ExpenseCategory,
        description: form.description.trim(),
        expense_date: form.expense_date,
        amount: form.amount,
        currency_code: form.currency_code.trim() || 'KES',
      }
      operation = editingId === null ? productionExpenseApi.create(data) : productionExpenseApi.update(editingId, data)
      successMessage = editingId === null ? 'Expense recorded.' : 'Expense updated.'
    } else {
      const data = {
        ...base,
        harvest_date: form.harvest_date,
        quantity: form.quantity,
        quantity_unit: form.quantity_unit as HarvestQuantityUnit,
      }
      operation = editingId === null ? harvestRecordApi.create(data) : harvestRecordApi.update(editingId, data)
      successMessage = editingId === null ? 'Harvest recorded.' : 'Harvest updated.'
    }

    setSaving(true)
    try {
      await operation
      setNotice(successMessage)
      setForm(blankForm(section))
      setEditingId(null)
      setLoadingRecords(true)
      setRefreshToken((current) => current + 1)
    } catch (requestError) {
      if (requestError instanceof ApiRequestError) {
        setError(requestError.message)
        setFieldErrors(requestError.fieldErrors)
      } else {
        setError(apiErrorMessage(requestError, 'Could not save this production record.'))
      }
    } finally {
      setSaving(false)
    }
  }

  async function voidRecord(record: ProductionRecord) {
    const reason = window.prompt('Why is this record being voided? The original record will be retained.')
    if (reason === null) return
    if (!reason.trim()) {
      setError('A reason is required to void a record.')
      return
    }
    setError('')
    setNotice('')
    setSaving(true)
    try {
      if (section === 'activities') await productionActivityApi.void(record.id, reason)
      else if (section === 'inputs') await inputUsageApi.void(record.id, reason)
      else if (section === 'expenses') await productionExpenseApi.void(record.id, reason)
      else if (section === 'harvests') await harvestRecordApi.void(record.id, reason)
      setNotice('Record voided. Its history is retained and excluded from active summaries.')
      setLoadingRecords(true)
      setRefreshToken((current) => current + 1)
    } catch (requestError) {
      setError(apiErrorMessage(requestError, 'Could not void this record.'))
    } finally {
      setSaving(false)
    }
  }

  function renderForm() {
    const cropField = (
      <label className="form-field field-wide">
        <span>Crop <b aria-hidden="true">*</b></span>
        <select name="crop" value={form.crop ?? ''} onChange={updateForm} required disabled={loadingReferences || crops.length === 0} aria-invalid={Boolean(fieldErrors.crop)}>
          <option value="">Select a crop</option>
          {crops.map((crop) => {
            const farm = farms.find((item) => item.id === crop.farm)
            return <option value={crop.id} key={crop.id}>{crop.crop_name}{crop.variety ? ` · ${crop.variety}` : ''} · {farm?.farm_name ?? crop.farm_name}</option>
          })}
        </select>
        {fieldErrors.crop && <small>{fieldErrors.crop}</small>}
      </label>
    )
    const notesField = (
      <label className="form-field field-wide">
        <span>Notes <i>Optional</i></span>
        <textarea name="notes" value={form.notes ?? ''} onChange={updateForm} rows={3} />
      </label>
    )
    const dateInput = (name: string, label: string, required = true) => (
      <label className="form-field">
        <span>{label} {required && <b aria-hidden="true">*</b>}</span>
        <input name={name} type="date" value={form[name] ?? ''} onChange={updateForm} required={required} max={today()} aria-invalid={Boolean(fieldErrors[name])} />
        {fieldErrors[name] && <small>{fieldErrors[name]}</small>}
      </label>
    )
    const currencyField = (
      <label className="form-field">
        <span>Currency code <b aria-hidden="true">*</b></span>
        <input name="currency_code" value={form.currency_code ?? 'KES'} onChange={updateForm} required maxLength={3} pattern="[A-Z]{3}" aria-invalid={Boolean(fieldErrors.currency_code)} />
        {fieldErrors.currency_code && <small>{fieldErrors.currency_code}</small>}
      </label>
    )

    if (section === 'activities') return <>
      {cropField}
      <label className="form-field">
        <span>Activity <b aria-hidden="true">*</b></span>
        <select name="activity_type" value={form.activity_type} onChange={updateForm} required>
          {activityTypes.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
        </select>
      </label>
      {dateInput('activity_date', 'Completed on')}
      <label className="form-field field-wide">
        <span>Description <i>Optional</i></span>
        <input name="description" value={form.description ?? ''} onChange={updateForm} maxLength={200} />
        {fieldErrors.description && <small>{fieldErrors.description}</small>}
      </label>
      {notesField}
    </>
    if (section === 'inputs') return <>
      {cropField}
      <label className="form-field">
        <span>Input type <b aria-hidden="true">*</b></span>
        <select name="input_type" value={form.input_type} onChange={updateForm} required>
          {inputTypes.map(([value, label]) => <option value={value} key={value}>{label}</option>)}
        </select>
      </label>
      <label className="form-field">
        <span>Product name <b aria-hidden="true">*</b></span>
        <input name="product_name" value={form.product_name ?? ''} onChange={updateForm} required maxLength={150} />
        {fieldErrors.product_name && <small>{fieldErrors.product_name}</small>}
      </label>
      {dateInput('usage_date', 'Used on')}
      <label className="form-field">
        <span>Quantity <b aria-hidden="true">*</b></span>
        <input name="quantity" type="number" min="0.001" step="0.001" value={form.quantity ?? ''} onChange={updateForm} required aria-invalid={Boolean(fieldErrors.quantity)} />
        {fieldErrors.quantity && <small>{fieldErrors.quantity}</small>}
      </label>
      <label className="form-field">
        <span>Unit <b aria-hidden="true">*</b></span>
        <select name="quantity_unit" value={form.quantity_unit} onChange={updateForm} required>
          {inputUnits.map(([value, label]) => <option value={value} key={value}>{label}</option>)}
        </select>
      </label>
      <label className="form-field">
        <span>Purchase cost <i>Optional</i></span>
        <input name="purchase_cost" type="number" min="0" step="0.01" value={form.purchase_cost ?? ''} onChange={updateForm} aria-invalid={Boolean(fieldErrors.purchase_cost)} />
        {fieldErrors.purchase_cost && <small>{fieldErrors.purchase_cost}</small>}
      </label>
      {form.purchase_cost && currencyField}
      {notesField}
    </>
    if (section === 'expenses') return <>
      {cropField}
      <label className="form-field">
        <span>Expense category <b aria-hidden="true">*</b></span>
        <select name="category" value={form.category} onChange={updateForm} required>
          {expenseCategories.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
        </select>
      </label>
      <label className="form-field field-wide">
        <span>Description <b aria-hidden="true">*</b></span>
        <input name="description" value={form.description ?? ''} onChange={updateForm} required maxLength={200} />
        {fieldErrors.description && <small>{fieldErrors.description}</small>}
      </label>
      {dateInput('expense_date', 'Incurred on')}
      <label className="form-field">
        <span>Amount <b aria-hidden="true">*</b></span>
        <input name="amount" type="number" min="0" step="0.01" value={form.amount ?? ''} onChange={updateForm} required aria-invalid={Boolean(fieldErrors.amount)} />
        {fieldErrors.amount && <small>{fieldErrors.amount}</small>}
      </label>
      {currencyField}
      {notesField}
    </>
    return <>
      {cropField}
      {dateInput('harvest_date', 'Harvest date')}
      <label className="form-field">
        <span>Actual quantity <b aria-hidden="true">*</b></span>
        <input name="quantity" type="number" min="0" step="0.001" value={form.quantity ?? ''} onChange={updateForm} required aria-invalid={Boolean(fieldErrors.quantity)} />
        {fieldErrors.quantity && <small>{fieldErrors.quantity}</small>}
      </label>
      <label className="form-field">
        <span>Unit <b aria-hidden="true">*</b></span>
        <select name="quantity_unit" value={form.quantity_unit} onChange={updateForm} required>
          <option value="kg">Kilograms</option>
          <option value="tonne">Tonnes</option>
        </select>
      </label>
      {notesField}
    </>
  }

  function recordTitle(record: ProductionRecord) {
    if (section === 'activities') {
      const activity = record as ProductionActivity
      return `${displayStage(activity.activity_type)}${activity.description ? ` · ${activity.description}` : ''}`
    }
    if (section === 'inputs') {
      const input = record as InputUsage
      return `${displayStage(input.input_type)} · ${input.product_name}`
    }
    if (section === 'expenses') {
      const expense = record as ProductionExpense
      return `${displayStage(expense.category)} · ${expense.description}`
    }
    const harvest = record as HarvestRecord
    return `${harvest.quantity} ${harvest.quantity_unit === 'kg' ? 'kg' : 'tonnes'} harvested`
  }

  function recordDate(record: ProductionRecord) {
    if (section === 'activities') return (record as ProductionActivity).activity_date
    if (section === 'inputs') return (record as InputUsage).usage_date
    if (section === 'expenses') return (record as ProductionExpense).expense_date
    return (record as HarvestRecord).harvest_date
  }

  function recordDetail(record: ProductionRecord) {
    if (section === 'inputs') {
      const input = record as InputUsage
      const cost = input.purchase_cost === null ? 'Cost not recorded' : `${input.currency_code} ${input.purchase_cost}`
      return `${input.quantity} ${input.quantity_unit} · ${cost}`
    }
    if (section === 'expenses') {
      const expense = record as ProductionExpense
      return `${expense.currency_code} ${expense.amount}`
    }
    return record.notes || 'No additional notes'
  }

  const heading = sections.find((item) => item.id === section)?.label ?? 'Production'
  const selectedCrop = crops.find((crop) => crop.id === Number(form.crop))

  return (
    <section className="management-page" aria-labelledby="production-title">
      <div className="management-heading">
        <p className="eyebrow"><span /> Crop-linked records</p>
        <h1 id="production-title">Production management</h1>
        <p>Record completed field work, inputs, costs, and actual harvests against registered crops.</p>
      </div>

      <nav className="production-tabs" aria-label="Production sections">
        {sections.map((item) => (
          <button type="button" key={item.id} className={section === item.id ? 'production-tab active' : 'production-tab'} aria-current={section === item.id ? 'page' : undefined} onClick={() => changeSection(item.id)}>{item.label}</button>
        ))}
      </nav>

      <section className="production-filters" aria-label="Production filters">
        <label className="form-field">
          <span>Crop</span>
          <select name="crop" value={filters.crop} onChange={updateFilter}>
            <option value="">All crops</option>
            {crops.map((crop) => <option value={crop.id} key={crop.id}>{crop.crop_name} · {crop.farm_name}</option>)}
          </select>
        </label>
        <label className="form-field">
          <span>Farm</span>
          <select name="farm" value={filters.farm} onChange={updateFilter}>
            <option value="">All farms</option>
            {farms.map((farm) => <option value={farm.id} key={farm.id}>{farm.farm_name}</option>)}
          </select>
        </label>
        <label className="form-field">
          <span>Farmer</span>
          <select name="farmer" value={filters.farmer} onChange={updateFilter}>
            <option value="">All farmers</option>
            {farmers.map((farmer) => <option value={farmer.id} key={farmer.id}>{farmer.full_name}</option>)}
          </select>
        </label>
        <label className="form-field">
          <span>From</span>
          <input name="date_from" type="date" value={filters.date_from} onChange={updateFilter} />
        </label>
        <label className="form-field">
          <span>To</span>
          <input name="date_to" type="date" value={filters.date_to} onChange={updateFilter} />
        </label>
        {section !== 'summary' && (
          <label className="voided-filter">
            <input name="include_voided" type="checkbox" checked={filters.include_voided} onChange={updateFilter} />
            <span>Include voided history</span>
          </label>
        )}
      </section>

      {error && <p className="form-alert error-alert" role="alert">{error}</p>}
      {notice && <p className="form-alert success-alert" role="status">{notice}</p>}

      {section !== 'summary' ? (
        <div className="production-layout">
          <form className="management-form" onSubmit={submitForm}>
            <div className="form-heading">
              <span className="form-index">{editingId === null ? 'NEW' : 'EDIT'}</span>
              <h2>{editingId === null ? `Record ${heading.toLowerCase()}` : `Update ${heading.toLowerCase()}`}</h2>
            </div>
            {section === 'inputs' && <p className="form-alert info-alert">Input purchase costs are recorded here. Do not enter them again as a separate production expense.</p>}
            {section === 'harvests' && <p className="form-alert info-alert">Actual harvests are separate from expected harvest quantities. Zero-yield records are allowed.</p>}
            {section === 'activities' && <p className="form-alert info-alert">Record completed activities only; future-dated activities are not accepted.</p>}
            {!loadingReferences && crops.length === 0 && <p className="form-alert error-alert" role="status">Register a crop before adding production records.</p>}
            <div className="form-grid">{renderForm()}</div>
            <div className="form-actions">
              <button className="button-primary" type="submit" disabled={saving || loadingReferences || crops.length === 0}>
                {saving ? 'Saving…' : editingId === null ? 'Save record' : 'Save changes'} <span aria-hidden="true">→</span>
              </button>
              {editingId !== null && <button className="button-secondary" type="button" onClick={clearForm}>Cancel</button>}
            </div>
            {selectedCrop && <p className="crop-capacity">Crop: {selectedCrop.crop_name}{selectedCrop.variety ? ` · ${selectedCrop.variety}` : ''} · {selectedCrop.farm_name}</p>}
          </form>

          <section className="records-panel" aria-labelledby="production-list-title">
            <div className="records-heading">
              <div>
                <p className="eyebrow"><span /> Production records</p>
                <h2 id="production-list-title">{heading}</h2>
              </div>
              <span className="record-count">{loadingRecords ? '…' : records.length}</span>
            </div>
            {loadingRecords ? (
              <p className="empty-state" role="status">Loading production records…</p>
            ) : records.length === 0 ? (
              <p className="empty-state">No {heading.toLowerCase()} match these filters.</p>
            ) : (
              <div className="record-list">
                {records.map((record) => (
                  <article className={record.is_voided ? 'record-row production-record is-voided' : 'record-row production-record'} key={record.id}>
                    <div className="record-main">
                      <div className="record-avatar" aria-hidden="true">{record.crop_name.trim().charAt(0).toUpperCase()}</div>
                      <div>
                        <h3>{recordTitle(record)}{record.is_voided && <span className="voided-badge">Voided</span>}</h3>
                        <p>{record.crop_name} · {record.farm_name} · {record.farmer_name}</p>
                        <p>{displayDate(recordDate(record))} · {recordDetail(record)}</p>
                        {record.is_voided && <p>Void reason: {record.void_reason}</p>}
                      </div>
                    </div>
                    {!record.is_voided && (
                      <div className="record-meta">
                        <div className="record-actions">
                          <button type="button" onClick={() => editRecord(record)}>Edit</button>
                          <button type="button" className="delete-action" disabled={saving} onClick={() => void voidRecord(record)}>Void</button>
                        </div>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      ) : (
        <ProductionSummaryPanel summary={summary} loading={loadingRecords} />
      )}
    </section>
  )
}

function ProductionSummaryPanel({ summary, loading }: { summary: ProductionSummary | null; loading: boolean }) {
  if (loading) return <p className="empty-state" role="status">Calculating production summary…</p>
  if (!summary) return <p className="empty-state">No summary data is available.</p>

  return (
    <section className="records-panel production-summary" aria-labelledby="production-summary-title">
      <div className="records-heading">
        <div>
          <p className="eyebrow"><span /> Active records only</p>
          <h2 id="production-summary-title">Harvest and cost summary</h2>
        </div>
      </div>
      <p className="summary-scope">
        {summary.harvest_comparison_scope === 'selected_period_only'
          ? 'Harvest totals are limited to the selected date range; they are not compared as a full-season yield.'
          : 'Full recorded-season totals. Voided records are excluded.'}
      </p>
      <div className="summary-counts">
        {Object.entries(summary.active_record_counts).map(([key, count]) => (
          <div className="summary-count" key={key}><strong>{count}</strong><span>{displayStage(key.replace('_', ' '))}</span></div>
        ))}
      </div>
      {summary.crops.length === 0 ? (
        <p className="empty-state">No crop records match these filters.</p>
      ) : (
        <div className="record-list">
          {summary.crops.map((crop) => (
            <article className="summary-crop" key={crop.crop_id}>
              <div className="records-heading">
                <div>
                  <h3>{crop.crop_name}{crop.variety ? ` · ${crop.variety}` : ''}</h3>
                  <p>{crop.farm_name} · {crop.farmer_name}</p>
                </div>
                <span className={crop.comparison.status === 'comparable' ? 'comparison-status comparable' : 'comparison-status'}>{comparisonLabel(crop.comparison.status)}</span>
              </div>
              <div className="summary-values">
                <p><span>Expected</span><strong>{crop.expected_harvest.quantity === null ? 'Not recorded' : `${crop.expected_harvest.quantity} ${crop.expected_harvest.unit}`}</strong></p>
                <p><span>Actual</span><strong>{crop.actual_harvest.normalized_kg === null ? 'No compatible harvest yet' : `${crop.actual_harvest.normalized_kg} kg`}</strong></p>
                {crop.comparison.difference_kg !== null && <p><span>Difference</span><strong>{crop.comparison.difference_kg} kg</strong></p>}
              </div>
              {crop.input_usage_by_type_product_unit.length > 0 && (
                <div className="summary-inputs">
                  <h4>Inputs used</h4>
                  {crop.input_usage_by_type_product_unit.map((input) => (
                    <p key={`${input.input_type}-${input.product_name}-${input.quantity_unit}`}>
                      {input.product_name}: {input.quantity} {input.quantity_unit}
                    </p>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
      <div className="summary-costs">
        <h3>Costs by currency</h3>
        {summary.costs_by_currency.length === 0 ? <p>No costs recorded for this period.</p> : summary.costs_by_currency.map((cost) => (
          <p key={cost.currency_code}><strong>{cost.currency_code} {cost.total}</strong><span>Inputs {cost.input_purchases} · Other expenses {cost.other_expenses}</span></p>
        ))}
      </div>
    </section>
  )
}