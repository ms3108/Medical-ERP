# AI-Enhanced Clinic ERP System

A comprehensive, microservices-based clinic management system with AI-powered features, real-time event streaming, and advanced analytics.

## 🏥 System Overview

This Clinic ERP system consists of multiple microservices working together to provide a complete healthcare management solution:

### Core Services

1. **Patient & Staff API** (FastAPI) - Port 8000
   - CRUD operations for patients, doctors, nurses, lab technicians
   - JWT-based authentication with role-based access control
   - Prescription and test order management
   - Event streaming to Kafka

2. **Scheduling Service** (Django REST Framework) - Port 8001
   - Appointment management with Redis slot locking
   - Google Calendar integration
   - Real-time availability checking
   - Double-booking prevention

3. **AI Memory Service** (FastAPI) - Port 8002
   - Prescription history analysis using TF-IDF and cosine similarity
   - AI-powered medication suggestions
   - Symptom pattern recognition
   - Test recommendation engine

4. **Billing Service** (FastAPI) - Port 8003
   - Invoice and payment management
   - Insurance claim processing
   - Idempotent endpoints for financial transactions
   - Revenue analytics

### Infrastructure

- **PostgreSQL** - Primary database
- **Redis** - Caching and slot locking
- **Kafka** - Event streaming
- **Airflow** - ETL pipeline for analytics
- **Prometheus + Grafana** - Monitoring and observability

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- At least 8GB RAM available
- Ports 8000-8003, 8080, 3000, 9090 available

### 1. Clone and Setup

```bash
git clone <repository-url>
cd clinic-erp
```

### 2. Environment Configuration

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql://admin:password123@postgres:5432/clinic_erp

# Redis
REDIS_URL=redis://redis:6379

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# JWT
SECRET_KEY=your-super-secret-key-here

# Google Calendar (optional)
GOOGLE_CALENDAR_API_KEY=your-google-api-key

# Airflow
AIRFLOW__CORE__FERNET_KEY=your-fernet-key-here
```

### 3. Start the System

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

### 4. Initialize Database

```bash
# Create database tables
docker-compose exec patient_api python -c "from main import app; from database import engine; from models import Base; Base.metadata.create_all(bind=engine)"
```

### 5. Access Services

- **Patient API**: http://localhost:8000/docs
- **Scheduling Service**: http://localhost:8001/api/
- **AI Memory Service**: http://localhost:8002/docs
- **Billing Service**: http://localhost:8003/docs
- **Airflow**: http://localhost:8080 (admin/admin)
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090

## 📊 API Usage Examples

### 1. Create a Patient

```bash
curl -X POST "http://localhost:8000/patients/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "John Doe",
    "date_of_birth": "1990-01-01T00:00:00",
    "gender": "male",
    "phone": "+1234567890",
    "email": "john@example.com",
    "address": "123 Main St",
    "emergency_contact": "+1234567891"
  }'
```

### 2. Create an Appointment

```bash
curl -X POST "http://localhost:8001/api/appointments/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN" \
  -d '{
    "patient_id": 1,
    "doctor_id": 1,
    "appointment_date": "2024-01-15",
    "start_time": "09:00:00",
    "end_time": "09:30:00",
    "notes": "Regular checkup"
  }'
```

### 3. Get AI Prescription Suggestions

```bash
curl -X GET "http://localhost:8002/suggestions/prescriptions/1?symptoms=fever%20and%20cough" \
  -H "Content-Type: application/json"
```

### 4. Create an Invoice

```bash
curl -X POST "http://localhost:8003/invoices/" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: unique-key-123" \
  -d '{
    "patient_id": 1,
    "appointment_id": 1,
    "invoice_number": "INV-001",
    "total_amount": 150.00,
    "due_date": "2024-01-20T00:00:00"
  }'
```

## 🔧 Development

### Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Patient API   │    │  Scheduling     │    │  AI Memory      │
│   (FastAPI)     │    │  Service        │    │  Service        │
│   Port: 8000    │    │  (Django)       │    │  (FastAPI)      │
│                 │    │  Port: 8001     │    │  Port: 8002     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Billing       │
                    │   Service       │
                    │   (FastAPI)     │
                    │   Port: 8003    │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │     Kafka       │
                    │   Event Stream  │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │    Airflow      │
                    │   ETL Pipeline  │
                    └─────────────────┘
```

### Key Features

#### 🔐 Authentication & Authorization
- JWT-based authentication
- Role-based access control (admin, doctor, nurse, lab_technician)
- Secure password hashing with bcrypt

#### 📅 Appointment Management
- Redis-based slot locking to prevent double bookings
- Real-time availability checking
- Google Calendar integration
- Appointment status tracking

#### 🤖 AI-Powered Features
- **Prescription Memory**: Analyzes patient history to suggest effective medications
- **Symptom Analysis**: Uses TF-IDF and cosine similarity for pattern recognition
- **Test Recommendations**: Rule-based test suggestions based on symptoms
- **Caching**: Redis caching for AI suggestions to improve performance

#### 💰 Billing & Insurance
- Idempotent endpoints for financial transactions
- Insurance claim processing
- Payment method tracking
- Revenue analytics

#### 📊 Analytics & Monitoring
- Real-time event streaming with Kafka
- ETL pipeline with Airflow
- Star schema data warehouse
- Prometheus metrics and Grafana dashboards

#### 🔄 Event-Driven Architecture
- Kafka topics for all major events
- Event sourcing for audit trails
- Real-time data synchronization

## 🛠️ Monitoring & Observability

### Prometheus Metrics

The system exposes metrics on `/metrics` endpoints for:
- API response times
- Database connection health
- Kafka consumer lag
- Redis cache hit rates
- Custom business metrics

### Grafana Dashboards

Pre-configured dashboards for:
- Service health and performance
- Appointment booking trends
- Revenue analytics
- AI suggestion accuracy
- System resource usage

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   docker-compose logs postgres
   docker-compose restart postgres
   ```

2. **Kafka Connection Issues**
   ```bash
   docker-compose logs kafka
   docker-compose restart kafka zookeeper
   ```

3. **Service Health Checks**
   ```bash
   # Check all services
   curl http://localhost:8000/health
   curl http://localhost:8001/api/health
   curl http://localhost:8002/health
   curl http://localhost:8003/health
   ```

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f patient_api
docker-compose logs -f scheduling_service
```

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale specific services
docker-compose up -d --scale patient_api=3
docker-compose up -d --scale ai_memory_service=2
```

### Production Deployment

For production deployment, consider:
- Using Kubernetes instead of Docker Compose
- Setting up proper SSL/TLS certificates
- Implementing database clustering
- Using managed Kafka services
- Setting up proper backup strategies

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation at `/docs` endpoints

---

**Note**: This is a development setup. For production use, ensure proper security configurations, SSL certificates, and environment-specific settings. #   M e d i c a l - E R P  
 # Medical-ERP
# Medical-ERP
