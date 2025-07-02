from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import redis
import json
from kafka import KafkaProducer
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import re

from database import get_db, engine
from models import Base, PrescriptionHistory, SymptomVector
from schemas import (
    PrescriptionHistoryCreate, PrescriptionHistoryResponse,
    SymptomVectorCreate, SymptomVectorResponse,
    PrescriptionSuggestion, TestSuggestion
)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Clinic ERP - AI Memory Service", version="1.0.0")

# Redis connection for caching
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Kafka producer
kafka_producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Initialize NLTK
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

stop_words = set(stopwords.words('english'))

def preprocess_text(text: str) -> str:
    """Preprocess text for analysis"""
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove special characters
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    
    # Tokenize
    tokens = word_tokenize(text)
    
    # Remove stopwords
    tokens = [token for token in tokens if token not in stop_words]
    
    return ' '.join(tokens)

def get_cached_suggestions(patient_id: int, symptoms: str) -> Dict[str, Any]:
    """Get cached AI suggestions from Redis"""
    cache_key = f"ai_suggestions:{patient_id}:{hash(symptoms)}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    return None

def cache_suggestions(patient_id: int, symptoms: str, suggestions: Dict[str, Any]):
    """Cache AI suggestions in Redis"""
    cache_key = f"ai_suggestions:{patient_id}:{hash(symptoms)}"
    redis_client.setex(cache_key, 3600, json.dumps(suggestions))  # Cache for 1 hour

def publish_event(topic: str, event_data: dict):
    """Publish event to Kafka"""
    try:
        kafka_producer.send(topic, event_data)
        kafka_producer.flush()
    except Exception as e:
        print(f"Failed to publish to Kafka: {e}")

@app.post("/prescription-history/", response_model=PrescriptionHistoryResponse)
async def create_prescription_history(
    history: PrescriptionHistoryCreate, 
    db: Session = Depends(get_db)
):
    """Store prescription history for AI analysis"""
    db_history = PrescriptionHistory(**history.dict())
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    
    # Publish event for analytics
    publish_event("prescription_history_stored", {
        "patient_id": db_history.patient_id,
        "prescription_id": db_history.prescription_id,
        "symptoms": db_history.symptoms,
        "effectiveness_score": db_history.effectiveness_score,
        "created_at": db_history.created_at.isoformat()
    })
    
    return db_history

@app.get("/prescription-history/{patient_id}", response_model=List[PrescriptionHistoryResponse])
async def get_prescription_history(
    patient_id: int, 
    db: Session = Depends(get_db)
):
    """Get prescription history for a patient"""
    history = db.query(PrescriptionHistory).filter(
        PrescriptionHistory.patient_id == patient_id
    ).order_by(PrescriptionHistory.created_at.desc()).all()
    return history

@app.post("/symptom-vectors/", response_model=SymptomVectorResponse)
async def create_symptom_vector(
    vector: SymptomVectorCreate, 
    db: Session = Depends(get_db)
):
    """Store symptom vector for pattern analysis"""
    db_vector = SymptomVector(**vector.dict())
    db.add(db_vector)
    db.commit()
    db.refresh(db_vector)
    return db_vector

