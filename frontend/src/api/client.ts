import type { ApiFieldErrors, Farm, FarmInput, FarmerInput, FarmerProfile } from '../types/records'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export class ApiRequestError extends Error {
  readonly fieldErrors: ApiFieldErrors

  constructor(
    message: string,
    fieldErrors: ApiFieldErrors = {},
  ) {
    super(message)
    this.name = 'ApiRequestError'
    this.fieldErrors = fieldErrors
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${apiBaseUrl}${path}`, { ...options, headers })
  const payload: unknown = await response.json().catch(() => null)

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
    const summary = detail ?? Object.values(fieldErrors)[0] ?? `Request failed (${response.status}).`
    throw new ApiRequestError(summary, fieldErrors)
  }

  return payload as T
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