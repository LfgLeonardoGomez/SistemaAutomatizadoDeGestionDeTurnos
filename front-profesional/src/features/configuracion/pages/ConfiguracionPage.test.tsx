import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ConfiguracionPage from './ConfiguracionPage'
import * as configuracionService from '../services/configuracionService'
import type { ProfesionalConfig } from '../../../shared/types'

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ConfiguracionPage />
    </QueryClientProvider>,
  )
}

const config: ProfesionalConfig = {
  horario_inicio: '09:00',
  horario_fin: '17:00',
  dias_atencion: ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'],
  duracion_turno: 30,
  especialidad: 'Odontología general',
}

describe('ConfiguracionPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a loading skeleton while fetching', () => {
    vi.spyOn(configuracionService, 'getConfiguracion').mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByRole('status', { name: /cargando/i })).toBeInTheDocument()
  })

  it('loads the current configuracion into the form', async () => {
    vi.spyOn(configuracionService, 'getConfiguracion').mockResolvedValue(config)
    renderPage()

    expect(await screen.findByDisplayValue('09:00')).toBeInTheDocument()
    expect(screen.getByDisplayValue('17:00')).toBeInTheDocument()
    expect(screen.getByDisplayValue('30')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Odontología general')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Lunes' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Sábado' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('especialidad is read-only', async () => {
    vi.spyOn(configuracionService, 'getConfiguracion').mockResolvedValue(config)
    renderPage()
    expect(await screen.findByDisplayValue('Odontología general')).toHaveAttribute('readonly')
  })

  it('shows a validation error when horario_inicio is not before horario_fin', async () => {
    vi.spyOn(configuracionService, 'getConfiguracion').mockResolvedValue(config)
    const user = userEvent.setup()
    renderPage()

    const horarioFin = await screen.findByLabelText(/hora de fin/i)
    await user.clear(horarioFin)
    await user.type(horarioFin, '08:00')
    await user.click(screen.getByRole('button', { name: /guardar cambios/i }))

    expect(await screen.findByText(/la hora de inicio debe ser menor a la hora de fin/i)).toBeInTheDocument()
  })

  it('shows a validation error when no dias are selected', async () => {
    vi.spyOn(configuracionService, 'getConfiguracion').mockResolvedValue(config)
    const user = userEvent.setup()
    renderPage()

    for (const dia of config.dias_atencion) {
      await user.click(await screen.findByRole('button', { name: dia }))
    }
    await user.click(screen.getByRole('button', { name: /guardar cambios/i }))

    expect(await screen.findByText(/seleccioná al menos un día/i)).toBeInTheDocument()
  })

  it('saves the configuracion and shows a success message', async () => {
    vi.spyOn(configuracionService, 'getConfiguracion').mockResolvedValue(config)
    const updateSpy = vi.spyOn(configuracionService, 'updateConfiguracion').mockResolvedValue(config)
    const user = userEvent.setup()
    renderPage()

    await screen.findByDisplayValue('09:00')
    await user.click(screen.getByRole('button', { name: /guardar cambios/i }))

    await vi.waitFor(() =>
      expect(updateSpy).toHaveBeenCalledWith(
        {
          horario_inicio: '09:00',
          horario_fin: '17:00',
          dias_atencion: ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'],
          duracion_turno: 30,
        },
        expect.anything(),
      ),
    )
    expect(await screen.findByText(/cambios guardados/i)).toBeInTheDocument()
  })
})
