from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app import main
from app.store import Store


@pytest.fixture
def client():
    main.store = Store()  # fresh state for every test
    return TestClient(main.app)


def future(hours=24):
    return (datetime.now(UTC) + timedelta(hours=hours)).isoformat()


def book(client, **overrides):
    body = {"patient_id": "P-1001", "provider": "Dr. Ada Lumen", "start_time": future()}
    body.update(overrides)
    return client.post("/appointments", json=body)


def test_health_and_ready(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").status_code == 200


def test_list_fictional_patients(client):
    ids = {p["id"] for p in client.get("/patients").json()}
    assert ids == {"P-1001", "P-1002", "P-1003"}


def test_create_and_get_appointment(client):
    r = book(client, reason="Annual check-up")
    assert r.status_code == 201
    appt = r.json()
    assert appt["status"] == "scheduled"
    assert client.get(f"/appointments/{appt['id']}").json() == appt


def test_unknown_patient_rejected(client):
    assert book(client, patient_id="P-9999").status_code == 404


def test_past_time_rejected(client):
    assert book(client, start_time=future(hours=-1)).status_code == 422


def test_naive_timestamp_rejected(client):
    assert book(client, start_time="2099-01-01T09:00:00").status_code == 422


def test_invalid_duration_rejected(client):
    assert book(client, duration_minutes=5).status_code == 422


def test_double_booking_rejected(client):
    t = future()
    assert book(client, start_time=t).status_code == 201
    assert book(client, patient_id="P-1002", start_time=t).status_code == 409


def test_double_booking_does_not_leak_other_appointment(client):
    t = future()
    first = book(client, start_time=t).json()
    r = book(client, patient_id="P-1002", start_time=t)
    assert r.status_code == 409
    assert first["id"] not in r.text


def test_back_to_back_same_provider_allowed(client):
    # A 30-minute slot ends exactly when the next one starts: touching is not overlapping.
    start = datetime.now(UTC).replace(microsecond=0) + timedelta(days=1)
    assert book(client, start_time=start.isoformat(), duration_minutes=30).status_code == 201
    nxt = (start + timedelta(minutes=30)).isoformat()
    assert book(client, patient_id="P-1002", start_time=nxt).status_code == 201


def test_one_minute_overlap_rejected(client):
    start = datetime.now(UTC).replace(microsecond=0) + timedelta(days=1)
    assert book(client, start_time=start.isoformat(), duration_minutes=30).status_code == 201
    overlap = (start + timedelta(minutes=29)).isoformat()
    assert book(client, patient_id="P-1002", start_time=overlap).status_code == 409


def test_different_provider_same_time_allowed(client):
    t = future()
    assert book(client, start_time=t).status_code == 201
    assert book(client, provider="Dr. Ben Placeholder", start_time=t).status_code == 201


def test_cancel_frees_slot(client):
    t = future()
    appt = book(client, start_time=t).json()
    r = client.delete(f"/appointments/{appt['id']}")
    assert r.json()["status"] == "cancelled"
    assert book(client, patient_id="P-1002", start_time=t).status_code == 201


def test_filter_by_patient(client):
    book(client, start_time=future(24))
    book(client, patient_id="P-1002", start_time=future(48))
    appts = client.get("/appointments", params={"patient_id": "P-1002"}).json()
    assert [a["patient_id"] for a in appts] == ["P-1002"]


def test_missing_appointment_404(client):
    assert client.get("/appointments/A-nope").status_code == 404
    assert client.delete("/appointments/A-nope").status_code == 404


def test_metrics_exposed(client):
    client.get("/healthz")
    body = client.get("/metrics").text
    assert 'http_requests_total{method="GET",route="/healthz",status="200"}' in body


def test_unknown_paths_share_one_metric_label(client):
    # Raw paths must never become label values (unbounded cardinality, IDs leaking into metrics).
    labels = {"method": "GET", "route": "unmatched", "status": "404"}
    before = REGISTRY.get_sample_value("http_requests_total", labels) or 0.0
    client.get("/does-not-exist")
    client.get("/also/missing/A-12345")
    assert REGISTRY.get_sample_value("http_requests_total", labels) == before + 2
    body = client.get("/metrics").text
    assert "does-not-exist" not in body and "A-12345" not in body


def test_metrics_not_counted_in_sli(client):
    client.get("/metrics")
    assert 'route="/metrics"' not in client.get("/metrics").text


def test_status_serialises_as_plain_string(client):
    appt = book(client).json()
    assert appt["status"] == "scheduled"
    assert client.delete(f"/appointments/{appt['id']}").json()["status"] == "cancelled"
