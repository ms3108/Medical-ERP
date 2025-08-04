from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import redis
import json
from kafka import KafkaProducer
import os

from database import get_db, engine
from models import Base, User, Patient, Doctor, Nurse, LabTechnician, Prescription, TestOrder
from schemas import (
    UserCreate, UserResponse, PatientCreate, PatientResponse, DoctorCreate, 
    DoctorResponse, NurseCreate, NurseResponse, LabTechnicianCreate, 
    LabTechnicianResponse, PrescriptionCreate, PrescriptionResponse,
    TestOrderCreate, TestOrderResponse, Token, TokenData
)
from auth import (
    authenticate_user, create_access_token, get_current_user, 
    get_current_active_user, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Clinic ERP - Patient & Staff API", version="1.0.0")

# Get CORS origins from environment variable
allowed_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',')]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Redis connection
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Kafka producer
kafka_producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def publish_event(topic: str, event_data: dict):
    """Publish event to Kafka"""
    try:
        kafka_producer.send(topic, event_data)
        kafka_producer.flush()
    except Exception as e:
        print(f"Failed to publish to Kafka: {e}")

@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users/", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Patient endpoints
@app.post("/patients/", response_model=PatientResponse)
async def create_patient(
    patient: PatientCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_patient = Patient(**patient.dict())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    
    publish_event("patient_created", {
        "patient_id": db_patient.id,
        "name": db_patient.name,
        "created_at": datetime.now().isoformat()
    })
    
    return db_patient

@app.get("/patients/", response_model=List[PatientResponse])
async def get_patients(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    patients = db.query(Patient).offset(skip).limit(limit).all()
    return patients

@app.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient

@app.put("/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int, 
    patient: PatientCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    for key, value in patient.dict().items():
        setattr(db_patient, key, value)
    
    db.commit()
    db.refresh(db_patient)
    return db_patient

@app.delete("/patients/{patient_id}")
async def delete_patient(
    patient_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    db.delete(patient)
    db.commit()
    return {"message": "Patient deleted successfully"}

# Doctor endpoints
@app.post("/doctors/", response_model=DoctorResponse)
async def create_doctor(
    doctor: DoctorCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_doctor = Doctor(**doctor.dict())
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor

@app.get("/doctors/", response_model=List[DoctorResponse])
async def get_doctors(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    doctors = db.query(Doctor).offset(skip).limit(limit).all()
    return doctors

@app.get("/doctors/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(
    doctor_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor

# Nurse endpoints
@app.post("/nurses/", response_model=NurseResponse)
async def create_nurse(
    nurse: NurseCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_nurse = Nurse(**nurse.dict())
    db.add(db_nurse)
    db.commit()
    db.refresh(db_nurse)
    return db_nurse

@app.get("/nurses/", response_model=List[NurseResponse])
async def get_nurses(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    nurses = db.query(Nurse).offset(skip).limit(limit).all()
    return nurses

# Lab Technician endpoints
@app.post("/lab-technicians/", response_model=LabTechnicianResponse)
async def create_lab_technician(
    lab_technician: LabTechnicianCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_lab_technician = LabTechnician(**lab_technician.dict())
    db.add(db_lab_technician)
    db.commit()
    db.refresh(db_lab_technician)
    return db_lab_technician

@app.get("/lab-technicians/", response_model=List[LabTechnicianResponse])
async def get_lab_technicians(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    lab_technicians = db.query(LabTechnician).offset(skip).limit(limit).all()
    return lab_technicians

# Prescription endpoints
@app.post("/prescriptions/", response_model=PrescriptionResponse)
async def create_prescription(
    prescription: PrescriptionCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_prescription = Prescription(**prescription.dict())
    db.add(db_prescription)
    db.commit()
    db.refresh(db_prescription)
    
    publish_event("prescription_issued", {
        "prescription_id": db_prescription.id,
        "patient_id": db_prescription.patient_id,
        "doctor_id": db_prescription.doctor_id,
        "medications": db_prescription.medications,
        "issued_at": datetime.now().isoformat()
    })
    
    return db_prescription

@app.get("/prescriptions/", response_model=List[PrescriptionResponse])
async def get_prescriptions(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    prescriptions = db.query(Prescription).offset(skip).limit(limit).all()
    return prescriptions

@app.get("/prescriptions/{prescription_id}", response_model=PrescriptionResponse)
async def get_prescription(
    prescription_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if prescription is None:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return prescription

# Test Order endpoints
@app.post("/test-orders/", response_model=TestOrderResponse)
async def create_test_order(
    test_order: TestOrderCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_test_order = TestOrder(**test_order.dict())
    db.add(db_test_order)
    db.commit()
    db.refresh(db_test_order)
    
    publish_event("test_ordered", {
        "test_order_id": db_test_order.id,
        "patient_id": db_test_order.patient_id,
        "doctor_id": db_test_order.doctor_id,
        "test_type": db_test_order.test_type,
        "ordered_at": datetime.now().isoformat()
    })
    
    return db_test_order

@app.get("/test-orders/", response_model=List[TestOrderResponse])
async def get_test_orders(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    test_orders = db.query(TestOrder).offset(skip).limit(limit).all()
    return test_orders

@app.put("/test-orders/{test_order_id}/complete")
async def complete_test_order(
    test_order_id: int,
    results: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    test_order = db.query(TestOrder).filter(TestOrder.id == test_order_id).first()
    if test_order is None:
        raise HTTPException(status_code=404, detail="Test order not found")
    
    test_order.status = "completed"
    test_order.results = results
    test_order.completed_at = datetime.now()
    db.commit()
    
    publish_event("test_completed", {
        "test_order_id": test_order.id,
        "patient_id": test_order.patient_id,
        "results": results,
        "completed_at": datetime.now().isoformat()
    })
    
    return {"message": "Test order completed successfully"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "patient_api"} 