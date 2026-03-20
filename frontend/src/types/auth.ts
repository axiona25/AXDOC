export type UserRole = 'OPERATOR' | 'REVIEWER' | 'APPROVER' | 'ADMIN'

export type UserType = 'internal' | 'guest'

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  user_type?: UserType
  is_guest?: boolean
  role: UserRole
  avatar: string | null
  phone: string
  must_change_password?: boolean
  mfa_enabled?: boolean
  is_active?: boolean
  date_joined?: string
  organizational_unit?: {
    id: string
    name: string
    code: string
  } | null
  organizational_units?: Array<{
    id: string
    name: string
    code: string
  }>
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access: string
  refresh: string
  user: User
  must_change_password: boolean
}
