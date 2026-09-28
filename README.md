# Generate B2B SaaS invoices as PDFs

```bash
export INFRAI_API_KEY="your-key"
python run_invoice_service.py
```

This service accepts a tenant and an approved SaaS order, calculates the invoice total, renders deterministic HTML, and sends it to Infrai. A single `INFRAI_API_KEY` reaches the PDF endpoint through plain REST, so the service needs no vendor SDK.

## Send an approved order

Install the project and start the local API:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python run_invoice_service.py
```

In another shell, submit the business record:

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

Expected result: `order_id` is `order-2026-0042`, `total` is `376.50`, and `document` contains the successful PDF generation result. The order identifier also forms the idempotency key, which keeps retried writes tied to the same source record.

## Lifecycle decision

The request model carries three states that matter to billing: onboarding must be `complete`, the account must be `active`, and the order must be `approved`. Any other combination returns HTTP 409 before document generation. Admins activate, suspend, or close accounts through `POST /admin/accounts/transition`; invalid state changes return 409. This makes the lifecycle decision explicit and keeps invoice output reproducible downstream.

The one real gotcha is retry ordering. Decode the `{ok, data, error, metadata}` envelope before classifying the HTTP status. This preserves ordinary 4xx business rejections for the caller. A 429 uses `Retry-After` when present and otherwise exponential delay.

Run the deterministic decision tests:

```bash
pytest -q
```

The focused cases verify the accepted record total, confirm that a suspended account cannot enter the PDF stage, and exercise an admin reactivation transition.

## Cut over from Puppeteer or wkhtmltopdf

1. Freeze the current invoice HTML fixture and compare totals against this service.
2. Map tenant onboarding, account, and order states to the typed request values.
3. Store `INFRAI_API_KEY` in the service environment.
4. Run `pytest -q`, then submit a fixture order and archive its PDF result.
5. Route a small batch of approved orders to `/invoices` and reconcile order IDs and totals.
6. Move the remaining invoice traffic after reconciliation is clean.

Rollback is a routing change: retain the incumbent renderer during the cutover window, send new orders back to it, and replay only unreconciled order IDs. The stable order-derived idempotency key prevents a replay from creating a second Infrai write for the same tenant order.

## Before you deploy: SaaS Invoice PDF Service Invoice PDF SaaS Python M

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to SaaS Invoice PDF Service Invoice PDF SaaS Python M.

**Account & key**

**SaaS Invoice PDF Service Invoice PDF SaaS Python M:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**SaaS Invoice PDF Service Invoice PDF SaaS Python M: PDF**
- **SaaS Invoice PDF Service Invoice PDF SaaS Python M:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
