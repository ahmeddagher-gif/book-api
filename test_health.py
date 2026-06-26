# test_health.py
import pytest
from conftest import client, setup_database

def test_health_check(setup_database):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["redis"] == "connected"
    assert "timestamp" in data