import { api, setTokens, clearTokens } from './api'
import type { LoginRequest, LoginResponse, User } from '../types/auth'

export type LoginResult = LoginResponse | { mfa_required: true; mfa_pending_token: string }

export async function login(email: string, password: string): Promise<LoginResult> {
  const { data } = await api.post<LoginResult>('/api/auth/login/', {
    email,
    password,
  } as LoginRequest)
  if ('mfa_required' in data && data.mfa_required) {
    return data
  }
  const res = data as LoginResponse
  setTokens(res.access, res.refresh)
  return res
}

export async function initMFASetup(): Promise<{ secret: string; qr_code_base64: string; otpauth_uri: string }> {
  const { data } = await api.get<{ secret: string; qr_code_base64: string; otpauth_uri: string }>('/api/auth/mfa/setup/')
  return data
}

export async function confirmMFASetup(code: string): Promise<{ success: boolean; backup_codes: string[] }> {
  const { data } = await api.post<{ success: boolean; backup_codes: string[] }>('/api/auth/mfa/setup/confirm/', { code })
  return data
}

export async function disableMFA(payload: { code?: string; backup_code?: string }): Promise<void> {
  await api.post('/api/auth/mfa/disable/', payload)
}

export async function verifyMFA(mfaPendingToken: string, payload: { code?: string; backup_code?: string }): Promise<LoginResponse> {
  const { data } = await api.post<LoginResponse>('/api/auth/mfa/verify/', {
    mfa_pending_token: mfaPendingToken,
    ...payload,
  })
  setTokens(data.access, data.refresh)
  return data
}

export async function getSSOAuthUrl(provider: 'google' | 'microsoft'): Promise<string> {
  const { data } = await api.get<{ auth_url: string }>(`/api/auth/sso/${provider}/`)
  return data.auth_url
}

export async function logout(): Promise<void> {
  const refresh = localStorage.getItem('axdoc_refresh_token')
  if (refresh) {
    try {
      await api.post('/api/auth/logout/', { refresh })
    } catch {
      // ignore
    }
  }
  clearTokens()
}

export async function getMe(): Promise<User> {
  const { data } = await api.get<User>('/api/auth/me/')
  return data
}

export async function requestPasswordReset(email: string): Promise<void> {
  await api.post('/api/auth/password-reset/', { email })
}

export async function confirmPasswordReset(
  token: string,
  new_password: string,
  new_password_confirm: string
): Promise<void> {
  await api.post('/api/auth/password-reset/confirm/', {
    token,
    new_password,
    new_password_confirm,
  })
}

export async function changePassword(
  old_password: string,
  new_password: string,
  new_password_confirm: string
): Promise<void> {
  await api.post('/api/auth/change-password/', {
    old_password,
    new_password,
    new_password_confirm,
  })
}

export async function changePasswordRequired(
  newPassword: string,
  confirmPassword: string
): Promise<void> {
  await api.post('/api/auth/change_password/', {
    new_password: newPassword,
    confirm_password: confirmPassword,
  })
}
