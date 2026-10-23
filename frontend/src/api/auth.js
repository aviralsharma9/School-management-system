import { api, setToken, clearToken } from './client'
const USER_KEY = 'sms_user'

export function getCachedUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function setCachedUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}


export async function login(username, password) {
  const data = await api.post('/login', { username, password })
  setToken(data.access_token)
  
  const user = {
    username: data.username,
    name: data.name,
    roles: data.roles,
  }

  setCachedUser(user)

  return user
}

export async function fetchMe() {
  const user = await api.get('/me')
  setCachedUser(user)
  return user
}

export function logout() {
  clearToken()
  localStorage.removeItem(USER_KEY)
}
