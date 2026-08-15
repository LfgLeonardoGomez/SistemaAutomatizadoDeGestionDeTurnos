export type TurnoEstado = 'DISPONIBLE' | 'RESERVADO_TEMPORAL' | 'CONFIRMADO' | 'CANCELADO' | 'COMPLETADO'

export interface Turno {
  id: number
  fecha: string
  hora_inicio: string
  hora_fin: string
  estado: TurnoEstado
  profesional_id: number
  paciente_id: number | null
  google_event_id: string | null
  creado_en: string
}

export interface PacienteInfo {
  id: number
  nombre: string
  apellido: string
  dni: string
  telefono: string
}

export interface TurnoConPaciente {
  id: number
  fecha: string
  hora_inicio: string
  hora_fin: string
  estado: TurnoEstado
  profesional_id: number
  paciente_id: number | null
  paciente: PacienteInfo | null
}

export interface Paciente {
  id: number
  nombre: string
  apellido: string
  dni: string
  telefono: string
  creado_en: string
}

export interface PacienteConHistorial extends Paciente {
  turnos: Turno[]
}

export interface PacienteBusqueda {
  id: number
  nombre: string
  apellido: string
  dni: string
  telefono: string
}

export interface SlotResponse {
  hora_inicio: string
  hora_fin: string
  disponible: boolean
}

export interface ReservaTurnoRequest {
  fecha: string
  hora_inicio: string
  paciente_id?: number
}

export interface ConfirmarTurnoRequest {
  nombre: string
  apellido: string
  dni: string
  telefono: string
  email?: string
}

export interface ReprogramarTurnoRequest {
  nueva_fecha: string
  nueva_hora_inicio: string
  paciente_data?: ConfirmarTurnoRequest
}

export interface ProfesionalConfig {
  horario_inicio: string
  horario_fin: string
  dias_atencion: string[]
  duracion_turno: number
  especialidad: string
}

export interface ProfesionalConfigUpdate {
  horario_inicio?: string
  horario_fin?: string
  dias_atencion?: string[]
  duracion_turno?: number
}

export interface Metricas {
  turnos_hoy: number
  tasa_confirmacion_30d: number
  tasa_cancelacion_30d: number
}

export interface Integraciones {
  has_telegram: boolean
  has_google: boolean
  google_calendar_id: string
}

export interface IntegracionesUpdate {
  telegram_bot_token?: string
  google_refresh_token?: string
  google_calendar_id?: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}
