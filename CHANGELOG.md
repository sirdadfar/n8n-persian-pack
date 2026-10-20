# Changelog

All notable changes to `n8n-persian-pack` are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.1.0] - 2026-10-21

### Added

- `SECURITY.md`: threat model, webhook authentication, `$env` access trade-off, third-party data
  flows, execution-data retention and the remaining gaps.
- `docs/credentials-fa.md` section 7: how to create and attach the webhook Basic Auth credential,
  with a `curl -u` example.
- Validator rules: every webhook node must declare authentication (not `none`) and must have a
  credential attached; a `responseNode` webhook must have a `respondToWebhook` node.
- Validator secret scan: fails on literal OpenAI/GitHub/Slack/AWS keys, Telegram bot tokens, JWTs,
  private keys and hard-coded Bearer tokens, and on `credentials` objects that carry `data`/`value`.

### Changed

- **Breaking for imports:** workflows 04 (lead) and 05 (invoice scan) now require Basic Auth on their
  webhook nodes. After import, create the `Webhook Basic Auth (n8n Persian Pack)` credential and
  assign it; the workflow will not accept unauthenticated requests.
- `scripts/build_workflows.py` emits the same authentication and credential reference, so
  regenerating the JSON keeps the hardening.
- `docker-compose.yml` binds port 5678 to `127.0.0.1` instead of all interfaces, documents pinning
  the image instead of `latest`, and explains the `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` trade-off.
- README (both languages) documents the webhook credential step and the stricter validation.

### Notes

- Workflow structure, node names and the other four workflows are unchanged.
