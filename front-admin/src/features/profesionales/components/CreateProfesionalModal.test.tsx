import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { CreateProfesionalModal } from './CreateProfesionalModal'
import * as profesionalService from '../services/profesionalService'
import type { ProfesionalCreateResponse } from '../../../shared/types'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

function renderModal(onSuccess = vi.fn(), onClose = vi.fn()) {
  return render(<CreateProfesionalModal isOpen onClose={onClose} onSuccess={onSuccess} />, { wrapper })
}

describe('CreateProfesionalModal', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows validation errors when submitting empty fields', async () => {
    const user = userEvent.setup()
    renderModal()

    await user.click(screen.getByRole('button', { name: /crear profesional/i }))

    expect(await screen.findAllByRole('alert')).toHaveLength(5)
  })

  it('shows an error when password and confirmar contraseña do not match', async () => {
    const user = userEvent.setup()
    renderModal()

    await user.type(screen.getByLabelText(/nombre completo/i), 'Dr. Alejandro Méndez')
    await user.type(screen.getByLabelText(/correo electrónico/i), 'alejandro@clinica.com')
    await user.type(screen.getByLabelText(/^especialidad/i), 'Ortodoncia')
    await user.type(screen.getByLabelText(/^contraseña$/i), 'password123')
    await user.type(screen.getByLabelText(/confirmar contraseña/i), 'otrapassword')
    await user.click(screen.getByRole('button', { name: /crear profesional/i }))

    expect(await screen.findByText(/las contraseñas no coinciden/i)).toBeInTheDocument()
  })

  it('submits and calls onSuccess with the created profesional on 201', async () => {
    const response: ProfesionalCreateResponse = {
      id: 5,
      nombre: 'Dr. Alejandro Méndez',
      email: 'alejandro@clinica.com',
      especialidad: 'Ortodoncia',
      is_active: true,
      duracion_turno: 30,
      horario_inicio: '09:00',
      horario_fin: '18:00',
      dias_atencion: ['lunes'],
      api_key: 'pk_live_abc123',
      telegram_secret_token: 'tg_secret_xyz',
    }
    vi.spyOn(profesionalService, 'createProfesional').mockResolvedValue(response)
    const onSuccess = vi.fn()
    const user = userEvent.setup()
    renderModal(onSuccess)

    await user.type(screen.getByLabelText(/nombre completo/i), 'Dr. Alejandro Méndez')
    await user.type(screen.getByLabelText(/correo electrónico/i), 'alejandro@clinica.com')
    await user.type(screen.getByLabelText(/^especialidad/i), 'Ortodoncia')
    await user.type(screen.getByLabelText(/^contraseña$/i), 'password123')
    await user.type(screen.getByLabelText(/confirmar contraseña/i), 'password123')
    await user.click(screen.getByRole('button', { name: /crear profesional/i }))

    await vi.waitFor(() => expect(onSuccess).toHaveBeenCalledWith(response))
  })

  it('shows a duplicate-email message on 409 and keeps the modal open', async () => {
    vi.spyOn(profesionalService, 'createProfesional').mockRejectedValue({
      response: { status: 409 },
    })
    const onClose = vi.fn()
    const user = userEvent.setup()
    renderModal(vi.fn(), onClose)

    await user.type(screen.getByLabelText(/nombre completo/i), 'Dr. Alejandro Méndez')
    await user.type(screen.getByLabelText(/correo electrónico/i), 'alejandro@clinica.com')
    await user.type(screen.getByLabelText(/^especialidad/i), 'Ortodoncia')
    await user.type(screen.getByLabelText(/^contraseña$/i), 'password123')
    await user.type(screen.getByLabelText(/confirmar contraseña/i), 'password123')
    await user.click(screen.getByRole('button', { name: /crear profesional/i }))

    expect(await screen.findByText(/ya existe un profesional con ese email/i)).toBeInTheDocument()
    expect(onClose).not.toHaveBeenCalled()
  })
})
