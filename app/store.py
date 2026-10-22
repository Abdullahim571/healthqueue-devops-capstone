"""In-memory data store seeded with FICTIONAL patients only.

No real PHI is ever stored. A production system would use a managed database
(provisioned later with OpenTofu); the in-memory store keeps the capstone simple.
"""
import threading
import uuid
from datetime import timedelta

from .models import Appointment, AppointmentCreate, AppointmentStatus, Patient

# Fictional patients. Names and dates of birth are invented.
SEED_PATIENTS = [
    Patient(id="P-1001", name="Avery Testwell", date_of_birth="1985-03-14"),
    Patient(id="P-1002", name="Jordan Samplesson", date_of_birth="1992-07-22"),
    Patient(id="P-1003", name="Riley Mockford", date_of_birth="1978-11-05"),
]


class SlotConflictError(Exception):
    """Raised when a provider already has an overlapping appointment."""


class Store:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.patients = {p.id: p for p in SEED_PATIENTS}
        self.appointments: dict[str, Appointment] = {}

    def list_appointments(self, patient_id: str | None = None) -> list[Appointment]:
        appts = self.appointments.values()
        if patient_id:
            appts = [a for a in appts if a.patient_id == patient_id]
        return sorted(appts, key=lambda a: a.start_time)

    def create_appointment(self, data: AppointmentCreate) -> Appointment:
        start = data.start_time
        end = start + timedelta(minutes=data.duration_minutes)
        with self._lock:
            for a in self.appointments.values():
                if a.status != AppointmentStatus.scheduled or a.provider != data.provider:
                    continue
                a_end = a.start_time + timedelta(minutes=a.duration_minutes)
                if start < a_end and a.start_time < end:
                    raise SlotConflictError(a.id)
            appt = Appointment(id=f"A-{uuid.uuid4().hex[:8]}", **data.model_dump())
            self.appointments[appt.id] = appt
            return appt

    def cancel_appointment(self, appt_id: str) -> Appointment | None:
        with self._lock:
            appt = self.appointments.get(appt_id)
            if appt:
                appt.status = AppointmentStatus.cancelled
            return appt
