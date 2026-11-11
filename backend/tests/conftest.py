import pytest
import sys
from pathlib import Path

# Add backend root to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from sqlmodel import Session, select
from core.database import engine
from main import app
from seed_db import seed_db
from models.identity import Users
from models.organization import StudentProfiles, FacultyProfiles

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure database is seeded with consistent reference data once per test session."""
    seed_db()
    yield

@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient instance."""
    return TestClient(app)

@pytest.fixture
def db_session():
    """Direct database session for inspecting or setting up test data."""
    with Session(engine) as session:
        yield session

def fetch_token(client: TestClient, email: str, password: str) -> str:
    res = client.post("/auth/token", data={"username": email, "password": password})
    assert res.status_code == 200, f"Authentication failed for {email}: {res.text}"
    return res.json()["access_token"]

@pytest.fixture(scope="session")
def admin_token(client):
    return fetch_token(client, "admin@college.edu", "password123")

@pytest.fixture(scope="session")
def faculty_token(client):
    return fetch_token(client, "faculty@college.edu", "password123")

@pytest.fixture(scope="session")
def student1_token(client):
    # student@college.edu has roll 26BCS001, student_profile id 30, user_id 3
    return fetch_token(client, "student@college.edu", "password123")

@pytest.fixture(scope="session")
def student2_token(client):
    # akshpathak001@iiitmg.ac.in has roll 2024BMS-001, student_profile id 1, user_id 12
    return fetch_token(client, "akshpathak001@iiitmg.ac.in", "1234")

@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}

@pytest.fixture(scope="session")
def faculty_headers(faculty_token):
    return {"Authorization": f"Bearer {faculty_token}"}

@pytest.fixture(scope="session")
def student1_headers(student1_token):
    return {"Authorization": f"Bearer {student1_token}"}

@pytest.fixture(scope="session")
def student2_headers(student2_token):
    return {"Authorization": f"Bearer {student2_token}"}

@pytest.fixture(scope="session")
def gql(client):
    """Convenience helper to execute GraphQL requests."""
    def _execute(query: str, headers: dict = None, variables: dict = None):
        res = client.post(
            "/graphql",
            json={"query": query, "variables": variables or {}},
            headers=headers or {}
        )
        body = res.json()
        return body.get("data"), body.get("errors")
    return _execute
