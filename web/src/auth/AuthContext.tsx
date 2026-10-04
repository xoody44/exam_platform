import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import api from '../api/client'
import type { LoginResponse } from '../api/types'

interface AuthState {
  token: string | null
  username: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'))
  const [username, setUsername] = useState<string | null>(() => localStorage.getItem('username'))

  const value = useMemo<AuthState>(
    () => ({
      token,
      username,
      async login(u: string, p: string) {
        const { data } = await api.post<LoginResponse>('/auth/login', {
          username: u,
          password: p,
        })
        localStorage.setItem('token', data.access_token)
        localStorage.setItem('username', data.user.username)
        setToken(data.access_token)
        setUsername(data.user.username)
      },
      logout() {
        localStorage.removeItem('token')
        localStorage.removeItem('username')
        setToken(null)
        setUsername(null)
      },
    }),
    [token, username],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth должен вызываться внутри AuthProvider')
  return ctx
}