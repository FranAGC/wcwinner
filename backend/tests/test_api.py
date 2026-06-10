import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add project root to python path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.api.main import app
from backend.database.repository import FootballRepository

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]

def test_get_teams():
    response = client.get("/teams")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # Check if Argentina is in the list
    team_ids = [t["team_id"] for t in data]
    assert "ARG" in team_ids
    assert "FRA" in team_ids

def test_get_team_detail():
    response = client.get("/team/ARG")
    assert response.status_code == 200
    data = response.json()
    assert data["team_name"] == "Argentina"
    assert data["team_code"] == "ARG"

def test_get_team_detail_not_found():
    response = client.get("/team/XYZ")
    assert response.status_code == 404

def test_get_matches():
    response = client.get("/matches")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Check if first match has team details
    assert "home_team" in data[0]
    assert "away_team" in data[0]

def test_get_rankings():
    response = client.get("/ranking")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Rank 1 should be Argentina or France in 2026
    assert data[0]["rank"] == 1

def test_get_elo():
    response = client.get("/elo")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # ELO list should be sorted desc
    assert data[0]["elo_rating"] >= data[1]["elo_rating"]
