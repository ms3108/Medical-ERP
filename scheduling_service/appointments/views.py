from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta
import redis
import json
from kafka import KafkaProducer
import os

from .models import Appointment, TimeSlot, DoctorSchedule
from .serializers import (
    AppointmentSerializer, TimeSlotSerializer, DoctorScheduleSerializer,
    AppointmentCreateSerializer, AppointmentUpdateSerializer
)

# Redis connection for slot locking
redis_client = redis.Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

# Kafka producer for event streaming
kafka_producer = KafkaProducer(
    bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def publish_event(topic: str, event_data: dict):
    """Publish event to Kafka"""
    try:
        kafka_producer.send(topic, event_data)
        kafka_producer.flush()
    except Exception as e:
        print(f"Failed to publish to Kafka: {e}")

def acquire_slot_lock(doctor_id: int, date: str, start_time: str, timeout: int = 30):
    """Acquire Redis lock for appointment slot"""
    lock_key = f"appointment_lock:{doctor_id}:{date}:{start_time}"
    return redis_client.set(lock_key, "locked", ex=timeout, nx=True)

def release_slot_lock(doctor_id: int, date: str, start_time: str):
    """Release Redis lock for appointment slot"""
    lock_key = f"appointment_lock:{doctor_id}:{date}:{start_time}"
    redis_client.delete(lock_key)

class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return AppointmentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AppointmentUpdateSerializer
        return AppointmentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Extract appointment details
        doctor_id = serializer.validated_data['doctor_id']
        appointment_date = serializer.validated_data['appointment_date']
        start_time = serializer.validated_data['start_time']
        
        # Try to acquire slot lock
        date_str = appointment_date.strftime('%Y-%m-%d')
        time_str = start_time.strftime('%H:%M:%S')
        
        if not acquire_slot_lock(doctor_id, date_str, time_str):
            return Response(
                {"error": "Slot is currently being booked by another user. Please try again."},
                status=status.HTTP_409_CONFLICT
            )
        
        try:
            # Check if slot is available
            existing_appointment = Appointment.objects.filter(
                doctor_id=doctor_id,
                appointment_date=appointment_date,
                start_time=start_time
            ).first()
            
            if existing_appointment:
                return Response(
                    {"error": "This time slot is already booked"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create appointment
            appointment = serializer.save()
            
            # Publish event to Kafka
            publish_event("appointment_created", {
                "appointment_id": str(appointment.id),
                "patient_id": appointment.patient_id,
                "doctor_id": appointment.doctor_id,
                "appointment_date": appointment_date.isoformat(),
                "start_time": start_time.isoformat(),
                "created_at": timezone.now().isoformat()
            })
            
            return Response(
                AppointmentSerializer(appointment).data,
                status=status.HTTP_201_CREATED
            )
        
        finally:
            # Always release the lock
            release_slot_lock(doctor_id, date_str, time_str)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        old_status = instance.status
        appointment = serializer.save()
        
        # Publish status change event
        if old_status != appointment.status:
            publish_event("appointment_status_changed", {
                "appointment_id": str(appointment.id),
                "old_status": old_status,
                "new_status": appointment.status,
                "updated_at": timezone.now().isoformat()
            })
        
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=False, methods=['get'])
    def available_slots(self, request):
        """Get available time slots for a doctor on a specific date"""
        doctor_id = request.query_params.get('doctor_id')
        date = request.query_params.get('date')
        
        if not doctor_id or not date:
            return Response(
                {"error": "doctor_id and date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get doctor's schedule for this day
        day_of_week = date_obj.weekday()
        schedule = DoctorSchedule.objects.filter(
            doctor_id=doctor_id,
            day_of_week=day_of_week,
            is_available=True
        ).first()
        
        if not schedule:
            return Response({"available_slots": []})
        
        # Generate time slots
        slots = []
        current_time = schedule.start_time
        slot_duration = timedelta(minutes=30)  # 30-minute slots
        
        while current_time < schedule.end_time:
            # Check if slot is already booked
            existing_appointment = Appointment.objects.filter(
                doctor_id=doctor_id,
                appointment_date=date_obj,
                start_time=current_time
            ).first()
            
            if not existing_appointment:
                slots.append({
                    "start_time": current_time.strftime('%H:%M'),
                    "end_time": (datetime.combine(date_obj, current_time) + slot_duration).time().strftime('%H:%M')
                })
            
            current_time = (datetime.combine(date_obj, current_time) + slot_duration).time()
        
        return Response({"available_slots": slots})

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an appointment"""
        appointment = self.get_object()
        appointment.status = 'cancelled'
        appointment.save()
        
        # Publish cancellation event
        publish_event("appointment_cancelled", {
            "appointment_id": str(appointment.id),
            "patient_id": appointment.patient_id,
            "doctor_id": appointment.doctor_id,
            "cancelled_at": timezone.now().isoformat()
        })
        
        return Response({"message": "Appointment cancelled successfully"})

class TimeSlotViewSet(viewsets.ModelViewSet):
    queryset = TimeSlot.objects.all()
    serializer_class = TimeSlotSerializer
    permission_classes = [IsAuthenticated]

class DoctorScheduleViewSet(viewsets.ModelViewSet):
    queryset = DoctorSchedule.objects.all()
    serializer_class = DoctorScheduleSerializer
    permission_classes = [IsAuthenticated] 