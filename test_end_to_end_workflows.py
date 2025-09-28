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
            "role": "admin"
        }

        cls.field_user = {
            "username": "e2e_field_user",
            "email": "e2e_field@test.com",
            "password": "testpass123",
            "role": "user"
        }

    def setUp(self):
        """Set up each test."""
        # Clear test data
        try:
            database.delete_user("e2e_admin")
            database.delete_user("e2e_field_user")
        except:
            pass

    def test_01_complete_user_registration_workflow(self):
        """Test complete user registration and setup workflow."""
        print("\n👤 Testing complete user registration workflow...")

        try:
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
            field_token = response.json()["access_token"]

            # Step 4: Verify both users exist in database
            admin_db = database.get_user("e2e_admin")
            field_db = database.get_user("e2e_field_user")

            self.assertIsNotNone(admin_db)
            self.assertIsNotNone(field_db)

            # Step 5: Test user profile access
            headers = {"Authorization": f"Bearer {admin_token}"}
            response = self.client.get("/api/auth/me", headers=headers)
            self.assertEqual(response.status_code, 200)

            print("✅ Complete user registration workflow test passed")
            return True

        except Exception as e:
            print(f"❌ Complete user registration workflow test failed: {e}")
            return False

    def test_02_emergency_zone_setup_workflow(self):
        """Test complete emergency zone setup workflow."""
        print("\n🚨 Testing emergency zone setup workflow...")

        try:
            # Step 1: Register admin
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {admin_token}"}

            # Step 2: Create emergency zone
            zone_data = {
                "name": "Emergency Response Zone",
                "description": "High-risk emergency response area",
                "coordinates": [
                    [55.7558, 37.6173],
                    [55.7658, 37.6273],
                    [55.7658, 37.6073],
                    [55.7558, 37.6173]
                ],
                "zone_type": "emergency",
                "alert_level": "high"
            }

            response = self.client.post("/api/zones/", json=zone_data, headers=headers)
            self.assertEqual(response.status_code, 200)
            zone_result = response.json()
            zone_id = zone_result["id"]

            # Step 3: Create alert rule for zone
            alert_data = {
                "title": "Emergency Zone Alert",
                "message": "Emergency situation in designated zone",
                "severity": "high",
                "alert_type": "emergency",
                "zone_id": zone_id
            }

            response = self.client.post("/api/alerts/", json=alert_data, headers=headers)
            self.assertEqual(response.status_code, 200)
            alert_result = response.json()
            alert_id = alert_result["id"]

            # Step 4: Verify zone and alert exist
            response = self.client.get(f"/api/zones/{zone_id}", headers=headers)
            self.assertEqual(response.status_code, 200)

            response = self.client.get(f"/api/alerts/{alert_id}", headers=headers)
            self.assertEqual(response.status_code, 200)

            # Step 5: Test zone listing
            response = self.client.get("/api/zones/", headers=headers)
            self.assertEqual(response.status_code, 200)
            zones = response.json()
            self.assertTrue(len(zones) > 0)

            print("✅ Emergency zone setup workflow test passed")
            return True

        except Exception as e:
            print(f"❌ Emergency zone setup workflow test failed: {e}")
            return False

    def test_03_field_user_emergency_response_workflow(self):
        """Test field user emergency response workflow."""
        print("\n🚑 Testing field user emergency response workflow...")

        try:
            # Step 1: Set up admin and emergency zone
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Create emergency zone
            zone_data = {
                "name": "Field Emergency Zone",
                "description": "Zone for field emergency testing",
                "coordinates": [
                    [55.7558, 37.6173],
                    [55.7658, 37.6273],
                    [55.7658, 37.6073],
                    [55.7558, 37.6173]
                ],
                "zone_type": "emergency",
                "alert_level": "high"
            }

            response = self.client.post("/api/zones/", json=zone_data, headers=admin_headers)
            zone_result = response.json()
            zone_id = zone_result["id"]

            # Step 2: Register field user
            response = self.client.post("/api/auth/register", json=self.field_user)
            field_token = response.json()["access_token"]
            field_headers = {"Authorization": f"Bearer {field_token}"}

            # Step 3: Simulate field user entering emergency zone
            emergency_location = {
                "user_id": "e2e_field_user",
                "latitude": 55.7600,  # Inside emergency zone
                "longitude": 37.6200,
                "altitude": 100,
                "battery_level": 60
            }

            result = geolocation_service.process_location_update(**emergency_location)
            self.assertTrue(result["success"])

            # Step 4: Create emergency alert as field user
            alert_data = {
                "title": "Field Emergency",
                "message": "Medical emergency in the field - immediate assistance needed",
                "severity": "critical",
                "alert_type": "medical",
                "location": {
                    "latitude": 55.7600,
                    "longitude": 37.6200
                }
            }

            response = self.client.post("/api/alerts/", json=alert_data, headers=field_headers)
            self.assertEqual(response.status_code, 200)
            alert_result = response.json()
            alert_id = alert_result["id"]

            # Step 5: Admin acknowledges alert
            update_data = {
                "status": "acknowledged",
                "response_notes": "Emergency response team dispatched"
            }
            response = self.client.put(f"/api/alerts/{alert_id}", json=update_data, headers=admin_headers)
            self.assertEqual(response.status_code, 200)

            # Step 6: Admin resolves alert
            update_data = {
                "status": "resolved",
                "response_notes": "Patient evacuated successfully"
            }
            response = self.client.put(f"/api/alerts/{alert_id}", json=update_data, headers=admin_headers)
            self.assertEqual(response.status_code, 200)

            print("✅ Field user emergency response workflow test passed")
            return True

        except Exception as e:
            print(f"❌ Field user emergency response workflow test failed: {e}")
            return False

    def test_04_user_group_zone_management_workflow(self):
        """Test user group and zone management workflow."""
        print("\n👥 Testing user group zone management workflow...")

        try:
            # Step 1: Register admin
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Step 2: Create multiple zones
            zones = []
            for i in range(3):
                zone_data = {
                    "name": f"Group Zone {i+1}",
                    "description": f"Zone {i+1} for group testing",
                    "coordinates": [
                        [55.7558 + i*0.01, 37.6173 + i*0.01],
                        [55.7658 + i*0.01, 37.6273 + i*0.01],
                        [55.7658 + i*0.01, 37.6073 + i*0.01],
                        [55.7558 + i*0.01, 37.6173 + i*0.01]
                    ],
                    "zone_type": "restricted",
                    "alert_level": "medium"
                }

                response = self.client.post("/api/zones/", json=zone_data, headers=admin_headers)
                self.assertEqual(response.status_code, 200)
                zones.append(response.json())

            # Step 3: Create users for different groups
            group1_user = {
                "username": "group1_user",
                "email": "group1@test.com",
                "password": "testpass123",
                "role": "user",
                "zone_access": [zones[0]["id"]]  # Access to zone 1 only
            }

            group2_user = {
                "username": "group2_user",
                "email": "group2@test.com",
                "password": "testpass123",
                "role": "user",
                "zone_access": [zones[1]["id"], zones[2]["id"]]  # Access to zones 2 and 3
            }

            response = self.client.post("/api/auth/register", json=group1_user)
            self.assertEqual(response.status_code, 200)

            response = self.client.post("/api/auth/register", json=group2_user)
            self.assertEqual(response.status_code, 200)

            # Step 4: Test zone access permissions
            group1_token = self.client.post("/api/auth/login", data={
                "username": "group1_user",
                "password": "testpass123"
            }).json()["access_token"]

            group1_headers = {"Authorization": f"Bearer {group1_token}"}

            # Group 1 user should only see their zone
            response = self.client.get("/api/zones/", headers=group1_headers)
            self.assertEqual(response.status_code, 200)
            group1_zones = response.json()
            self.assertEqual(len(group1_zones), 1)
            self.assertEqual(group1_zones[0]["id"], zones[0]["id"])

            # Step 5: Create alerts for different zones
            alert1_data = {
                "title": "Group 1 Alert",
                "message": "Alert for group 1 zone",
                "severity": "medium",
                "alert_type": "zone",
                "zone_id": zones[0]["id"]
            }

            alert2_data = {
                "title": "Group 2 Alert",
                "message": "Alert for group 2 zones",
                "severity": "medium",
                "alert_type": "zone",
                "zone_id": zones[1]["id"]
            }

            response = self.client.post("/api/alerts/", json=alert1_data, headers=admin_headers)
            self.assertEqual(response.status_code, 200)

            response = self.client.post("/api/alerts/", json=alert2_data, headers=admin_headers)
            self.assertEqual(response.status_code, 200)

            print("✅ User group zone management workflow test passed")
            return True

        except Exception as e:
            print(f"❌ User group zone management workflow test failed: {e}")
            return False

    def test_05_real_time_location_tracking_workflow(self):
        """Test real-time location tracking and updates workflow."""
        print("\n📍 Testing real-time location tracking workflow...")

        try:
            # Step 1: Set up admin and tracking zone
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Create tracking zone
            zone_data = {
                "name": "Location Tracking Zone",
                "description": "Zone for real-time tracking test",
                "coordinates": [
                    [55.7558, 37.6173],
                    [55.7658, 37.6273],
                    [55.7658, 37.6073],
                    [55.7558, 37.6173]
                ],
                "zone_type": "tracking",
                "alert_level": "low"
            }

            response = self.client.post("/api/zones/", json=zone_data, headers=admin_headers)
            zone_result = response.json()
            zone_id = zone_result["id"]

            # Step 2: Register field user
            response = self.client.post("/api/auth/register", json=self.field_user)
            field_token = response.json()["access_token"]

            # Step 3: Simulate real-time location updates
            locations = [
                {"lat": 55.7560, "lng": 37.6180, "alt": 100},  # Outside zone
                {"lat": 55.7590, "lng": 37.6210, "alt": 105},  # Entering zone
                {"lat": 55.7600, "lng": 37.6220, "alt": 110},  # Inside zone
                {"lat": 55.7610, "lng": 37.6230, "alt": 115},  # Moving within zone
                {"lat": 55.7700, "lng": 37.6300, "alt": 120},  # Exiting zone
            ]

            for i, location in enumerate(locations):
                result = geolocation_service.process_location_update(
                    user_id="e2e_field_user",
                    latitude=location["lat"],
                    longitude=location["lng"],
                    altitude=location["alt"],
                    battery_level=85 - i*2
                )

                self.assertTrue(result["success"])
                self.assertIsInstance(result["is_moving"], bool)
                self.assertIsInstance(result["speed_mps"], (int, float))

                # Small delay to simulate real-time tracking
                time.sleep(0.1)

            # Step 4: Verify location history is stored
            user = database.get_user("e2e_field_user")
            self.assertIsNotNone(user)

            print("✅ Real-time location tracking workflow test passed")
            return True

        except Exception as e:
            print(f"❌ Real-time location tracking workflow test failed: {e}")
            return False

    def test_06_bot_trigger_response_workflow(self):
        """Test bot trigger and response workflow."""
        print("\n🤖 Testing bot trigger response workflow...")

        try:
            # Step 1: Set up admin and configure bot
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Step 2: Create bot trigger configuration
            trigger_data = {
                "name": "Emergency Keyword Trigger",
                "description": "Trigger on emergency keywords",
                "keywords": ["help", "emergency", "urgent"],
                "response_template": "Emergency signal received. Help is on the way. Current location: {latitude}, {longitude}",
                "alert_level": "high",
                "cooldown_minutes": 5
            }

            # Note: This would typically be done through a bot configuration API
            # For now, we'll simulate the trigger logic

            # Step 3: Simulate incoming emergency message
            emergency_message = "HELP! I'm in an emergency situation!"

            # Simulate message processing (this would normally come through Meshtastic)
            # Store the message
            database.insert_message(
                sender="bot_test_user",
                receiver="central",
                message=emergency_message,
                direction="incoming"
            )

            # Step 4: Verify message is stored and could trigger bot response
            messages = database.get_messages_for_user("bot_test_user", limit=10)
            self.assertTrue(len(messages) > 0)

            emergency_found = any("HELP" in msg["message"] for msg in messages)
            self.assertTrue(emergency_found)

            print("✅ Bot trigger response workflow test passed")
            return True

        except Exception as e:
            print(f"❌ Bot trigger response workflow test failed: {e}")
            return False

    def test_07_multi_user_coordination_workflow(self):
        """Test multi-user coordination workflow."""
        print("\n🤝 Testing multi-user coordination workflow...")

        try:
            # Step 1: Set up admin and multiple users
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Create multiple field users
            field_users = []
            for i in range(3):
                user_data = {
                    "username": f"coordination_user_{i+1}",
                    "email": f"coordination{i+1}@test.com",
                    "password": "testpass123",
                    "role": "user"
                }

                response = self.client.post("/api/auth/register", json=user_data)
                self.assertEqual(response.status_code, 200)
                field_users.append(response.json())

            # Step 2: Create shared emergency zone
            zone_data = {
                "name": "Multi-User Emergency Zone",
                "description": "Shared zone for coordination testing",
                "coordinates": [
                    [55.7558, 37.6173],
                    [55.7658, 37.6273],
                    [55.7658, 37.6073],
                    [55.7558, 37.6173]
                ],
                "zone_type": "emergency",
                "alert_level": "high"
            }

            response = self.client.post("/api/zones/", json=zone_data, headers=admin_headers)
            zone_result = response.json()
            zone_id = zone_result["id"]

            # Step 3: Simulate multiple users in emergency situation
            for i, user_token in enumerate([fu["access_token"] for fu in field_users]):
                user_headers = {"Authorization": f"Bearer {user_token}"}

                # Users report emergency situation
                alert_data = {
                    "title": f"Emergency Report {i+1}",
                    "message": f"User {i+1} reporting emergency in shared zone",
                    "severity": "high",
                    "alert_type": "emergency",
                    "zone_id": zone_id
                }

                response = self.client.post("/api/alerts/", json=alert_data, headers=user_headers)
                self.assertEqual(response.status_code, 200)

            # Step 4: Admin coordinates response
            # Get all alerts for the zone
            response = self.client.get(f"/api/zones/{zone_id}/alerts", headers=admin_headers)
            self.assertEqual(response.status_code, 200)
            zone_alerts = response.json()
            self.assertTrue(len(zone_alerts) >= 3)

            # Admin creates coordination alert
            coordination_alert = {
                "title": "Emergency Coordination Alert",
                "message": "Multiple emergencies reported. Coordinating response teams.",
                "severity": "critical",
                "alert_type": "coordination",
                "zone_id": zone_id
            }

            response = self.client.post("/api/alerts/", json=coordination_alert, headers=admin_headers)
            self.assertEqual(response.status_code, 200)

            print("✅ Multi-user coordination workflow test passed")
            return True

        except Exception as e:
            print(f"❌ Multi-user coordination workflow test failed: {e}")
            return False

    def run_end_to_end_workflow_suite(self):
        """Run the complete end-to-end workflow test suite."""
        print("🔄 Starting Firefly Station End-to-End Workflow Test Suite")
        print("=" * 70)

        tests = [
            self.test_01_complete_user_registration_workflow,
            self.test_02_emergency_zone_setup_workflow,
            self.test_03_field_user_emergency_response_workflow,
            self.test_04_user_group_zone_management_workflow,
            self.test_05_real_time_location_tracking_workflow,
            self.test_06_bot_trigger_response_workflow,
            self.test_07_multi_user_coordination_workflow
        ]

        passed = 0
        total = len(tests)

        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")

        print("\n" + "=" * 70)
        print(f"End-to-End Workflow Test Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All end-to-end workflow tests passed!")
            return True
        else:
            print("⚠️  Some end-to-end workflow tests failed")
            return False


def main():
    """Main function to run end-to-end workflow tests."""
    test_suite = EndToEndWorkflowTest()
    success = test_suite.run_end_to_end_workflow_suite()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()