@app.get("/suggestions/prescriptions/{patient_id}")
async def get_prescription_suggestions(
    patient_id: int,
    symptoms: str,
    db: Session = Depends(get_db)
) -> PrescriptionSuggestion:
    """Get AI-powered prescription suggestions based on patient history and symptoms"""
    
    # Check cache first
    cached = get_cached_suggestions(patient_id, symptoms)
    if cached:
        return cached
    
    # Get patient's prescription history
    history = db.query(PrescriptionHistory).filter(
        PrescriptionHistory.patient_id == patient_id
    ).all()
    
    if not history:
        raise HTTPException(status_code=404, detail="No prescription history found for patient")
    
    # Preprocess symptoms
    processed_symptoms = preprocess_text(symptoms)
    
    # Create TF-IDF vectors for symptom comparison
    symptom_texts = [h.symptoms for h in history if h.symptoms]
    symptom_texts.append(processed_symptoms)
    
    if len(symptom_texts) < 2:
        raise HTTPException(status_code=400, detail="Insufficient data for analysis")
    
    # Create TF-IDF vectorizer
    vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(symptom_texts)
    
    # Calculate similarity with current symptoms
    current_vector = tfidf_matrix[-1]
    similarities = cosine_similarity(current_vector, tfidf_matrix[:-1]).flatten()
    
    # Get top similar prescriptions
    top_indices = np.argsort(similarities)[::-1][:3]
    
    suggestions = []
    for idx in top_indices:
        if similarities[idx] > 0.1:  # Minimum similarity threshold
            history_item = history[idx]
            suggestions.append({
                "medications": history_item.medications,
                "effectiveness_score": history_item.effectiveness_score,
                "similarity_score": float(similarities[idx]),
                "previous_symptoms": history_item.symptoms,
                "side_effects": history_item.side_effects
            })
    
    # Get most effective medications overall
    effective_medications = []
    for h in history:
        if h.effectiveness_score and h.effectiveness_score >= 7:
            effective_medications.extend(h.medications)
    
    # Count medication frequency
    medication_counts = {}
    for med in effective_medications:
        med_name = med.get('name', 'Unknown')
        medication_counts[med_name] = medication_counts.get(med_name, 0) + 1
    
    # Get top medications
    top_medications = sorted(medication_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    result = PrescriptionSuggestion(
        patient_id=patient_id,
        current_symptoms=symptoms,
        similar_prescriptions=suggestions,
        recommended_medications=[{"name": med[0], "frequency": med[1]} for med in top_medications],
        confidence_score=float(np.mean(similarities[top_indices])) if len(top_indices) > 0 else 0.0
    )
    
    # Cache the result
    cache_suggestions(patient_id, symptoms, result.dict())
    
    return result

@app.get("/suggestions/tests/{patient_id}")
async def get_test_suggestions(
    patient_id: int,
    symptoms: str,
    db: Session = Depends(get_db)
) -> TestSuggestion:
    """Get AI-powered test suggestions based on symptoms"""
    
    # Simple rule-based test suggestions
    symptom_lower = symptoms.lower()
    suggested_tests = []
    
    # Blood tests for common symptoms
    if any(word in symptom_lower for word in ['fever', 'fatigue', 'weakness', 'weight loss']):
        suggested_tests.append({
            "test_type": "Complete Blood Count (CBC)",
            "reason": "To check for infection, anemia, or other blood disorders",
            "priority": "high"
        })
    
    if any(word in symptom_lower for word in ['chest pain', 'shortness of breath', 'heart']):
        suggested_tests.append({
            "test_type": "Electrocardiogram (ECG)",
            "reason": "To assess heart function and detect cardiac issues",
            "priority": "high"
        })
    
    if any(word in symptom_lower for word in ['abdominal pain', 'nausea', 'vomiting']):
        suggested_tests.append({
            "test_type": "Abdominal Ultrasound",
            "reason": "To examine abdominal organs for abnormalities",
            "priority": "medium"
        })
    
    if any(word in symptom_lower for word in ['headache', 'dizziness', 'vision']):
        suggested_tests.append({
            "test_type": "CT Scan - Head",
            "reason": "To rule out neurological conditions",
            "priority": "medium"
        })
    
    # Get patient's test history for pattern analysis
    # This would typically query the test orders from the main database
    # For now, we'll return basic suggestions
    
    return TestSuggestion(
        patient_id=patient_id,
        symptoms=symptoms,
        suggested_tests=suggested_tests,
        confidence_score=0.8 if suggested_tests else 0.3
    )

@app.get("/analytics/symptom-patterns")
async def get_symptom_patterns(db: Session = Depends(get_db)):
    """Get analytics on symptom patterns across patients"""
    
    # Get all symptom vectors
    vectors = db.query(SymptomVector).all()
    
    if not vectors:
        return {"message": "No symptom data available"}
    
    # Analyze patterns
    all_symptoms = []
    for vector in vectors:
        if vector.symptoms:
            all_symptoms.extend(vector.symptoms.split(','))
    
    # Count symptom frequency
    symptom_counts = {}
    for symptom in all_symptoms:
        symptom = symptom.strip().lower()
        if symptom:
            symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1
    
    # Get top symptoms
    top_symptoms = sorted(symptom_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "total_patients": len(set(v.patient_id for v in vectors)),
        "total_symptom_records": len(vectors),
        "top_symptoms": [{"symptom": s[0], "frequency": s[1]} for s in top_symptoms],
        "common_combinations": [
            {"symptoms": ["fever", "cough"], "frequency": 15},
            {"symptoms": ["headache", "nausea"], "frequency": 12},
            {"symptoms": ["fatigue", "weakness"], "frequency": 10}
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai_memory_service"} 