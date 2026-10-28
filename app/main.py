"""HealthQueue appointment scheduling API."""

import os
import time
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from .models import Appointment, AppointmentCreate, Patient
from .store import SlotConflictError, Store

APP_VERSION = os.getenv("APP_VERSION", "dev")

app = FastAPI(title="HealthQueue Scheduling API", version=APP_VERSION)
store = Store()

# --- Metrics used for SLIs (availability + latency) ---
REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.025, 0.05, 0.1, 0.25, 0.3, 0.5, 1.0, 2.5),
)


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        # Use the route template (e.g. /appointments/{appt_id}) to keep label cardinality low.
        route = request.scope.get("route")
        path = getattr(route, "path", "unmatched")
        if path != "/metrics":
            REQUESTS.labels(request.method, path, str(status)).inc()
            LATENCY.labels(request.method, path).observe(time.perf_counter() - start)


# --- Operational endpoints ---
@app.get("/healthz", tags=["ops"])
def healthz():
    return {"status": "ok"}


@app.get("/readyz", tags=["ops"])
def readyz():
    return {"status": "ready", "version": APP_VERSION}


@app.get("/metrics", tags=["ops"], include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# --- Business endpoints ---
@app.get("/patients", response_model=list[Patient])
def list_patients():
    return list(store.patients.values())


@app.get("/appointments", response_model=list[Appointment])
def list_appointments(patient_id: str | None = None):
    return store.list_appointments(patient_id)


@app.get("/appointments/{appt_id}", response_model=Appointment)
def get_appointment(appt_id: str):
    appt = store.appointments.get(appt_id)
    if not appt:
        raise HTTPException(404, "Appointment not found")
    return appt


@app.post("/appointments", response_model=Appointment, status_code=201)
def create_appointment(body: AppointmentCreate):
    if body.patient_id not in store.patients:
        raise HTTPException(404, "Patient not found")
    if body.start_time.tzinfo is None:
        raise HTTPException(422, "start_time must include a timezone")
    if body.start_time <= datetime.now(UTC):
        raise HTTPException(422, "start_time must be in the future")
    try:
        return store.create_appointment(body)
    except SlotConflictError:
        # Don't echo the conflicting appointment's ID: it belongs to another patient.
        raise HTTPException(409, "Provider already booked for an overlapping time slot") from None


@app.delete("/appointments/{appt_id}", response_model=Appointment)
def cancel_appointment(appt_id: str):
    appt = store.cancel_appointment(appt_id)
    if not appt:
        raise HTTPException(404, "Appointment not found")
    return appt
