from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AppointmentViewSet, TimeSlotViewSet, DoctorScheduleViewSet

router = DefaultRouter()
router.register(r'appointments', AppointmentViewSet)
router.register(r'timeslots', TimeSlotViewSet)
router.register(r'doctor-schedules', DoctorScheduleViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 