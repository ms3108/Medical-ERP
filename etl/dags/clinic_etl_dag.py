from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta
import json
import pandas as pd
from kafka import KafkaConsumer
import psycopg2
from sqlalchemy import create_engine
import os

default_args = {
    'owner': 'clinic_erp',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'clinic_etl_pipeline',
    default_args=default_args,
    description='ETL pipeline for Clinic ERP analytics',
    schedule_interval=timedelta(hours=1),
    catchup=False,
)

def extract_kafka_events():
    """Extract events from Kafka topics"""
    
    # Kafka consumer configuration
    consumer = KafkaConsumer(
        'appointment_created',
        'prescription_issued', 
        'test_completed',
        'patient_created',
        bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id='etl_consumer',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    
    # Extract events for the last hour
    events = []
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=1)
    
    for message in consumer:
        event_time = datetime.fromisoformat(message.value.get('created_at', '').replace('Z', '+00:00'))
        if start_time <= event_time <= end_time:
            events.append({
                'topic': message.topic,
                'event_data': message.value,
                'timestamp': event_time
            })
    
    consumer.close()
    
    # Store in staging table
    engine = create_engine(os.getenv('DATABASE_URL', 'postgresql://admin:password123@localhost:5432/clinic_erp'))
    
    for event in events:
        with engine.connect() as conn:
            conn.execute("""
                INSERT INTO staging_events (topic, event_data, timestamp)
                VALUES (%s, %s, %s)
            """, (event['topic'], json.dumps(event['event_data']), event['timestamp']))
            conn.commit()
    
    return len(events)

def transform_appointments():
    """Transform appointment events into fact table"""
    
    engine = create_engine(os.getenv('DATABASE_URL', 'postgresql://admin:password123@localhost:5432/clinic_erp'))
    
    # Get appointment events from staging
    query = """
        SELECT event_data, timestamp 
        FROM staging_events 
        WHERE topic = 'appointment_created'
        AND processed = false
    """
    
    df = pd.read_sql(query, engine)
    
    if df.empty:
        return 0
    
    # Transform data
    appointments = []
    for _, row in df.iterrows():
        event_data = row['event_data']
        appointments.append({
            'appointment_id': event_data.get('appointment_id'),
            'patient_id': event_data.get('patient_id'),
            'doctor_id': event_data.get('doctor_id'),
            'appointment_date': event_data.get('appointment_date'),
            'start_time': event_data.get('start_time'),
            'created_at': row['timestamp']
        })
    
    # Insert into fact table
    if appointments:
        df_fact = pd.DataFrame(appointments)
        df_fact.to_sql('fact_appointments', engine, if_exists='append', index=False)
        
        # Mark as processed
        with engine.connect() as conn:
            conn.execute("""
                UPDATE staging_events 
                SET processed = true 
                WHERE topic = 'appointment_created' AND processed = false
            """)
            conn.commit()
    
    return len(appointments)

def transform_prescriptions():
    """Transform prescription events into fact table"""
    
    engine = create_engine(os.getenv('DATABASE_URL', 'postgresql://admin:password123@localhost:5432/clinic_erp'))
    
    # Get prescription events from staging
    query = """
        SELECT event_data, timestamp 
        FROM staging_events 
        WHERE topic = 'prescription_issued'
        AND processed = false
    """
    
    df = pd.read_sql(query, engine)
    
    if df.empty:
        return 0
    
    # Transform data
    prescriptions = []
    for _, row in df.iterrows():
        event_data = row['event_data']
        prescriptions.append({
            'prescription_id': event_data.get('prescription_id'),
            'patient_id': event_data.get('patient_id'),
            'doctor_id': event_data.get('doctor_id'),
            'medications': json.dumps(event_data.get('medications', [])),
            'issued_at': event_data.get('issued_at'),
            'created_at': row['timestamp']
        })
    
    # Insert into fact table
    if prescriptions:
        df_fact = pd.DataFrame(prescriptions)
        df_fact.to_sql('fact_prescriptions', engine, if_exists='append', index=False)
        
        # Mark as processed
        with engine.connect() as conn:
            conn.execute("""
                UPDATE staging_events 
                SET processed = true 
                WHERE topic = 'prescription_issued' AND processed = false
            """)
            conn.commit()
    
    return len(prescriptions)

def load_dimension_tables():
    """Load dimension tables from main database"""
    
    engine = create_engine(os.getenv('DATABASE_URL', 'postgresql://admin:password123@localhost:5432/clinic_erp'))
    
    # Load patient dimension
    patients_query = "SELECT id, name, date_of_birth, gender FROM patients"
    df_patients = pd.read_sql(patients_query, engine)
    
    if not df_patients.empty:
        df_patients.to_sql('dim_patient', engine, if_exists='replace', index=False)
    
    # Load doctor dimension
    doctors_query = "SELECT id, name, specialization FROM doctors"
    df_doctors = pd.read_sql(doctors_query, engine)
    
    if not df_doctors.empty:
        df_doctors.to_sql('dim_doctor', engine, if_exists='replace', index=False)
    
    # Load date dimension (for the last 30 days)
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
    df_dates = pd.DataFrame({
        'date_id': dates.strftime('%Y%m%d'),
        'date': dates,
        'year': dates.year,
        'month': dates.month,
        'day': dates.day,
        'day_of_week': dates.dayofweek
    })
    
    df_dates.to_sql('dim_date', engine, if_exists='replace', index=False)
    
    return len(df_patients) + len(df_doctors) + len(df_dates)

# Define tasks
extract_task = PythonOperator(
    task_id='extract_kafka_events',
    python_callable=extract_kafka_events,
    dag=dag,
)

transform_appointments_task = PythonOperator(
    task_id='transform_appointments',
    python_callable=transform_appointments,
    dag=dag,
)

transform_prescriptions_task = PythonOperator(
    task_id='transform_prescriptions',
    python_callable=transform_prescriptions,
    dag=dag,
)

load_dimensions_task = PythonOperator(
    task_id='load_dimension_tables',
    python_callable=load_dimension_tables,
    dag=dag,
)

# Define task dependencies
extract_task >> [transform_appointments_task, transform_prescriptions_task, load_dimensions_task] 