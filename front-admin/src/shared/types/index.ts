export interface ProfesionalAdminResponse {
  id: number
  nombre: string
  especialidad: string
  email: string
  is_active: boolean
  creado_en: string
}

export interface ProfesionalCreateRequest {
  nombre: string
  email: string
  password: string
  especialidad: string
}

export interface ProfesionalCreateResponse {
  id: number
  nombre: string
  email: string
  especialidad: string
  is_active: boolean
  duracion_turno: number
  horario_inicio: string
  horario_fin: string
  dias_atencion: string[]
  api_key: string
  telegram_secret_token: string
}

export interface GlobalMetrics {
  total_profesionales: number
  profesionales_activos: number
  profesionales_inactivos: number
  total_turnos: number
  turnos_hoy: number
  turnos_confirmados_30d: number
  turnos_cancelados_30d: number
  total_pacientes: number
  tasa_confirmacion_30d: number
  tasa_cancelacion_30d: number
}

export interface SuperAdminLoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}
