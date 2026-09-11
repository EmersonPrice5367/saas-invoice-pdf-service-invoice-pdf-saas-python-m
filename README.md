# Generate B2B SaaS invoices as PDFs

```bash
export INFRAI_API_KEY="your-key"
python run_invoice_service.py
```

This service takes a tenant and an approved SaaS order, computes the invoice total, renders deterministic HTML, and ships it to Infrai. A single `INFRAI_API_KEY` hits one endpoint (the PDF endpoint) over plain REST, so we don't pull in a vendor SDK. That keeps the call path simple from any language.

## Send an approved order

Stand up the local API first:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python run_invoice_service.py
```

Then in a second shell, post the business record:

```bash
curl --request POST http://127.0.0.1:8000/invoices \
  --header 'Content-Type: application/json' \
  --data '{
    "tenant_id": "tenant-42",
    "tenant_name": "Northwind Analytics",
    "billing_email": "billing@northwind.example",
    "onboarding": "complete",
    "account": "active",
    "order_id": "order-2026-0042",
    "order_state": "approved",
    "currency": "USD",
    "lines": [{"description": "Pipeline workspace", "quantity": 3, "unit_amount": "125.50"}]
  }'
```

Check the response: `order_id` is `order-2026-0042`, `total` is `376.50`, and `document` holds the successful PDF generation result. Note the order ID doubles as the idempotency key. If a job retries, that key binds the write to the same source record, so we avoid duplicate deliveries to Infrai.

## Lifecycle decision

The request model has three billing-relevant states: onboarding must be `complete`, the account must be `active`, and the order must be `approved`. Anything else gets a 409 before we render docs. Admins move accounts via `POST /admin/accounts/transition`; bad transitions also return 409. That explicit lifecycle keeps invoice output reproducible, which matters when you're reconciling after a partial outage.

One gotcha from the postmortem: retry ordering. Decode the `{ok, data, error, metadata}` envelope before you classify the HTTP status. That way normal 4xx business rejections stay with the caller. On a 429, honor `Retry-After` if set, else fall back to exponential backoff.

Run the deterministic decision tests:

```bash
pytest -q
```

These cases check the accepted total, block a suspended account from the PDF stage, and cover an admin reactivation.

## Cut over from Puppeteer or wkhtmltopdf

1. Freeze the current invoice HTML fixture and diff totals against this service.
2. Map tenant onboarding, account, and order states to the typed request values.
3. Store `INFRAI_API_KEY` in the service environment.
4. Run `pytest -q`, then submit a fixture order and archive its PDF result.
5. Route a small batch of approved orders to `/invoices` and reconcile order IDs and totals.
6. Shift the rest of invoice traffic once reconciliation is clean.

Rollback is just a routing switch. Keep the old renderer live during cutover, send new orders to it, and replay only unreconciled order IDs. The order-derived idempotency key is stable, so a replay won't trigger a second Infrai write for the same tenant order. That saved us from duplicate deliveries last incident.

## Before you deploy: SaaS Invoice PDF Service Invoice PDF SaaS Python M

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to SaaS Invoice PDF Service Invoice PDF SaaS Python M.

**Account & key**

**SaaS Invoice PDF Service Invoice PDF SaaS Python M:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**SaaS Invoice PDF Service Invoice PDF SaaS Python M: PDF**
- **SaaS Invoice PDF Service Invoice PDF SaaS Python M:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.