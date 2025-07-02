from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    username: str
    email: str
    role: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Patient schemas
class PatientBase(BaseModel):
    name: str
    date_of_birth: datetime
    gender: str
    phone: str
    email: str
    address: str
    emergency_contact: str
    medical_history: Optional[str] = None
    allergies: Optional[str] = None

class PatientCreate(PatientBase):
    pass

class PatientResponse(PatientBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Doctor schemas
class DoctorBase(BaseModel):
    name: str
    specialization: str
    license_number: str
    phone: str
    email: str

class DoctorCreate(DoctorBase):
    pass

class DoctorResponse(DoctorBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Nurse schemas
class NurseBase(BaseModel):
    name: str
    license_number: str
    phone: str
    email: str
    department: str

class NurseCreate(NurseBase):
    pass

class NurseResponse(NurseBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Lab Technician schemas
class LabTechnicianBase(BaseModel):
    name: str
    license_number: str
    phone: str
    email: str
    specialization: str

class LabTechnicianCreate(LabTechnicianBase):
    pass

class LabTechnicianResponse(LabTechnicianBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Prescription schemas
class PrescriptionBase(BaseModel):
    patient_id: int
    doctor_id: int
    medications: List[Dict[str, Any]]
    diagnosis: str
    instructions: str
    expiry_date: Optional[datetime] = None

class PrescriptionCreate(PrescriptionBase):
    pass

class PrescriptionResponse(PrescriptionBase):
    id: int
    issued_date: datetime
    is_active: bool

    class Config:
        from_attributes = True

# Test Order schemas
class TestOrderBase(BaseModel):
    patient_id: int
    doctor_id: int
    test_type: str
    test_details: str

class TestOrderCreate(TestOrderBase):
    pass

class TestOrderResponse(TestOrderBase):
    id: int
    status: str
    ordered_date: datetime
    completed_at: Optional[datetime] = None
    results: Optional[str] = None
    attachments: Optional[List[str]] = None

    class Config:
        from_attributes = True

# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None 