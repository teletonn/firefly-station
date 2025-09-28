#!/usr/bin/env python3
"""Test script for API endpoints."""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_root_endpoint():
    """Test the root endpoint."""
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Root endpoint: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Root endpoint failed: {e}")
        return False

def test_register_admin():
    """Test admin registration."""
    try:
        data = {
            "username": "testadmin",
            "email": "test@example.com",
            "password": "testpass123",
            "role": "admin"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=data)
        print(f"Register admin: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
        else:
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Register admin failed: {e}")
        return False

def test_login():
    """Test admin login."""
    try:
        data = {
            "username": "testadmin",
            "password": "testpass123"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", data=data)
        print(f"Login: {response.status_code}")
        if response.status_code == 200:
            token_data = response.json()
            print(f"Token received: {token_data['token_type']}")
            return token_data
        else:
            print(f"Error: {response.text}")
        return None
    except Exception as e:
        print(f"Login failed: {e}")
        return None

def test_protected_endpoint(token):
    """Test a protected endpoint."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        print(f"Protected endpoint: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
        else:
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Protected endpoint failed: {e}")
        return False

def test_users_endpoint(token):
    """Test users endpoint."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{BASE_URL}/api/users/", headers=headers)
        print(f"Users endpoint: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
        else:
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Users endpoint failed: {e}")
        return False

def main():
    print("Testing API endpoints...")

    # Test root endpoint
    if not test_root_endpoint():
        print("Root endpoint test failed")
        return

    # Test admin registration
    if not test_register_admin():
        print("Admin registration test failed")
        return

    # Test login
    token_data = test_login()
    if not token_data:
        print("Login test failed")
        return

    token = token_data['access_token']

    # Test protected endpoint
    if not test_protected_endpoint(token):
        print("Protected endpoint test failed")
        return

    # Test users endpoint
    if not test_users_endpoint(token):
        print("Users endpoint test failed")
        return

    print("All API tests passed!")

if __name__ == "__main__":
    main()