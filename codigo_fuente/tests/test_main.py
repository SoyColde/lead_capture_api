from fastapi.testclient import TestClient
from codigo_fuente.main import app
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

api_key = os.getenv("API_KEY")  # Retrieve the API key from environment variables

Client = TestClient(app)

def test_create_lead():

    lead_data = {
        "name": "Juan Perez",
        "email": "juan@example.com",
        "phone": "8095551234",
        "request": "Web Development",
        "notes": "Interested in a website"
    }

    response = Client.post(
        "/leads", json=lead_data, 
        headers={"X-API-Key": api_key})

    assert response.status_code == 201

def test_duplicate_information():
    lead_data = {
        "name": "Gindo Meregildo",
        "email": "juan@example.com",  # Duplicate email
        "phone": "8095555463",
        "request": "Web Development",
        "notes": "Interested in a website"
    }

    response = Client.post(
        "/leads", json=lead_data, 
        headers={"X-API-Key": api_key})

    assert response.status_code == 409

def test_incorrect_format():
    lead_data = {
        "name": "Carlos Santana",
        "email": "carlos@example.com",
        "request": "Web Development",
        "notes": "Interested in a website"
    }

    response = Client.post("/leads", json=lead_data, headers={"X-API-Key": api_key})
    assert response.status_code == 422

def test_missing_api_key():
    lead_data = {
        "name": "Maria Lopez",
        "email": "maria@example.com",
        "phone": "8095557890",
        "request": "Web Development",
        "notes": "Interested in a website"
    }

    response = Client.post("/leads", json=lead_data)
    assert response.status_code == 403 or response.status_code == 401  # Depending on how the API handles missing API keys

