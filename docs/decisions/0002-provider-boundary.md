# ADR 0002: Normalize providers before the UI boundary

- Status: accepted
- Date: 2026-09-19

## Context

Providers expose different concepts, payload shapes, reset windows, authentication states, and failure modes. Embedding provider-specific parsing in QML would couple the UI to unstable protocols and make partial failure difficult to contain.

## Decision

Every provider adapter returns the versioned snapshot defined in `contracts/provider-snapshot.schema.json`. The UI uses only that contract. Raw provider responses are transient and are neither persisted nor logged.

The first adapter will use Codex app-server account methods. It will be replaceable without changing the UI contract.

## Consequences

- Provider protocol changes remain isolated.
- Fixtures can exercise UI states without real accounts.
- Last-good caching has a stable, privacy-reviewed format.
- Some provider-specific details may require future optional contract fields or a schema-version change.
