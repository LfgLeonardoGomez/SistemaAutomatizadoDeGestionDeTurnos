## MODIFIED Requirements

### Requirement: ReservaTemporal tiene tiempo de expiración
El sistema SHALL almacenar `expiracion` como TIMESTAMP en `ReservaTemporal`. **El valor SHALL ser naive-UTC (sin `tzinfo`) para mantener compatibilidad con la columna `TIMESTAMP WITHOUT TIME ZONE` de PostgreSQL, pero SHALL estar siempre expresado en tiempo universal coordinado (UTC).** El sistema SHALL garantizar que todas las comparaciones de expiración en código de aplicación (`expiracion < NOW()`) se realicen contra `datetime.now(timezone.utc).replace(tzinfo=None)`, evitando `datetime.now()` naive que depende del timezone del servidor.

#### Scenario: Expiración futura
- **WHEN** se crea una `ReservaTemporal` con `expiracion` dentro de 2 minutos calculado como `datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=2)`
- **THEN** la reserva se persiste con el timestamp correcto

#### Scenario: Comparación de expiración es timezone-consistent
- **WHEN** el servidor tiene timezone `America/Argentina/Buenos_Aires` (UTC-3)
- **AND** una `ReservaTemporal` tiene `expiracion = 2026-06-27 15:00:00` (naive UTC = 12:00:00 ART)
- **AND** la hora actual local es `2026-06-27 12:00:30` (que es `2026-06-27 15:00:30` UTC)
- **THEN** el sistema SHALL comparar `expiracion` contra `datetime.now(timezone.utc).replace(tzinfo=None)` (= 15:00:30)
- **AND** SHALL detectar correctamente que la reserva aún NO expiró

#### Scenario: Comparación de expiración detecta reserva vencida en UTC
- **WHEN** el servidor tiene timezone `America/Argentina/Buenos_Aires` (UTC-3)
- **AND** una `ReservaTemporal` tiene `expiracion = 2026-06-27 15:00:00` (naive UTC)
- **AND** la hora actual local es `2026-06-27 12:01:00` (que es `2026-06-27 15:01:00` UTC)
- **THEN** el sistema SHALL detectar la expiración correctamente

## ADDED Requirements

(ninguno)

## REMOVED Requirements

(ninguno)
