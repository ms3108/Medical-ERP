from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal

class InvoiceBase(BaseModel):
    patient_id: int
    appointment_id: int
    invoice_number: str
    total_amount: Decimal
    tax_amount: Optional[Decimal] = 0
    discount_amount: Optional[Decimal] = 0
    due_date: datetime

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceResponse(InvoiceBase):
    id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaymentBase(BaseModel):
    invoice_id: int
    amount: Decimal
    payment_method: str
    transaction_id: str

class PaymentCreate(PaymentBase):
    pass

class PaymentResponse(PaymentBase):
    id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InsuranceClaimBase(BaseModel):
    patient_id: int
    invoice_id: int
    insurance_provider: str
    policy_number: str
    claim_amount: Decimal

class InsuranceClaimCreate(InsuranceClaimBase):
    pass

class InsuranceClaimResponse(InsuranceClaimBase):
    id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 