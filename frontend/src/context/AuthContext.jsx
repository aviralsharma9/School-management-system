import { createContext, useContext, useEffect, useState } from 'react'
import { getToken } from '../api/client'
import {
  getCachedUser,
  fetchMe,
  login as apiLogin,
  logout as apiLogout,
} from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => (getToken() ? getCachedUser() : null))
  const [checking, setChecking] = useState(() => Boolean(getToken()))

  useEffect(() => {
    if (!getToken()) {
      setChecking(false)
      return
    }

    let cancelled = false

    fetchMe()
      .then((fresh) => {
        if (!cancelled) setUser(fresh)
      })
      .catch(() => {
        if (!cancelled) setUser(null)
      })
      .finally(() => {
        if (!cancelled) setChecking(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  async function login(username, password) {
    const loggedIn = await apiLogin(username, password)
    setUser(loggedIn)
    return loggedIn
  }

  function logout() {
    apiLogout()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, checking, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (context === null) {
    throw new Error('useAuth must be used inside an AuthProvider')
  }

  return context
}