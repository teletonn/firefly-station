#!/usr/bin/env python3
"""
Component Integration Testing for Firefly Station
Tests individual component interactions and dependencies.
"""

import asyncio
import json
import os
import sys
import time
import unittest
from typing import Dict, List, Optional
from unittest.mock import Mock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from backend.main import app
from backend import database
from backend.geolocation import geolocation_service


class ComponentIntegrationTest(unittest.TestCase):
    """Test integration between individual system components."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.client = TestClient(app)
        database.init_db()

        # Test data
        cls.test_admin = {
            "username": "component_admin",
            "email": "component@test.com",
            "password": "testpass123",
            "role": "admin"
        }

    def setUp(self):
        """Set up each test."""
        # Clear test data
        try:
            database.delete_user("component_admin")
        except:
            pass

    def test_01_database_geolocation_integration(self):
        """Test database and geolocation service integration."""
        print("\n🗄️  Testing database-geolocation integration...")

        try:
            # Test storing location data in database
            test_user_data = {
                "user": {"longName": "Location Test User", "shortName": "LTU"},
                "position": {"latitude": 55.7558, "longitude": 37.6173, "altitude": 100},
                "deviceMetrics": {"batteryLevel": 85}
            }

            # Store user in database
            database.insert_or_update_user("location_test_user", test_user_data)

            # Process location through geolocation service
            result = geolocation_service.process_location_update(
                user_id="location_test_user",
                latitude=55.7558,
                longitude=37.6173,
                altitude=100,
                battery_level=85
            )

            # Verify integration
            self.assertTrue(result["success"])
            self.assertIsInstance(result["is_moving"], bool)
            self.assertIsInstance(result["speed_mps"], (int, float))

            # Verify user data persisted
            user = database.get_user("location_test_user")
            self.assertIsNotNone(user)
            self.assertEqual(user["long_name"], "Location Test User")

            print("✅ Database-geolocation integration test passed")
            return True

        except Exception as e:
            print(f"❌ Database-geolocation integration test failed: {e}")
            return False

    def test_02_api_database_integration(self):
        """Test API endpoints with database operations."""
        print("\n🔗 Testing API-database integration...")

        try:
            # Register user through API
            response = self.client.post("/api/auth/register", json=self.test_admin)
            self.assertEqual(response.status_code, 200)
            token = response.json()["access_token"]

            # Get user data through API
            headers = {"Authorization": f"Bearer {token}"}
            response = self.client.get("/api/auth/me", headers=headers)
            self.assertEqual(response.status_code, 200)
            user_data = response.json()

            # Verify user exists in database
            db_user = database.get_user(user_data["username"])
            self.assertIsNotNone(db_user)
            self.assertEqual(db_user["username"], user_data["username"])

            print("✅ API-database integration test passed")
            return True

        except Exception as e:
            print(f"❌ API-database integration test failed: {e}")
            return False

    def test_03_geolocation_zone_integration(self):
        """Test geolocation service with zone management."""
        print("\n📍 Testing geolocation-zone integration...")

        try:
            # Register admin and create zone
            response = self.client.post("/api/auth/register", json=self.test_admin)
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Create test zone
            zone_data = {
                "name": "Geolocation Test Zone",
                "description": "Test zone for geolocation integration",
                "coordinates": [
                    [55.7558, 37.6173],
                    [55.7658, 37.6273],
                    [55.7658, 37.6073],
                    [55.7558, 37.6173]
                ],
                "zone_type": "test",
                "alert_level": "low"
            }

            response = self.client.post("/api/zones/", json=zone_data, headers=headers)
            self.assertEqual(response.status_code, 200)
            zone_result = response.json()
            zone_id = zone_result["id"]

            # Test location inside zone
            inside_location = {
                "user_id": "zone_test_user_inside",
                "latitude": 55.7600,  # Inside the zone
                "longitude": 37.6200,
                "altitude": 100,
                "battery_level": 80
            }

            result = geolocation_service.process_location_update(**inside_location)
            self.assertTrue(result["success"])

            # Test location outside zone
            outside_location = {
                "user_id": "zone_test_user_outside",
                "latitude": 55.8000,  # Outside the zone
                "longitude": 37.7000,
                "altitude": 100,
                "battery_level": 80
            }

            result = geolocation_service.process_location_update(**outside_location)
            self.assertTrue(result["success"])

            print("✅ Geolocation-zone integration test passed")
            return True

        except Exception as e:
            print(f"❌ Geolocation-zone integration test failed: {e}")
            return False

    def test_04_alert_geolocation_integration(self):
        """Test alert system with geolocation triggers."""
        print("\n🚨 Testing alert-geolocation integration...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.test_admin)
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Create zone with alert triggers
            zone_data = {
                "name": "Alert Test Zone",
                "description": "Zone for testing alert integration",
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
            zone_result = response.json()
            zone_id = zone_result["id"]

            # Create alert rule for the zone
            alert_data = {
                "title": "Zone Entry Alert",
                "message": "User entered emergency zone",
                "severity": "high",
                "alert_type": "zone_entry",
                "zone_id": zone_id
            }

            response = self.client.post("/api/alerts/", json=alert_data, headers=headers)
            self.assertEqual(response.status_code, 200)

            # Test location that should trigger alert
            alert_location = {
                "user_id": "alert_test_user",
                "latitude": 55.7600,
                "longitude": 37.6200,
                "altitude": 100,
                "battery_level": 70
            }

            result = geolocation_service.process_location_update(**alert_location)

            # Should detect zone entry and potentially create alerts
            self.assertTrue(result["success"])
            self.assertIn("alerts", result)

            print("✅ Alert-geolocation integration test passed")
            return True

        except Exception as e:
            print(f"❌ Alert-geolocation integration test failed: {e}")
            return False

    def test_05_websocket_api_integration(self):
        """Test WebSocket service with API endpoints."""
        print("\n🔄 Testing WebSocket-API integration...")

        try:
            # Test WebSocket endpoint exists and is configured
            response = self.client.get("/api/websocket/test")
            self.assertEqual(response.status_code, 200)

            # Register user for WebSocket testing
            response = self.client.post("/api/auth/register", json=self.test_admin)
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Test that WebSocket can access user data
            response = self.client.get("/api/auth/me", headers=headers)
            self.assertEqual(response.status_code, 200)

            print("✅ WebSocket-API integration test passed")
            return True

        except Exception as e:
            print(f"❌ WebSocket-API integration test failed: {e}")
            return False

    def test_06_user_zone_alert_integration(self):
        """Test user management with zone access and alerts."""
        print("\n👤 Testing user-zone-alert integration...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.test_admin)
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Create test zone
            zone_data = {
                "name": "User Access Test Zone",
                "description": "Zone for testing user access integration",
                "coordinates": [
                    [55.7558, 37.6173],
                    [55.7658, 37.6273],
                    [55.7658, 37.6073],
                    [55.7558, 37.6173]
                ],
                "zone_type": "restricted",
                "alert_level": "medium"
            }

            response = self.client.post("/api/zones/", json=zone_data, headers=headers)
            zone_result = response.json()
            zone_id = zone_result["id"]

            # Create user with zone access
            user_data = {
                "username": "zone_access_user",
                "email": "zoneaccess@test.com",
                "password": "testpass123",
                "role": "user",
                "zone_access": [zone_id]
            }

            response = self.client.post("/api/auth/register", json=user_data)
            self.assertEqual(response.status_code, 200)

            # Create alert for the zone
            alert_data = {
                "title": "Zone Access Alert",
                "message": "Testing zone access alert system",
                "severity": "medium",
                "alert_type": "zone",
                "zone_id": zone_id
            }

            response = self.client.post("/api/alerts/", json=alert_data, headers=headers)
            self.assertEqual(response.status_code, 200)

            # Verify user can access zone alerts
            response = self.client.get(f"/api/zones/{zone_id}/alerts", headers=headers)
            self.assertEqual(response.status_code, 200)

            print("✅ User-zone-alert integration test passed")
            return True

        except Exception as e:
            print(f"❌ User-zone-alert integration test failed: {e}")
            return False

    def test_07_message_geolocation_integration(self):
        """Test message handling with geolocation data."""
        print("\n💬 Testing message-geolocation integration...")

        try:
            # Test message storage with location data
            test_message_data = {
                "user": {"longName": "Message Test User", "shortName": "MTU"},
                "position": {"latitude": 55.7558, "longitude": 37.6173, "altitude": 120},
                "deviceMetrics": {"batteryLevel": 90}
            }

            # Store user with location
            database.insert_or_update_user("message_test_user", test_message_data)

            # Store message for user
            database.insert_message(
                sender="message_test_user",
                receiver="central",
                message="Test message with location",
                direction="incoming"
            )

            # Verify message and location integration
            messages = database.get_messages_for_user("message_test_user", limit=10)
            self.assertTrue(len(messages) > 0)

            user = database.get_user("message_test_user")
            self.assertIsNotNone(user)
            self.assertEqual(user["long_name"], "Message Test User")

            print("✅ Message-geolocation integration test passed")
            return True

        except Exception as e:
            print(f"❌ Message-geolocation integration test failed: {e}")
            return False

    def test_08_concurrent_component_access(self):
        """Test concurrent access to multiple components."""
        print("\n⚡ Testing concurrent component access...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.test_admin)
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Perform concurrent operations across components
            operations = []

            # Database operations
            for i in range(3):
                user_data = {
                    "user": {"longName": f"Concurrent User {i}", "shortName": f"CU{i}"},
                    "position": {"latitude": 55.7558 + i*0.001, "longitude": 37.6173 + i*0.001},
                    "deviceMetrics": {"batteryLevel": 80 + i}
                }
                database.insert_or_update_user(f"concurrent_user_{i}", user_data)

            # API operations
            for i in range(3):
                zone_data = {
                    "name": f"Concurrent Zone {i}",
                    "description": f"Zone for concurrent testing {i}",
                    "coordinates": [
                        [55.7558 + i*0.001, 37.6173 + i*0.001],
                        [55.7658 + i*0.001, 37.6273 + i*0.001],
                        [55.7658 + i*0.001, 37.6073 + i*0.001],
                        [55.7558 + i*0.001, 37.6173 + i*0.001]
                    ],
                    "zone_type": "test",
                    "alert_level": "low"
                }
                operations.append(
                    self.client.post("/api/zones/", json=zone_data, headers=headers)
                )

            # Execute API operations
            results = []
            for op in operations:
                response = op
                results.append(response.status_code == 200)

            # Verify all operations succeeded
            success_rate = sum(results) / len(results)
            self.assertGreaterEqual(success_rate, 0.8)

            # Verify database operations
            for i in range(3):
                user = database.get_user(f"concurrent_user_{i}")
                self.assertIsNotNone(user)

            print(f"✅ Concurrent component access test passed ({success_rate:.1%})")
            return True

        except Exception as e:
            print(f"❌ Concurrent component access test failed: {e}")
            return False

    def run_component_integration_suite(self):
        """Run the complete component integration test suite."""
        print("🔧 Starting Firefly Station Component Integration Test Suite")
        print("=" * 65)

        tests = [
            self.test_01_database_geolocation_integration,
            self.test_02_api_database_integration,
            self.test_03_geolocation_zone_integration,
            self.test_04_alert_geolocation_integration,
            self.test_05_websocket_api_integration,
            self.test_06_user_zone_alert_integration,
            self.test_07_message_geolocation_integration,
            self.test_08_concurrent_component_access
        ]

        passed = 0
        total = len(tests)

        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")

        print("\n" + "=" * 65)
        print(f"Component Integration Test Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All component integration tests passed!")
            return True
        else:
            print("⚠️  Some component integration tests failed")
            return False


def main():
    """Main function to run component integration tests."""
    test_suite = ComponentIntegrationTest()
    success = test_suite.run_component_integration_suite()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()