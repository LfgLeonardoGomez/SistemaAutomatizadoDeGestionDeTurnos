class TurnoError(Exception):
    """Base exception for turno domain errors."""


class TurnoNoDisponibleError(TurnoError):
    """Raised when the requested slot is not available."""

    def __init__(self, message: str = "El turno solicitado no está disponible"):
        self.message = message
        super().__init__(self.message)


class TurnoExpiradoError(TurnoError):
    """Raised when trying to confirm an expired temporary reservation."""

    def __init__(self, message: str = "La reserva temporal ha expirado"):
        self.message = message
        super().__init__(self.message)


class PacienteConTurnoActivoError(TurnoError):
    """Raised when a patient already has an active turno (RN-TU-01)."""

    def __init__(self, message: str = "El paciente ya tiene un turno activo"):
        self.message = message
        super().__init__(self.message)


class TurnoNoEncontradoError(TurnoError):
    """Raised when a turno with the given ID does not exist."""

    def __init__(self, message: str = "Turno no encontrado"):
        self.message = message
        super().__init__(self.message)


class TurnoYaCanceladoError(TurnoError):
    """Raised when trying to cancel or reschedule a turno that is already CANCELADO."""

    def __init__(self, message: str = "El turno ya está cancelado"):
        self.message = message
        super().__init__(self.message)
