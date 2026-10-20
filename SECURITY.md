# Security policy — n8n Persian Pack

This document covers the workflow JSON files, documentation, scripts and the example Docker Compose
file in this repository. It does not cover your n8n instance, server, reverse proxy, provider
accounts or the customer data that flows through your workflows.

Persian documentation starts at [`README.fa.md`](README.fa.md); credentials setup is described in
[`docs/credentials-fa.md`](docs/credentials-fa.md).

## Supported versions

| Version | Supported |
| --- | --- |
| `1.1.x` | Yes |
| `1.0.x` | No; the webhook nodes in 1.0.0 had no authentication |

The pack is a set of JSON workflows, not a library. Fixes are applied to the current branch; older
exports are not backported.

## Reporting a vulnerability

Open a **private** GitHub Security Advisory:

<https://github.com/sirdadfar/n8n-persian-pack/security/advisories/new>

Do not open a public issue for a suspected vulnerability, and never paste live tokens, webhook
credentials, customer phone numbers or a production n8n URL into a report. Redact the payload and
describe the node and workflow file instead.

This is a single-maintainer portfolio project: no SLA and no bounty.

## In scope

- The exported workflow JSON in `workflows/`.
- `scripts/validate.mjs` (structural checks, webhook authentication check, secret scan).
- `scripts/build_workflows.py` (must keep the JSON safe when regenerated).
- `docker-compose.yml` and `env.example` as examples of a safe default.
- Documentation that could lead a user into an insecure setup.

## Out of scope

- Your n8n installation, database, encryption key, user accounts and network.
- Third-party providers (WooCommerce, Kavenegar, Telegram, CRM, OCR, Postgres).
- Data protection law compliance for the customer data your workflows process.
- Custom nodes or community packages you add.
- The workflows' business logic after you edit them.

## Security design

### No secrets in the repository

- Every credential is read from `$env` or from an n8n Credential; no token, password, API key or
  private key is committed.
- `env.example` contains only placeholders (`change-me`), never real values.
- `scripts/validate.mjs` fails the build when a node parameter contains something that looks like a
  literal secret (OpenAI/GitHub/Slack/AWS keys, Telegram bot tokens, JWTs, private keys, hard-coded
  Bearer tokens) or when a `credentials` object carries `data`/`value` fields.
- The same script fails when a webhook node has `authentication: none` or has authentication but no
  Credential attached.

### Webhooks are authenticated by default

Workflows 04 (`lead`) and 05 (`invoice-scan`) accept public HTTP input. Both ship with
`authentication: basicAuth` and a reference to a credential named
`Webhook Basic Auth (n8n Persian Pack)`.

- After import you must create that Basic Auth credential and assign it; until then the node reports
  a missing credential and the webhook does not run as intended.
- The webhook path is published in this repository, so path secrecy is **not** a control. Treat the
  URL as public.
- Put n8n behind HTTPS. Basic Auth without TLS sends the password in clear text.
- The lead workflow normalises the phone number and tolerates missing fields, but upstream
  validation is still your job: the webhook is an untrusted input boundary.

### Instance hardening (the example, not a guarantee)

`docker-compose.yml` is a starting point, not a hardened deployment:

- The published port is bound to `127.0.0.1`. Expose n8n through a reverse proxy with TLS and an
  access control layer; do not publish `0.0.0.0:5678`.
- `N8N_ENCRYPTION_KEY` comes from `.env`; generate a long random value and back it up. Losing it
  makes stored credentials unreadable.
- `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` is required for `$env` expressions in these workflows. It
  means anyone who can edit a workflow can read process environment variables. Restrict editor
  access to people you would trust with the server, and on n8n versions that support
  `N8N_BLOCKED_ENV_VARIABLES`, block `N8N_ENCRYPTION_KEY` and database credentials.
- n8n's Code node executes JavaScript on the server. Editor access is effectively server access;
  there is no sandbox boundary to rely on.
- `N8N_BASIC_AUTH_*` in `env.example` is a legacy option; current n8n versions use user management
  with email/password and optional 2FA. Use that instead of the legacy variables.
- Execution data may contain customer messages and order payloads. Configure retention/pruning
  (`EXECUTIONS_DATA_PRUNE`, `EXECUTIONS_DATA_MAX_AGE`) to match your data policy.

### Data leaving your server

The workflows intentionally send data to third parties:

- Kavenegar (SMS) receives phone numbers and message text.
- Telegram receives chat ids and report/alert text.
- The CRM and the OCR provider receive lead and invoice data.
- The default OCR endpoint is `api.ocr.space`, a foreign service. If invoice images must not leave
  the country, point `OCR_API_URL` at a self-hosted or local provider. The workflow only requires a
  `ParsedText`/`text` field in the response.

Document this in your own privacy notice before using the pack with real customers.

### Transport and URLs

- HTTP Request nodes call URLs built from environment variables. Only administrators should be able
  to change `.env`; a malicious `WOO_BASE_URL` or `CRM_API_URL` redirects customer data.
- `KAVENEGAR_BASE_URL` and `OCR_API_URL` are overridable on purpose (regional or self-hosted
  providers). Treat changing them as a security-relevant change.
- There is no automatic retry on webhook responses; a failing CRM call surfaces as a workflow error
  instead of silently dropping the lead.

## Known gaps and residual risk

- **Not tested against a live n8n in CI.** CI validates structure, connections, webhook auth and
  secrets with `npm run validate`; `scripts/import-test.sh` performs a real import but needs a local
  n8n instance and is not part of CI.
- **Credentials are referenced, not provisioned.** Import cannot create provider credentials for
  you; the documented manual step is mandatory.
- **No rate limiting inside the workflows.** A public webhook can be spammed at the HTTP layer; use
  your reverse proxy or n8n's own limits. SMS sending costs money per message.
- **No signature verification for providers that support it.** The pack uses Basic Auth on the
  webhook; if your provider can sign payloads, add a verification node.
- **Phone/amount parsing is heuristic.** It normalises digits and strips separators, but it is not
  a substitute for validating input in the source form.
- **No secret rotation automation.** Rotate provider keys and the webhook password manually.

## CI posture

`.github/workflows/validate.yml` runs on every push:

1. `npm run validate` — structure, UUIDs, connections, orphan nodes, webhook authentication,
   credential attachment, secret scan.
2. `jq` check that every file is valid JSON with `name`, `nodes` and `connections`.

The repository has no npm runtime dependencies, so there is no dependency tree to audit.
