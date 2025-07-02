# 🧠 AI-Enhanced Clinic ERP System

A comprehensive, **microservices-based clinic management system** with **AI-powered features**, **real-time event streaming**, and **advanced analytics**.

---

## 🏥 System Overview

This Clinic ERP system consists of multiple microservices working together to provide a complete healthcare management solution:

### Core Services

#### 1. Patient & Staff API (FastAPI) — Port `8000`

- CRUD operations for patients, doctors, nurses, lab technicians
- JWT-based authentication with role-based access control
- Prescription and test order management
- Event streaming to Kafka

#### 2. Scheduling Service (Django REST Framework) — Port `8001`

- Appointment management with Redis slot locking
- Google Calendar integration
- Real-time availability checking
- Double-booking prevention

#### 3. AI Memory Service (FastAPI) — Port `8002`

- Prescription history analysis using TF-IDF and cosine similarity
- AI-powered medication suggestions
- Symptom pattern recognition
- Test recommendation engine

#### 4. Billing Service (FastAPI) — Port `8003`

- Invoice and payment management
- Insurance claim processing
- Idempotent endpoints for financial transactions
- Revenue analytics

---

## 🧱 Infrastructure

- **PostgreSQL** - Primary database  
- **Redis** - Caching and slot locking  
- **Kafka** - Event streaming  
- **Airflow** - ETL pipeline for analytics  
- **Prometheus + Grafana** - Monitoring and observability  

---

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- At least **8GB RAM**
- Ports `8000–8003`, `8080`, `3000`, `9090` available

---

## Access Services
Patient API: http://localhost:8000/docs

Scheduling Service: http://localhost:8001/api/

AI Memory Service: http://localhost:8002/docs

Billing Service: http://localhost:8003/docs

Airflow: http://localhost:8080 (admin/admin)

Grafana: http://localhost:3000 (admin/admin)

Prometheus: http://localhost:9090

### 1. Clone and Setup

```bash
git clone <repository-url>
cd clinic-erp
