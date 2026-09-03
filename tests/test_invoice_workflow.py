from decimal import Decimal

import pytest
from fastapi import HTTPException

from invoice_service.invoice_api import apply_admin_operation, invoice_total, require_billable_order
from invoice_service.invoice_models import AccountState, AdminOperation, InvoiceRequest


def order(**changes: str) -> InvoiceRequest:
    payload = {
        "tenant_id": "tenant-42",
        "tenant_name": "Northwind Analytics",
        "billing_email": "billing@northwind.example",
        "onboarding": "complete",
        "account": "active",
        "order_id": "order-2026-0042",
        "order_state": "approved",
        "currency": "USD",
        "lines": [{"description": "Pipeline workspace", "quantity": 3, "unit_amount": "125.50"}],
    }
    payload.update(changes)
    return InvoiceRequest.model_validate(payload)


def test_approved_active_tenant_is_billable() -> None:
    request = order()
    require_billable_order(request)
    assert invoice_total(request) == Decimal("376.50")


def test_suspended_tenant_is_rejected_before_pdf_generation() -> None:
    with pytest.raises(HTTPException) as rejected:
        require_billable_order(order(account="suspended"))
    assert rejected.value.status_code == 409


def test_admin_reactivation_changes_invoice_eligibility() -> None:
    state = apply_admin_operation(AccountState.SUSPENDED, AdminOperation.ACTIVATE)
    request = order(account=state.value)
    require_billable_order(request)
    assert state is AccountState.ACTIVE
