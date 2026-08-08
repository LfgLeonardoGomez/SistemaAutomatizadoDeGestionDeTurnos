## ADDED Requirements

### Requirement: Autenticación dual en los endpoints de pacientes
El sistema SHALL aceptar, en todos los endpoints de `/pacientes`, tanto un header `X-API-Key` válido como un `Authorization: Bearer` JWT válido, tratándolos como identidades equivalentes con alcance de profesional. Esto habilita a los llamadores máquina (n8n), que hoy reciben 401 porque los endpoints exigen JWT exclusivamente.

El alcance de autorización NO cambia: el profesional se resuelve por request y toda consulta sigue acotada a su `profesional_id`.

#### Scenario: Acceso con API key
- **WHEN** se envía un request a un endpoint de /pacientes con un `X-API-Key` válido de un profesional activo
- **THEN** el sistema resuelve ese profesional y responde acotado a sus pacientes

#### Scenario: Acceso con JWT
- **WHEN** se envía un request a un endpoint de /pacientes con un `Authorization: Bearer` JWT válido
- **THEN** el sistema responde igual que antes de este cambio, sin regresión

#### Scenario: Sin credenciales
- **WHEN** se envía un request a un endpoint de /pacientes sin `X-API-Key` ni `Authorization`
- **THEN** el sistema retorna 401 con un mensaje genérico que no revela qué esquemas acepta

#### Scenario: API key de un profesional inactivo
- **WHEN** se envía un request con un `X-API-Key` que corresponde a un profesional dado de baja
- **THEN** el sistema retorna 401 y no expone ningún dato

#### Scenario: Aislamiento entre profesionales
- **WHEN** un profesional accede a /pacientes autenticado con su `X-API-Key`
- **THEN** el sistema retorna únicamente pacientes cuyo `profesional_id` coincide con el suyo, sin filtrar pacientes de otros profesionales
