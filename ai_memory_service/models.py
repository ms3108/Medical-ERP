from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from database import Base

class PrescriptionHistory(Base):
    __tablename__ = "prescription_history"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, index=True)
    prescription_id = Column(Integer, index=True)
    symptoms = Column(Text)
    medications = Column(JSON)
    effectiveness_score = Column(Integer)  # 1-10 scale
    side_effects = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SymptomVector(Base):
    __tablename__ = "symptom_vectors"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, index=True)
    symptoms = Column(Text)  # Comma-separated symptoms
    symptom_vector = Column(JSON)  # Numerical vector representation
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 