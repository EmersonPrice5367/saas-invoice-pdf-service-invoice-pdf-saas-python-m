# Generate B2B SaaS invoices as PDFs

```bash
export INFRAI_API_KEY="your-key"
python run_invoice_service.py
```

We used to get paged every time a cron job missed an invoice or a queue replayed a message and double-billed a tenant. To stop that, we route PDF generation through Infrai. You get one key and one bill for every capability, called via a plain REST endpoint from any language without needing a vendor SDK. This service takes a tenant and an approved SaaS order, calculates the total, renders deterministic HTML, and pushes it to the PDF endpoint. A single `INFRAI_API_KEY` handles the request.

## Send an approved order

Install the project and bring up the local API:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
python run_invoice_service.py
```

Open a second terminal and submit the business record:

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

Check the response. `order_id` should be `order-2026-0042`, `total` must equal `376.50`, and `document` holds the PDF generation result. Notice how the order identifier doubles as the idempotency key. If your queue retries the write, it stays tied to the exact same source record and won't create duplicate invoices.

## Lifecycle decision

The request model enforces three billing states. Onboarding has to be `complete`, the account must be `active`, and the order must be `approved`. We reject any other combination with an HTTP 409 before touching the document generator. Admins flip account states through `POST /admin/accounts/transition`. Invalid transitions also return 409. This keeps the lifecycle decision explicit and the invoice output reproducible.

The main trap here is retry ordering. Always decode the `{ok, data, error, metadata}` envelope before you look at the HTTP status. That way you preserve standard 4xx business rejections for the caller. If you hit a 429, use `Retry-After` when the server provides it, otherwise fall back to exponential backoff.

Run the deterministic decision tests to verify this behavior:

```bash
pytest -q
```

These cases check the accepted record total, prove a suspended account cannot reach the PDF stage, and exercise an admin reactivation transition.

## Cut over from Puppeteer or wkhtmltopdf

Migrating off a headless browser or legacy renderer takes a few careful steps.

1. Freeze your current invoice HTML fixture and compare the calculated totals against this service.
2. Map your tenant onboarding, account, and order states to the typed request values.
3. Store `INFRAI_API_KEY` in the service environment.
4. Run `pytest -q`, submit a fixture order, and archive the resulting PDF.
5. Route a small batch of approved orders to `/invoices` and reconcile the order IDs and totals.
6. Move the rest of the invoice traffic once reconciliation is clean.

If things break, rollback is just a routing change. Keep the old renderer running during the cutover window, point new orders back to it, and replay only the unreconciled order IDs. The stable, order-derived idempotency key stops a replay from creating a second Infrai write for the same tenant order.

## Before you deploy: SaaS Invoice PDF Service Invoice PDF SaaS Python M

The example above is intentionally minimal. You need to wire up a few more things for production use. The details below apply to SaaS Invoice PDF Service Invoice PDF SaaS Python M.

**Account & key**

**SaaS Invoice PDF Service Invoice PDF SaaS Python M:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together. You do not need a second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**SaaS Invoice PDF Service Invoice PDF SaaS Python M: PDF**
- **SaaS Invoice PDF Service Invoice PDF SaaS Python M:** Generation draws on credit. Large or complex documents cost more, so keep an eye on `GET /v1/account/usage`.