"""Request/response schemas for the HealthQueue scheduling API."""
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class AppointmentStatus(str, Enum):
    scheduled = "scheduled"
    cancelled = "cancelled"


class Patient(BaseModel):
    id: str
    name: str
    date_of_birth: str


class AppointmentCreate(BaseModel):
    patient_id: str = Field(..., examples=["P-1001"])
    provider: str = Field(..., min_length=1, max_length=100, examples=["Dr. Ada Lumen"])
    start_time: datetime = Field(..., description="ISO-8601 timestamp with timezone")
    duration_minutes: int = Field(30, ge=10, le=120)
    reason: str = Field("", max_length=200)


class Appointment(AppointmentCreate):
    id: str
    status: AppointmentStatus = AppointmentStatus.scheduled
