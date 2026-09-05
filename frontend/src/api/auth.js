import { api, setToken, clearToken } from './client'

export async function login(username, password) {
  const data = await api.post('/login', { username, password })
  setToken(data.access_token)
  return data
}

export function logout() {
  clearToken()
}