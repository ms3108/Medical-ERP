from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)  # admin, doctor, nurse, lab_technician
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    date_of_birth = Column(DateTime)
    gender = Column(String)
    phone = Column(String)
    email = Column(String)
    address = Column(Text)
    emergency_contact = Column(String)
    medical_history = Column(Text)
    allergies = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    prescriptions = relationship("Prescription", back_populates="patient")
    test_orders = relationship("TestOrder", back_populates="patient")

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    specialization = Column(String)
    license_number = Column(String, unique=True)
    phone = Column(String)
    email = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    prescriptions = relationship("Prescription", back_populates="doctor")
    test_orders = relationship("TestOrder", back_populates="doctor")

class Nurse(Base):
    __tablename__ = "nurses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    license_number = Column(String, unique=True)
    phone = Column(String)
    email = Column(String)
    department = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class LabTechnician(Base):
    __tablename__ = "lab_technicians"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    license_number = Column(String, unique=True)
    phone = Column(String)
    email = Column(String)
    specialization = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    medications = Column(JSON)  # List of medications with dosage, frequency, etc.
    diagnosis = Column(Text)
    instructions = Column(Text)
    issued_date = Column(DateTime(timezone=True), server_default=func.now())
    expiry_date = Column(DateTime)
    is_active = Column(Boolean, default=True)

    patient = relationship("Patient", back_populates="prescriptions")
    doctor = relationship("Doctor", back_populates="prescriptions")

class TestOrder(Base):
    __tablename__ = "test_orders"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    test_type = Column(String)
    test_details = Column(Text)
    status = Column(String, default="ordered")  # ordered, in_progress, completed, cancelled
    ordered_date = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime)
    results = Column(Text)
    attachments = Column(JSON)  # List of file paths/URLs

    patient = relationship("Patient", back_populates="test_orders")
    doctor = relationship("Doctor", back_populates="test_orders")

class PrescriptionHistory(Base):
    __tablename__ = "prescription_history"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"))
    symptoms = Column(Text)
    medications = Column(JSON)
    effectiveness_score = Column(Integer)  # 1-10 scale
    side_effects = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 