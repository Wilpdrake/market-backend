# OpenAPI contract

[`openapi.yaml`](openapi.yaml) is the single machine-readable contract for the public,
administrative and planned Market Backend HTTP API.

- `x-status: implemented` marks operations exposed by the current FastAPI application;
- `x-status: planned` marks contract-first operations that are not available yet.

## Frontend usage

The frontend may use the contract to:

1. generate TypeScript types with `openapi-typescript` or Orval;
2. run a local mock server with Prism;
3. implement MSW handlers that return examples conforming to the schemas;
4. review contract changes before backend implementation.

Do not hand-copy `TerminalKey`, terminal passwords or provider signing secrets into generated
frontend configuration. The only public terminal identifier is `payment_option_id`.

## Approval checklist

Before changing `x-status` from `planned` to `implemented`, the API review should confirm:

- Google account-linking policy and allowed OAuth Client IDs;
- authenticated-only checkout versus guest checkout;
- final order/customer/delivery fields;
- one-stage versus two-stage T‑Bank payments;
- card/SBP terminal mapping;
- fiscal receipt (54-FZ) requirements;
- success/failure frontend URLs and refund policy.

After approval, backend tests must compare the relevant paths and component schemas from the
FastAPI-generated `/openapi.json` with this contract. Breaking changes require explicit API
review rather than silent edits.

Architecture documentation remains in [`structure.md`](structure.md), while Pydantic model
conventions remain in [`pydantic-models.md`](pydantic-models.md).

## Local validation

The repository validates this document by parsing YAML, validating it with FastAPI's OpenAPI
model, resolving every local `$ref`, checking unique `operationId` values and checking the
expected operation set. A dedicated CI command can be added when the team selects a shared
OpenAPI linter (for example Redocly CLI or Spectral).
