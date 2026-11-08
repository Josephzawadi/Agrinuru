import type {
  ApiFieldErrors,
  Crop,
  CropInput,
  Farm,
  FarmInput,
  FarmerInput,
  FarmerProfile,
  HarvestRecord,
  HarvestRecordInput,
  InputUsage,
  InputUsageInput,
  ProductionActivity,
  ProductionActivityInput,
  ProductionExpense,
  ProductionExpenseInput,
  ProductionFilters,
  ProductionSummary,
} from '../types/records'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export interface AuthUser {
  id: number
  username: string
  email: string
  role: 'administrator' | 'staff' | 'farmer' | 'unlinked'
  has_farmer_profile: boolean
}

export class ApiRequestError extends Error {
  readonly fieldErrors: ApiFieldErrors
  readonly statusCode: number

  constructor(
    message: string,
    fieldErrors: ApiFieldErrors = {},
    statusCode = 0,
  ) {
    super(message)
    this.name = 'ApiRequestError'
    this.fieldErrors = fieldErrors
    this.statusCode = statusCode
  }
}

type SessionExpiredListener = () => void

const sessionExpiredListeners = new Set<SessionExpiredListener>()
let sessionExpiredNotified = false
let sessionCheck: Promise<boolean | null> | null = null
let sessionCheckCache: { checkedAt: number; result: boolean | null } | null = null

export function subscribeToSessionExpired(listener: SessionExpiredListener) {
  sessionExpiredListeners.add(listener)
  if (sessionExpiredNotified) listener()
  return () => {
    sessionExpiredListeners.delete(listener)
  }
}

function resetSessionExpired() {
  sessionExpiredNotified = false
  sessionCheckCache = null
}

function notifySessionExpired() {
  if (sessionExpiredNotified) return
  sessionExpiredNotified = true
  for (const listener of sessionExpiredListeners) listener()
}

async function verifySession(): Promise<boolean | null> {
  if (sessionExpiredNotified) return false
  if (sessionCheckCache && Date.now() - sessionCheckCache.checkedAt < 5000) {
    return sessionCheckCache.result
  }
  if (!sessionCheck) {
    sessionCheck = fetch(`${apiBaseUrl}/api/auth/me/`, {
      credentials: 'include',
    })
      .then((response) => {
        if (response.ok) return true
        if (response.status === 401 || response.status === 403) return false
        return null
      })
      .catch(() => null)
      .then((result) => {
        sessionCheckCache = { checkedAt: Date.now(), result }
        return result
      })
      .finally(() => {
        sessionCheck = null
      })
  }
  return sessionCheck
}

function isAuthenticationEndpoint(path: string) {
  return [
    '/api/auth/csrf/',
    '/api/auth/register/',
    '/api/auth/login/',
    '/api/auth/me/',
  ].includes(path.split('?')[0])
}

export function apiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiRequestError) {
    if (error.statusCode === 401) return 'Your session has expired. Please sign in again.'
    if (error.statusCode === 403) return 'You do not have permission to perform this action.'
    if (error.statusCode >= 500) return 'The server encountered an error. Please try again later.'
    if (error.statusCode === 0) return 'Could not reach the server. Check your network connection and try again.'
    return error.message
  }
  if (error instanceof TypeError) {
    return 'Could not reach the server. Check your network connection and try again.'
  }
  return fallback
}

