# Patient DNI Lookup Specification

## Purpose

Let an API caller determine whether a DNI already belongs to a patient of the authenticated professional, and retrieve that patient's stored data when it does — so a conversational client can tell a returning patient from a new one before deciding what to ask.

**Non-goals**: patient search by name, phone or email; fuzzy matching; cross-professional lookup; any write operation.

## ADDED Requirements

### Requirement: Lookup a patient by DNI

The system MUST resolve a patient from a DNI scoped to the authenticated professional, and MUST return the stored patient data when a match exists so the caller does not have to re-collect it.

#### Scenario: DNI belongs to an existing patient

- **WHEN** a lookup is requested for a DNI that belongs to a patient of the authenticated professional
- **THEN** the system responds `200` with that patient's identifier, `nombre`, `apellido`, `dni` and `telefono`

#### Scenario: DNI is not registered

- **WHEN** a lookup is requested for a DNI that has no patient for the authenticated professional
- **THEN** the system responds `404`

#### Scenario: DNI is absent or empty

- **WHEN** a lookup is requested without a DNI value
- **THEN** the system responds `422` and performs no query

### Requirement: DNI lookup is scoped to the authenticated professional

The system MUST scope every DNI lookup to the professional resolved from the request credentials. A DNI registered under one professional MUST NOT be resolvable by another, even though the same DNI may legitimately exist under several professionals.

#### Scenario: Same DNI registered under two professionals

- **WHEN** professional A and professional B each have a patient with DNI `30111222`, and professional A performs a lookup for `30111222`
- **THEN** the system responds `200` with professional A's patient, and never with professional B's

#### Scenario: DNI exists only under another professional

- **WHEN** professional B performs a lookup for a DNI that exists only under professional A
- **THEN** the system responds `404`, disclosing nothing about the other professional's records

### Requirement: DNI lookup accepts machine and human credentials

The system MUST accept either a valid `X-API-Key` header or a valid `Authorization: Bearer` JWT on the lookup, treating both as equivalent professional-scoped identities, so that both n8n and a dashboard session can use it.

#### Scenario: Lookup with an API key

- **WHEN** a lookup is requested with a valid `X-API-Key` for an active professional
- **THEN** the system resolves that professional and answers the lookup within their scope

#### Scenario: Lookup without credentials

- **WHEN** a lookup is requested with neither an `X-API-Key` nor an `Authorization` header
- **THEN** the system responds `401` with a generic message that does not reveal which schemes are accepted
