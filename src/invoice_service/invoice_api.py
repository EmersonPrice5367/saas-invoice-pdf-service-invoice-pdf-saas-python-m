from decimal import Decimal
from html import escape

from fastapi import FastAPI, HTTPException

from .infrai_pdf import InfraiError, InfraiPdfClient
from .invoice_models import (
    AccountState,
    AccountTransitionRequest,
    AccountTransitionResult,
    AdminOperation,
    InvoiceRequest,
    InvoiceResult,
    OnboardingState,
    OrderState,
)

service = FastAPI(title="SaaS invoice PDF service")


def invoice_total(request: InvoiceRequest) -> Decimal:
    return sum((line.unit_amount * line.quantity for line in request.lines), Decimal("0.00"))


def require_billable_order(request: InvoiceRequest) -> None:
    if request.onboarding is not OnboardingState.COMPLETE:
        raise HTTPException(status_code=409, detail="Tenant onboarding is not complete")
    if request.account is not AccountState.ACTIVE:
        raise HTTPException(status_code=409, detail="Tenant account is not active")
    if request.order_state is not OrderState.APPROVED:
        raise HTTPException(status_code=409, detail="Order is not approved")


def apply_admin_operation(current: AccountState, operation: AdminOperation) -> AccountState:
    transitions = {
        (AccountState.SUSPENDED, AdminOperation.ACTIVATE): AccountState.ACTIVE,
        (AccountState.ACTIVE, AdminOperation.SUSPEND): AccountState.SUSPENDED,
        (AccountState.ACTIVE, AdminOperation.CLOSE): AccountState.CLOSED,
        (AccountState.SUSPENDED, AdminOperation.CLOSE): AccountState.CLOSED,
    }
    next_state = transitions.get((current, operation))
    if next_state is None:
        raise HTTPException(status_code=409, detail="Account operation is invalid for the current state")
    return next_state


def render_invoice(request: InvoiceRequest, total: Decimal) -> str:
    rows = "".join(
        f"<tr><td>{escape(line.description)}</td><td>{line.quantity}</td>"
        f"<td>{line.unit_amount:.2f}</td><td>{line.quantity * line.unit_amount:.2f}</td></tr>"
        for line in request.lines
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><style>"
        "body{font-family:Arial,sans-serif;margin:40px}table{width:100%;border-collapse:collapse}"
        "th,td{padding:8px;border-bottom:1px solid #ddd;text-align:left}</style></head><body>"
        f"<h1>Invoice {escape(request.order_id)}</h1><p>{escape(request.tenant_name)}</p>"
        f"<p>{escape(request.billing_email)}</p><table><thead><tr><th>Item</th><th>Qty</th>"
        f"<th>Unit</th><th>Amount</th></tr></thead><tbody>{rows}</tbody></table>"
        f"<h2>Total {escape(request.currency)} {total:.2f}</h2></body></html>"
    )


@service.post("/invoices", response_model=InvoiceResult)
def create_invoice(request: InvoiceRequest) -> InvoiceResult:
    require_billable_order(request)
    total = invoice_total(request)
    try:
        document = InfraiPdfClient().generate(
            render_invoice(request, total),
            idempotency_key=f"invoice:{request.tenant_id}:{request.order_id}",
        )
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail={"code": exc.code, "error": exc.detail}) from exc
    return InvoiceResult(order_id=request.order_id, total=total, document=document)


@service.post("/admin/accounts/transition", response_model=AccountTransitionResult)
def transition_account(request: AccountTransitionRequest) -> AccountTransitionResult:
    return AccountTransitionResult(
        tenant_id=request.tenant_id,
        previous=request.current,
        current=apply_admin_operation(request.current, request.operation),
    )
