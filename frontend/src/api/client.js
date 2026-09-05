const API_URL = import.meta.env.VITE_API_URL

const TOKEN_KEY = 'sms_token'

//------Token storage-------

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

//------Function talks to backend-------

async function apiRequest(path, options = {}) {
  const token = getToken()

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}${path}`, {
    method: options.method || 'GET',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })

  const isAuthEndpoint = path === '/login' || path === '/token'

  if (response.status === 401 && token && !isAuthEndpoint) {
    clearToken()
    window.location.href = '/login'
    throw new Error('Session expired. Please log in again.')
  }
  
  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(extractError(data, response.status))
  }

  return data
}

function extractError(data, status) {
  const detail = data?.detail

  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join(', ')

  return `Request failed (${status})`
}

export const api = {
  get: (path) => apiRequest(path, { method: 'GET' }),
  post: (path, body) => apiRequest(path, { method: 'POST', body }),
  put: (path, body) => apiRequest(path, { method: 'PUT', body }),
  del: (path) => apiRequest(path, { method: 'DELETE' }),
}
