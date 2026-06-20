import pytest
from conftest import client, setup_database


def test_signup(setup_database):
    """Test user signup"""
    response = client.post("/create-author", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "test123"
    })
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
    assert "hashed_password" not in response.json()  # Password should not be returned


def test_signup_duplicate_email(setup_database):
    """Test signup with an email that already exists"""
    # First signup
    client.post("/create-author", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "test123"
    })
    
    # Second signup with same email
    response = client.post("/create-author", json={
        "name": "Another User",
        "email": "test@example.com",
        "password": "test123"
    })
    assert response.status_code == 409  # Conflict


def test_login_wrong_password(setup_database):
    # Signup first
    signup_response = client.post("/create-author", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "test123"
    })
    print("Signup response:", signup_response.status_code, signup_response.json())
    
    # Login with wrong password
    response = client.post("/login", json={
        "email": "test@example.com",
        "password": "wrongpassword",
        "role": "author"
    })
    print("Login response:", response.status_code, response.json())
    assert response.status_code == 401


def test_login_wrong_password(setup_database):
    """Test login with wrong password"""
    # Signup first
    client.post("/create-author", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "test123"
    })
    
    # Login with wrong password
    response = client.post("/login", json={
        "email": "test@example.com",
        "password": "wrongpassword",
        "role":'author'
    })
    assert response.status_code == 401

def test_protected_endpoint(setup_database):
    # Signup
    client.post("/create-author", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "test123"
    })
    
    # Login to get token
    login_response = client.post("/login", json={
        "email": "test@example.com",
        "password": "test123",
        "role": "author"
    })
    
    # Print to debug
    print("Login status:", login_response.status_code)
    print("Login body:", login_response.json())
    
    token = login_response.json()["access_token"]
    
    # Access protected endpoint
    response = client.get(
        "/my-profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

def test_protected_endpoint_no_token(setup_database):
    """Test accessing a protected endpoint without a token"""
    response = client.get("/my-profile")
    assert response.status_code == 401