from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, Boolean, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, index=True)
    appointment_id = Column(Integer, index=True)
    invoice_number = Column(String, unique=True, index=True)
    total_amount = Column(Numeric(10, 2))
    tax_amount = Column(Numeric(10, 2), default=0)
    discount_amount = Column(Numeric(10, 2), default=0)
    status = Column(String, default="pending")  # pending, paid, cancelled
    due_date = Column(DateTime)
    idempotency_key = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    amount = Column(Numeric(10, 2))
    payment_method = Column(String)  # cash, credit_card, debit_card, insurance
    transaction_id = Column(String, unique=True, index=True)
    status = Column(String, default="pending")  # pending, completed, failed, refunded
    idempotency_key = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class InsuranceClaim(Base):
    __tablename__ = "insurance_claims"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    insurance_provider = Column(String)
    policy_number = Column(String)
    claim_amount = Column(Numeric(10, 2))
    status = Column(String, default="submitted")  # submitted, approved, rejected, paid
    idempotency_key = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 