from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field


class OnboardingState(StrEnum):
    PENDING = "pending"
    COMPLETE = "complete"


class AccountState(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class AdminOperation(StrEnum):
    ACTIVATE = "activate"
    SUSPEND = "suspend"
    CLOSE = "close"


class OrderState(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    CANCELLED = "cancelled"


class InvoiceLine(BaseModel):
    description: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    unit_amount: Decimal = Field(ge=0, decimal_places=2)


class InvoiceRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    tenant_name: str = Field(min_length=1)
    billing_email: str = Field(min_length=3)
    onboarding: OnboardingState
    account: AccountState
    order_id: str = Field(min_length=1)
    order_state: OrderState
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    lines: list[InvoiceLine] = Field(min_length=1)


class InvoiceResult(BaseModel):
    order_id: str
    total: Decimal
    document: dict[str, object]


class AccountTransitionRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    current: AccountState
    operation: AdminOperation


class AccountTransitionResult(BaseModel):
    tenant_id: str
    previous: AccountState
    current: AccountState
