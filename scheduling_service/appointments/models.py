from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient_id = models.IntegerField()
    doctor_id = models.IntegerField()
    appointment_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True, null=True)
    google_calendar_event_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['doctor_id', 'appointment_date', 'start_time']
        ordering = ['appointment_date', 'start_time']
    
    def __str__(self):
        return f"Appointment {self.id} - Patient {self.patient_id} with Doctor {self.doctor_id}"

class TimeSlot(models.Model):
    doctor_id = models.IntegerField()
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    appointment_id = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['doctor_id', 'date', 'start_time']
    
    def __str__(self):
        return f"TimeSlot - Doctor {self.doctor_id} on {self.date} at {self.start_time}"

class DoctorSchedule(models.Model):
    doctor_id = models.IntegerField()
    day_of_week = models.IntegerField()  # 0=Monday, 6=Sunday
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['doctor_id', 'day_of_week']
    
    def __str__(self):
        return f"Schedule - Doctor {self.doctor_id} on day {self.day_of_week}" 