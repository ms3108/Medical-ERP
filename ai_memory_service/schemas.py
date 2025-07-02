from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class PrescriptionHistoryBase(BaseModel):
    patient_id: int
    prescription_id: int
    symptoms: str
    medications: List[Dict[str, Any]]
    effectiveness_score: int
    side_effects: Optional[str] = None

class PrescriptionHistoryCreate(PrescriptionHistoryBase):
    pass

class PrescriptionHistoryResponse(PrescriptionHistoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class SymptomVectorBase(BaseModel):
    patient_id: int
    symptoms: str
    symptom_vector: Optional[List[float]] = None

class SymptomVectorCreate(SymptomVectorBase):
    pass

class SymptomVectorResponse(SymptomVectorBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PrescriptionSuggestion(BaseModel):
    patient_id: int
    current_symptoms: str
    similar_prescriptions: List[Dict[str, Any]]
    recommended_medications: List[Dict[str, Any]]
    confidence_score: float

class TestSuggestion(BaseModel):
    patient_id: int
    symptoms: str
    suggested_tests: List[Dict[str, Any]]
    confidence_score: float 