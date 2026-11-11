import pytest
from datetime import timedelta
from auth.auth import pwd_context, create_access_token, authenticate_user
from core.config import settings

def test_password_hashing_and_verification():
    raw_password = "SecurePassword123!"
    hashed = pwd_context.hash(raw_password)
    assert hashed != raw_password
    assert pwd_context.verify(raw_password, hashed) is True
    assert pwd_context.verify("WrongPassword", hashed) is False

def test_create_user_rest_endpoint(client, db_session):
    unique_email = "new_unique_user@college.edu"
    payload = {"email": unique_email, "password": "password123"}
    
    # 1. Create user
    res = client.post("/auth/", json=payload)
    assert res.status_code == 201
    assert res.json()["message"] == "User created successfully"

    # 2. Duplicate email rejected
    res_dup = client.post("/auth/", json=payload)
    assert res_dup.status_code == 400
    assert "already registered" in res_dup.json()["detail"].lower()

def test_login_for_access_token_success(client):
    res = client.post("/auth/token", data={"username": "admin@college.edu", "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_for_access_token_invalid_password(client):
    res = client.post("/auth/token", data={"username": "admin@college.edu", "password": "wrong_password"})
    assert res.status_code == 401
    assert "incorrect email or password" in res.json()["detail"].lower()

def test_login_for_access_token_nonexistent_user(client):
    res = client.post("/auth/token", data={"username": "ghost@college.edu", "password": "password123"})
    assert res.status_code == 401
    assert "incorrect email or password" in res.json()["detail"].lower()

def test_login_deactivated_user(client, db_session):
    from models.identity import Users
    from sqlmodel import select
    
    # Create deactivated user
    deactivated_email = "deactivated@college.edu"
    existing = db_session.exec(select(Users).where(Users.email == deactivated_email)).first()
    if not existing:
        u = Users(email=deactivated_email, password_hash=pwd_context.hash("password123"), is_active=False)
        db_session.add(u)
        db_session.commit()
    else:
        existing.is_active = False
        db_session.add(existing)
        db_session.commit()

    res = client.post("/auth/token", data={"username": deactivated_email, "password": "password123"})
    assert res.status_code == 401
    assert "deactivated" in res.json()["detail"].lower()

def test_root_user_endpoint_authenticated(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    res = client.get("/", headers=headers)
    assert res.status_code == 200
    assert res.json()["User"]["email"] == "admin@college.edu"

def test_root_user_endpoint_unauthenticated(client):
    res = client.get("/")
    assert res.status_code == 401
