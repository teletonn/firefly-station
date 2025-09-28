#!/usr/bin/env python3
"""
End-to-End Workflow Testing for Firefly Station
Tests complete user workflows from registration to emergency response.
"""

import asyncio
import json
import os
import sys
import time
import unittest
from typing import Dict, List, Optional

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from backend.main import app
from backend import database
from backend.geolocation import geolocation_service


class EndToEndWorkflowTest(unittest.TestCase):
    """Test complete end-to-end workflows."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.client = TestClient(app)
        database.init_db()

        # Test data
        cls.admin_user = {
            "username": "e2e_admin",
            "email": "e2e_admin@test.com",
            "password": "testpass123",
            "role": "super_admin"
        }

        cls.field_user = {
            "username": "e2e_field_user",
            "email": "e2e_field@test.com",
            "password": "testpass123",
            "role": "user"
        }

        cls.mesh_user_id = "!a1b2c3d4"

    def setUp(self):
        """Set up each test."""
        # Clear test data
        try:
            database.delete_user("e2e_admin")
            database.delete_user("e2e_field_user")
            database.delete_user("group1_user")
            database.delete_user("group2_user")

            # Clean up mesh user
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (self.mesh_user_id,))
            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Error in setUp cleaning users: {e}")

    def test_01_complete_user_registration_workflow(self):
        """Test complete user registration and setup workflow."""
        print("\n👤 Testing complete user registration workflow...")
        # Step 1: Admin registers
        response = self.client.post("/api/auth/register", json=self.admin_user)
        self.assertEqual(response.status_code, 200)
        admin_token = response.json()["access_token"]

        # Step 2: Admin logs in and verifies account
        login_data = {
            "username": self.admin_user["username"],
            "password": self.admin_user["password"]
        }
        response = self.client.post("/api/auth/login", data=login_data)
        self.assertEqual(response.status_code, 200)

        # Step 3: Admin creates field user account
        field_user_data = self.field_user.copy()
        response = self.client.post("/api/auth/register", json=field_user_data)
        self.assertEqual(response.status_code, 200)

        # Step 4: Verify both users exist in database
        admin_db = database.get_admin_user_by_username("e2e_admin")
        field_db = database.get_admin_user_by_username("e2e_field_user")

        self.assertIsNotNone(admin_db)
        self.assertIsNotNone(field_db)

        # Step 5: Test user profile access
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(response.status_code, 200)
        print("✅ Complete user registration workflow test passed")

    def test_02_emergency_zone_setup_workflow(self):
        """Test complete emergency zone setup workflow."""
        print("\n🚨 Testing emergency zone setup workflow...")
        # Step 1: Register admin
        response = self.client.post("/api/auth/register", json=self.admin_user)
        self.assertEqual(response.status_code, 200, f"Failed to register admin user: {response.text}")
        admin_token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Step 2: Create emergency zone
        zone_data = {
            "name": "Emergency Response Zone",
            "description": "High-risk emergency response area",
            "center_latitude": 55.7558,
            "center_longitude": 37.6173,
            "radius_meters": 1000,
            "zone_type": "danger_zone"
        }

        response = self.client.post("/api/zones", json=zone_data, headers=headers)
        self.assertEqual(response.status_code, 200, f"Failed to create zone: {response.text}")
        zone_result = response.json()
        zone_id = zone_result["id"]

        # Step 3: Verify zone exists
        response = self.client.get(f"/api/zones/{zone_id}", headers=headers)
        self.assertEqual(response.status_code, 200)
        print("✅ Emergency zone setup workflow test passed")

    def test_03_field_user_emergency_response_workflow(self):
        """Test field user emergency response workflow."""
        print("\n🚑 Testing field user emergency response workflow...")
        # Step 1: Set up admin and emergency zone
        response = self.client.post("/api/auth/register", json=self.admin_user)
        self.assertEqual(response.status_code, 200)
        admin_token = response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        zone_data = {
            "name": "Field Emergency Zone",
            "description": "Zone for field emergency testing",
            "center_latitude": 55.7558,
            "center_longitude": 37.6173,
            "radius_meters": 1000,
            "zone_type": "danger_zone"
        }
        response = self.client.post("/api/zones", json=zone_data, headers=admin_headers)
        self.assertEqual(response.status_code, 200)
        zone_id = response.json()["id"]

        # Step 2: Register field user
        response = self.client.post("/api/auth/register", json=self.field_user)
        self.assertEqual(response.status_code, 200)

        # Step 3: Create emergency alert as admin
        alert_data = {
            "title": "Field Emergency",
            "message": "Medical emergency in the field - immediate assistance needed",
            "severity": "critical",
            "alert_type": "medical"
        }

        response = self.client.post("/api/alerts/", json=alert_data, headers=admin_headers)
        self.assertEqual(response.status_code, 201)
        alert_id = response.json()["alert_id"]

        # Step 4: Admin acknowledges alert
        response = self.client.put(f"/api/alerts/{alert_id}/acknowledge", headers=admin_headers)
        self.assertEqual(response.status_code, 200)

        # Step 5: Admin resolves alert
        response = self.client.put(f"/api/alerts/{alert_id}/resolve", headers=admin_headers)
        self.assertEqual(response.status_code, 200)
        print("✅ Field user emergency response workflow test passed")

    def test_04_user_group_management_workflow(self):
        """Test user group and zone management workflow."""
        print("\n👥 Testing user group management workflow...")
        # Step 1: Register admin
        response = self.client.post("/api/auth/register", json=self.admin_user)
        self.assertEqual(response.status_code, 200)
        admin_token = response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Step 2: Create user group
        group_data = {"name": "Test Group", "description": "A group for testing"}
        response = self.client.post("/api/users/groups", json=group_data, headers=admin_headers)
        self.assertEqual(response.status_code, 200, f"Failed to create group: {response.text}")
        group_id = response.json()["id"]

        # Step 3: Create a mesh user directly in the database for testing
        database.insert_or_update_user(self.mesh_user_id, {"user": {"longName": "Test Mesh User"}})

        # Step 4: Add user to group
        response = self.client.post(f"/api/users/groups/{group_id}/users/{self.mesh_user_id}", headers=admin_headers)
        self.assertEqual(response.status_code, 200, f"Failed to add user to group: {response.text}")

        # Step 5: Verify user is in group
        response = self.client.get(f"/api/users/groups/{group_id}", headers=admin_headers)
        self.assertEqual(response.status_code, 200)
        group_details = response.json()
        self.assertIn(self.mesh_user_id, [user['id'] for user in group_details['users']])
        print("✅ User group management workflow test passed")

    def test_05_process_execution_workflow(self):
        """Test process creation and execution workflow."""
        print("\n⚙️ Testing process execution workflow...")
        # Step 1: Register admin
        response = self.client.post("/api/auth/register", json=self.admin_user)
        self.assertEqual(response.status_code, 200)
        admin_token = response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Step 2: Create a process
        process_data = {
            "name": "Test Process",
            "description": "A process for testing",
            "actions": [
                {
                    "action_type": "create_alert",
                    "action_config": {
                        "title": "Process Alert",
                        "message": "This alert was created by a process",
                        "severity": "low"
                    },
                    "action_order": 1
                }
            ]
        }
        response = self.client.post("/api/processes/", json=process_data, headers=admin_headers)
        self.assertEqual(response.status_code, 200)
        process_id = response.json()["process_id"]

        # Step 3: Execute the process
        response = self.client.post(f"/api/processes/{process_id}/execute", headers=admin_headers)
        self.assertEqual(response.status_code, 200)
        execution_id = response.json()["execution_id"]

        # Give a moment for the action to be processed
        time.sleep(0.1)

        # Step 4: Verify alert was created
        response = self.client.get("/api/alerts/", headers=admin_headers)
        self.assertEqual(response.status_code, 200)
        alerts = response.json()["alerts"]
        self.assertTrue(any(a['title'] == 'Process Alert' for a in alerts), "Process-generated alert not found")
        print("✅ Process execution workflow test passed")

if __name__ == "__main__":
    unittest.main()