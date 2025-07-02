from fastapi import FastAPI, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from kafka import KafkaProducer
import os
import uuid

from database import get_db, engine
from models import Base, Invoice, Payment, InsuranceClaim
from schemas import (
    InvoiceCreate, InvoiceResponse, PaymentCreate, PaymentResponse,
    InsuranceClaimCreate, InsuranceClaimResponse
)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Clinic ERP - Billing Service", version="1.0.0")

# Kafka producer
kafka_producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def publish_event(topic: str, event_data: dict):
    """Publish event to Kafka"""
    try:
        kafka_producer.send(topic, event_data)
        kafka_producer.flush()
    except Exception as e:
        print(f"Failed to publish to Kafka: {e}")

def get_idempotency_key(x_idempotency_key: Optional[str] = Header(None)):
    """Get idempotency key from header"""
    return x_idempotency_key

@app.post("/invoices/", response_model=InvoiceResponse)
async def create_invoice(
    invoice: InvoiceCreate, 
    db: Session = Depends(get_db),
    idempotency_key: str = Depends(get_idempotency_key)
):
    """Create invoice with idempotency support"""
    
    # Check for existing invoice with same idempotency key
    if idempotency_key:
        existing_invoice = db.query(Invoice).filter(
            Invoice.idempotency_key == idempotency_key
        ).first()
        if existing_invoice:
            return existing_invoice
    
    # Create new invoice
    db_invoice = Invoice(**invoice.dict())
    if idempotency_key:
        db_invoice.idempotency_key = idempotency_key
    
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    
    # Publish event
    publish_event("invoice_created", {
        "invoice_id": db_invoice.id,
        "patient_id": db_invoice.patient_id,
        "amount": float(db_invoice.total_amount),
        "created_at": db_invoice.created_at.isoformat()
    })
    
    return db_invoice

@app.get("/invoices/", response_model=List[InvoiceResponse])
async def get_invoices(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Get all invoices"""
    invoices = db.query(Invoice).offset(skip).limit(limit).all()
    return invoices

@app.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Get specific invoice"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@app.put("/invoices/{invoice_id}/status")
async def update_invoice_status(
    invoice_id: int, 
    status: str, 
    db: Session = Depends(get_db)
):
    """Update invoice status"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice.status = status
    db.commit()
    
    # Publish status change event
    publish_event("invoice_status_changed", {
        "invoice_id": invoice.id,
        "new_status": status,
        "updated_at": invoice.updated_at.isoformat()
    })
    
    return {"message": "Invoice status updated successfully"}

@app.post("/payments/", response_model=PaymentResponse)
async def create_payment(
    payment: PaymentCreate, 
    db: Session = Depends(get_db),
    idempotency_key: str = Depends(get_idempotency_key)
):
    """Create payment with idempotency support"""
    
    # Check for existing payment with same idempotency key
    if idempotency_key:
        existing_payment = db.query(Payment).filter(
            Payment.idempotency_key == idempotency_key
        ).first()
        if existing_payment:
            return existing_payment
    
    # Create new payment
    db_payment = Payment(**payment.dict())
    if idempotency_key:
        db_payment.idempotency_key = idempotency_key
    
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    # Update invoice status if payment is successful
    if db_payment.status == "completed":
        invoice = db.query(Invoice).filter(Invoice.id == db_payment.invoice_id).first()
        if invoice:
            invoice.status = "paid"
            db.commit()
    
    # Publish event
    publish_event("payment_processed", {
        "payment_id": db_payment.id,
        "invoice_id": db_payment.invoice_id,
        "amount": float(db_payment.amount),
        "status": db_payment.status,
        "created_at": db_payment.created_at.isoformat()
    })
    
    return db_payment

@app.get("/payments/", response_model=List[PaymentResponse])
async def get_payments(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Get all payments"""
    payments = db.query(Payment).offset(skip).limit(limit).all()
    return payments

@app.post("/insurance-claims/", response_model=InsuranceClaimResponse)
async def create_insurance_claim(
    claim: InsuranceClaimCreate, 
    db: Session = Depends(get_db),
    idempotency_key: str = Depends(get_idempotency_key)
):
    """Create insurance claim with idempotency support"""
    
    # Check for existing claim with same idempotency key
    if idempotency_key:
        existing_claim = db.query(InsuranceClaim).filter(
            InsuranceClaim.idempotency_key == idempotency_key
        ).first()
        if existing_claim:
            return existing_claim
    
    # Create new claim
    db_claim = InsuranceClaim(**claim.dict())
    if idempotency_key:
        db_claim.idempotency_key = idempotency_key
    
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)
    
    # Publish event
    publish_event("insurance_claim_created", {
        "claim_id": db_claim.id,
        "patient_id": db_claim.patient_id,
        "invoice_id": db_claim.invoice_id,
        "amount": float(db_claim.claim_amount),
        "created_at": db_claim.created_at.isoformat()
    })
    
    return db_claim

@app.get("/insurance-claims/", response_model=List[InsuranceClaimResponse])
async def get_insurance_claims(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """Get all insurance claims"""
    claims = db.query(InsuranceClaim).offset(skip).limit(limit).all()
    return claims

@app.put("/insurance-claims/{claim_id}/status")
async def update_claim_status(
    claim_id: int, 
    status: str, 
    db: Session = Depends(get_db)
):
    """Update insurance claim status"""
    claim = db.query(InsuranceClaim).filter(InsuranceClaim.id == claim_id).first()
    if claim is None:
        raise HTTPException(status_code=404, detail="Insurance claim not found")
    
    claim.status = status
    db.commit()
    
    # Publish status change event
    publish_event("insurance_claim_status_changed", {
        "claim_id": claim.id,
        "new_status": status,
        "updated_at": claim.updated_at.isoformat()
    })
    
    return {"message": "Insurance claim status updated successfully"}

@app.get("/analytics/revenue")
async def get_revenue_analytics(db: Session = Depends(get_db)):
    """Get revenue analytics"""
    
    # Calculate total revenue
    total_revenue = db.query(Invoice).filter(Invoice.status == "paid").with_entities(
        db.func.sum(Invoice.total_amount)
    ).scalar() or 0
    
    # Calculate pending payments
    pending_amount = db.query(Invoice).filter(Invoice.status == "pending").with_entities(
        db.func.sum(Invoice.total_amount)
    ).scalar() or 0
    
    # Get payment method distribution
    payment_methods = db.query(Payment.payment_method, db.func.count(Payment.id)).group_by(
        Payment.payment_method
    ).all()
    
    return {
        "total_revenue": float(total_revenue),
        "pending_amount": float(pending_amount),
        "payment_methods": [{"method": method, "count": count} for method, count in payment_methods],
        "total_invoices": db.query(Invoice).count(),
        "total_payments": db.query(Payment).count()
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "billing_service"} 