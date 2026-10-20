# Persian n8n Automation Pack

Six production-ready [n8n](https://n8n.io) workflows for the day-to-day operations of Iranian small businesses: WooCommerce stores, accounting, CRM, SMS and uptime monitoring.

[![validate](https://github.com/sirdadfar/n8n-persian-pack/actions/workflows/validate.yml/badge.svg)](https://github.com/sirdadfar/n8n-persian-pack/actions/workflows/validate.yml)

🇮🇷 [توضیحات فارسی](README.fa.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)

## Workflows

| File | What it does | Services |
|---|---|---|
| `01-woocommerce-order-to-accounting.json` | New WooCommerce order → create invoice in accounting → SMS confirmation → Telegram alert on failure | WooCommerce, accounting API, Kavenegar, Telegram |
| `02-abandoned-cart-reminder.json` | Finds `pending` orders and sends at most one SMS reminder (flags the order afterwards) | WooCommerce, Kavenegar |
| `03-daily-sales-report.json` | Every night at 21:00 sends revenue, AOV and top products to Telegram | WooCommerce, Telegram |
| `04-lead-to-crm.json` | Website form lead → mobile validation → CRM insert → instant sales notification | CRM, Telegram |
| `05-invoice-ocr-to-accounting.json` | Invoice photo → OCR → amount/date/number extraction → database → Telegram summary | OCR, Postgres, Telegram |
| `06-site-uptime-alert.json` | Pings a URL every 5 minutes and alerts only after a confirming second check | Telegram |

Everything is idempotent-ish by design: workflow 02 tags orders so a customer is never spammed, and workflow 06 re-checks before alerting so a 3-second restart does not page anyone.

## Quick start

```bash
docker compose up -d          # n8n on http://localhost:5678
cp env.example .env           # then fill in real values
n8n import:workflow --input=workflows/01-woocommerce-order-to-accounting.json
```

Workflows import **inactive** and without credentials — by design. Create the credentials in the n8n UI, attach them, then activate.

Workflows 04 (`lead`) and 05 (`invoice-scan`) expose a webhook and ship with `authentication: basicAuth`. Before they can accept requests, create a **Basic Auth** credential named exactly `Webhook Basic Auth (n8n Persian Pack)` with a long random password and assign it to the webhook node. If n8n says "credential not found", the name does not match. The webhook path is public in this repository, so path secrecy is not a security control — the password is.

## Validate

```bash
npm run validate      # structural checks + webhook auth + secret scan (no n8n needed)
npm run test:import   # ایمپورت واقعی در یک نمونهٔ موقت n8n (نیازمند نصب n8n)

`validate` fails when a webhook node has no authentication or no attached credential, when a
`responseNode` webhook lacks a `respondToWebhook` node, when a node parameter contains something that
looks like a literal secret, or when a `credentials` object carries `data`/`value`.
```

`validate` checks JSON validity, unique UUIDs, known node types, dangling connections, orphan nodes and that no workflow ships pre-activated — this runs in CI on every push. `test:import` imports all workflows into a throwaway n8n instance and asserts they land in the database, which is the only way to catch importer-level schema issues (for example, n8n's CLI rejects duplicate tag names across workflows).

## Environment variables

See [`env.example`](env.example). No secrets are stored in this repository; every value is read through `{{ $env.NAME }}`.

## Regenerating the JSON files

```bash
python3 scripts/build_workflows.py
```

If you edit a workflow in the n8n UI, mirror the change in `scripts/build_workflows.py` so the next build does not overwrite it.

## License

MIT — free for commercial use. See [LICENSE](LICENSE).