async function csrfToken(): Promise<string> {
  const response = await fetch(`${apiBaseUrl}/api/auth/csrf/`, {
    credentials: 'include',
  })
  const payload: unknown = await response.json().catch(() => null)

  if (!response.ok || !payload || typeof payload !== 'object' || !('csrfToken' in payload) || typeof payload.csrfToken !== 'string') {
    throw new ApiRequestError(`Could not prepare a secure request (${response.status}).`, {}, response.status)
  }

  return payload.csrfToken
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const method = (options.method ?? 'GET').toUpperCase()
  if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
    headers.set('X-CSRFToken', await csrfToken())
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    credentials: 'include',
    headers,
  })
  const payload: unknown = await response.json().catch(() => null)

  let sessionExpired = response.status === 401
  if (!response.ok && !isAuthenticationEndpoint(path)) {
    if (sessionExpired) {
      notifySessionExpired()
    } else if (response.status === 403 && await verifySession() === false) {
      sessionExpired = true
      notifySessionExpired()
    }
  }

  if (!response.ok) {
    const data = payload && typeof payload === 'object'
      ? payload as Record<string, unknown>
      : {}
    const fieldErrors: ApiFieldErrors = {}
    for (const [field, value] of Object.entries(data)) {
      if (field === 'detail') continue
      const message = Array.isArray(value) ? value.join(' ') : String(value)
      if (message && message !== '[object Object]') fieldErrors[field] = message
    }

    const detail = typeof data.detail === 'string' ? data.detail : undefined
    const statusCode = sessionExpired ? 401 : response.status
    const summary = sessionExpired
      ? 'Your session has expired. Please sign in again.'
      : detail ?? Object.values(fieldErrors)[0] ?? `Request failed (${response.status}).`
    throw new ApiRequestError(summary, fieldErrors, statusCode)
  }

  return payload as T
}

export const authApi = {
  register: (data: {
    username: string
    email: string
    full_name: string
    phone_number: string
    county: string
    sub_county: string
    password: string
  }) =>
    request<AuthUser>('/api/auth/register/', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  login: (data: { username: string; password: string }) =>
    request<AuthUser>('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify(data),
    }).then((user) => {
      resetSessionExpired()
      return user
    }),
  logout: () => request<{ detail: string }>('/api/auth/logout/', { method: 'POST' }),
  currentUser: () => request<AuthUser>('/api/auth/me/').then((user) => {
    resetSessionExpired()
    return user
  }),
}

export const farmerApi = {
  list: () => request<FarmerProfile[]>('/api/farmers/'),
  create: (data: FarmerInput) => request<FarmerProfile>('/api/farmers/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: number, data: Partial<FarmerInput>) => request<FarmerProfile>(`/api/farmers/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  remove: (id: number) => request<void>(`/api/farmers/${id}/`, { method: 'DELETE' }),
}

export const farmApi = {
  list: () => request<Farm[]>('/api/farms/'),
  create: (data: FarmInput) => request<Farm>('/api/farms/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: number, data: Partial<FarmInput>) => request<Farm>(`/api/farms/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  remove: (id: number) => request<void>(`/api/farms/${id}/`, { method: 'DELETE' }),
}

export const cropApi = {
  list: () => request<Crop[]>('/api/crops/'),
  create: (data: CropInput) => request<Crop>('/api/crops/', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  update: (id: number, data: Partial<CropInput>) => request<Crop>(`/api/crops/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),
  remove: (id: number) => request<void>(`/api/crops/${id}/`, { method: 'DELETE' }),
}

function queryString(filters: ProductionFilters = {}) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value))
    }
  }
  const query = params.toString()
  return query ? `?${query}` : ''
}

function productionResource<TRecord, TInput>(resource: string) {
  const basePath = `/api/production/${resource}/`
  return {
    list: (filters?: ProductionFilters) => request<TRecord[]>(`${basePath}${queryString(filters)}`),
    retrieve: (id: number) => request<TRecord>(`${basePath}${id}/`),
    create: (data: TInput) => request<TRecord>(basePath, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
    update: (id: number, data: Partial<TInput>) => request<TRecord>(`${basePath}${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
    void: (id: number, reason: string) => request<TRecord>(`${basePath}${id}/void/`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  }
}

export const productionActivityApi = productionResource<ProductionActivity, ProductionActivityInput>('activities')
export const inputUsageApi = productionResource<InputUsage, InputUsageInput>('inputs')
export const productionExpenseApi = productionResource<ProductionExpense, ProductionExpenseInput>('expenses')
export const harvestRecordApi = productionResource<HarvestRecord, HarvestRecordInput>('harvests')

export const productionSummaryApi = {
  get: (filters?: Omit<ProductionFilters, 'include_voided'>) =>
    request<ProductionSummary>(`/api/production/summary/${queryString(filters)}`),
}