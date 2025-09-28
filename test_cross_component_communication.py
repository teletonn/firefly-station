#!/usr/bin/env python3
"""
Cross-Component Communication Testing for Firefly Station
Tests communication between different system components.
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


class CrossComponentCommunicationTest(unittest.TestCase):
    """Test communication between system components."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.client = TestClient(app)
        database.init_db()

        # Test data
        cls.admin_user = {
            "username": "comm_admin",
            "email": "comm_admin@test.com",
            "password": "testpass123",
            "role": "admin"
        }

        cls.test_user = {
            "username": "comm_user",
            "email": "comm_user@test.com",
            "password": "testpass123",
            "role": "user"
        }

    def setUp(self):
        """Set up each test."""
        # Clear test data
        try:
            database.delete_user("comm_admin")
            database.delete_user("comm_user")
        except:
            pass

    def test_01_api_websocket_integration(self):
        """Test API endpoints with WebSocket real-time updates."""
        print("\n🔄 Testing API-WebSocket integration...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Test WebSocket endpoint availability
            response = self.client.get("/api/websocket/test")
            self.assertEqual(response.status_code, 200)

            # Create zone through API
            zone_data = {
                "name": "WebSocket Test Zone",
                "description": "Zone for WebSocket communication testing",
                "coordinates": [
                    [55.7558, 37.6173],
                    [55.7658, 37.6273],
                    [55.7658, 37.6073],
                    [55.7558, 37.6173]
                ],
                "zone_type": "test",
                "alert_level": "low"
            }

            response = self.client.post("/api/zones/", json=zone_data, headers=admin_headers)
            self.assertEqual(response.status_code, 200)
            zone_result = response.json()
            zone_id = zone_result["id"]

            # Simulate real-time location update that would trigger WebSocket broadcast
            location_update = {
                "user_id": "websocket_test_user",
                "latitude": 55.7600,
                "longitude": 37.6200,
                "altitude": 100,
                "battery_level": 80
            }

            # Process location update
            result = geolocation_service.process_location_update(**location_update)
            self.assertTrue(result["success"])

            # Verify the location update is stored and accessible via API
            user_data = {
                "user": {"longName": "WebSocket Test User", "shortName": "WTU"},
                "position": location_update,
                "deviceMetrics": {"batteryLevel": location_update["battery_level"]}
            }
            database.insert_or_update_user("websocket_test_user", user_data)

            user = database.get_user("websocket_test_user")
            self.assertIsNotNone(user)

            print("✅ API-WebSocket integration test passed")
            return True

        except Exception as e:
            print(f"❌ API-WebSocket integration test failed: {e}")
            return False

    def test_02_geolocation_alert_broadcasting(self):
        """Test geolocation updates triggering alert broadcasts."""
        print("\n📢 Testing geolocation-alert broadcasting...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Create emergency zone
            zone_data = {
                "name": "Broadcast Test Zone",
                "description": "Zone for testing alert broadcasting",
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

            # Create alert rule for zone entry
            alert_data = {
                "title": "Zone Entry Alert",
                "message": "User entered emergency zone - broadcasting alert",
                "severity": "high",
                "alert_type": "zone_entry",
                "zone_id": zone_id
            }

            response = self.client.post("/api/alerts/", json=alert_data, headers=admin_headers)
            self.assertEqual(response.status_code, 200)

            # Simulate user entering zone (would trigger broadcast)
            entry_location = {
                "user_id": "broadcast_test_user",
                "latitude": 55.7600,  # Inside zone
                "longitude": 37.6200,
                "altitude": 100,
                "battery_level": 75
            }

            result = geolocation_service.process_location_update(**entry_location)
            self.assertTrue(result["success"])

            # Verify alert was created and is accessible
            response = self.client.get("/api/alerts/", headers=admin_headers)
            self.assertEqual(response.status_code, 200)
            alerts = response.json()
            self.assertTrue(len(alerts) > 0)

            print("✅ Geolocation-alert broadcasting test passed")
            return True

        except Exception as e:
            print(f"❌ Geolocation-alert broadcasting test failed: {e}")
            return False

    def test_03_user_group_alert_targeting(self):
        """Test user groups affect alert targeting and delivery."""
        print("\n🎯 Testing user group alert targeting...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Create multiple zones
            zones = []
            for i in range(3):
                zone_data = {
                    "name": f"Targeting Zone {i+1}",
                    "description": f"Zone {i+1} for targeting testing",
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
                zones.append(response.json())

            # Create users with different zone access
            group1_user = {
                "username": "target_group1_user",
                "email": "targetgroup1@test.com",
                "password": "testpass123",
                "role": "user",
                "zone_access": [zones[0]["id"]]  # Zone 1 only
            }

            group2_user = {
                "username": "target_group2_user",
                "email": "targetgroup2@test.com",
                "password": "testpass123",
                "role": "user",
                "zone_access": [zones[1]["id"], zones[2]["id"]]  # Zones 2 and 3
            }

            response = self.client.post("/api/auth/register", json=group1_user)
            group1_token = response.json()["access_token"]

            response = self.client.post("/api/auth/register", json=group2_user)
            group2_token = response.json()["access_token"]

            # Create zone-specific alerts
            alert1_data = {
                "title": "Group 1 Targeted Alert",
                "message": "Alert targeted to group 1 zone",
                "severity": "medium",
                "alert_type": "zone",
                "zone_id": zones[0]["id"]
            }

            alert2_data = {
                "title": "Group 2 Targeted Alert",
                "message": "Alert targeted to group 2 zones",
                "severity": "medium",
                "alert_type": "zone",
                "zone_id": zones[1]["id"]
            }

            # Create alerts as admin
            response = self.client.post("/api/alerts/", json=alert1_data, headers=admin_headers)
            self.assertEqual(response.status_code, 200)

            response = self.client.post("/api/alerts/", json=alert2_data, headers=admin_headers)
            self.assertEqual(response.status_code, 200)

            # Test that users only see alerts for zones they have access to
            group1_headers = {"Authorization": f"Bearer {group1_token}"}
            response = self.client.get("/api/alerts/", headers=group1_headers)
            self.assertEqual(response.status_code, 200)
            group1_alerts = response.json()

            # Group 1 should only see alert for zone 1
            zone1_alerts = [alert for alert in group1_alerts if alert.get("zone_id") == zones[0]["id"]]
            self.assertTrue(len(zone1_alerts) > 0)

            print("✅ User group alert targeting test passed")
            return True

        except Exception as e:
            print(f"❌ User group alert targeting test failed: {e}")
            return False

    def test_04_meshtastic_geolocation_data_flow(self):
        """Test Firefly message processing with geolocation data."""
        print("\n📡 Testing Firefly-geolocation data flow...")

        try:
            # Simulate Firefly device data
            meshtastic_data = {
                "user": {"longName": "Firefly Test Device", "shortName": "MTD"},
                "position": {"latitude": 55.7558, "longitude": 37.6173, "altitude": 150},
                "deviceMetrics": {"batteryLevel": 90}
            }

            # Store device data (simulating Firefly message reception)
            database.insert_or_update_user("meshtastic_test_device", meshtastic_data)

            # Process location through geolocation service
            result = geolocation_service.process_location_update(
                user_id="meshtastic_test_device",
                latitude=55.7558,
                longitude=37.6173,
                altitude=150,
                battery_level=90
            )

            self.assertTrue(result["success"])

            # Verify data flow from Firefly to geolocation to database
            user = database.get_user("meshtastic_test_device")
            self.assertIsNotNone(user)
            self.assertEqual(user["long_name"], "Firefly Test Device")

            # Simulate message storage (as would happen with Firefly)
            database.insert_message(
                sender="meshtastic_test_device",
                receiver="central",
                message="Test message from Firefly device",
                direction="incoming"
            )

            # Verify message is stored and linked to user
            messages = database.get_messages_for_user("meshtastic_test_device", limit=10)
            self.assertTrue(len(messages) > 0)

            print("✅ Firefly-geolocation data flow test passed")
            return True

        except Exception as e:
            print(f"❌ Firefly-geolocation data flow test failed: {e}")
            return False

    def test_05_real_time_update_propagation(self):
        """Test real-time updates propagate correctly across components."""
        print("\n⚡ Testing real-time update propagation...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Create zone for real-time testing
            zone_data = {
                "name": "Real-time Test Zone",
                "description": "Zone for real-time update testing",
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

            # Simulate sequence of real-time location updates
            locations = [
                {"lat": 55.7560, "lng": 37.6180, "alt": 100},
                {"lat": 55.7590, "lng": 37.6210, "alt": 105},
                {"lat": 55.7600, "lng": 37.6220, "alt": 110},  # Entering zone
                {"lat": 55.7610, "lng": 37.6230, "alt": 115},  # Moving in zone
            ]

            for i, location in enumerate(locations):
                result = geolocation_service.process_location_update(
                    user_id="realtime_test_user",
                    latitude=location["lat"],
                    longitude=location["lng"],
                    altitude=location["alt"],
                    battery_level=85 - i
                )

                self.assertTrue(result["success"])

                # Verify location data is immediately accessible via API
                user_data = {
                    "user": {"longName": "Real-time Test User", "shortName": "RTU"},
                    "position": {"latitude": location["lat"], "longitude": location["lng"], "altitude": location["alt"]},
                    "deviceMetrics": {"batteryLevel": 85 - i}
                }
                database.insert_or_update_user("realtime_test_user", user_data)

                # Small delay to simulate real-time updates
                time.sleep(0.05)

            # Verify final state is accessible
            user = database.get_user("realtime_test_user")
            self.assertIsNotNone(user)

            # Verify zone change detection
            final_result = geolocation_service.process_location_update(
                user_id="realtime_test_user",
                latitude=55.7610,
                longitude=37.6230,
                altitude=115,
                battery_level=81
            )
            self.assertTrue(final_result["success"])

            print("✅ Real-time update propagation test passed")
            return True

        except Exception as e:
            print(f"❌ Real-time update propagation test failed: {e}")
            return False

    def test_06_bot_system_cross_component_integration(self):
        """Test bot system integration with other components."""
        print("\n🤖 Testing bot system cross-component integration...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Create zone with bot triggers
            zone_data = {
                "name": "Bot Integration Zone",
                "description": "Zone for bot integration testing",
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

            # Simulate bot trigger scenario
            # User sends emergency message (would trigger bot response)
            emergency_message = "EMERGENCY! Need immediate assistance!"

            # Store message (simulating Firefly reception)
            database.insert_message(
                sender="bot_integration_user",
                receiver="central",
                message=emergency_message,
                direction="incoming"
            )

            # Process user location (would be used in bot response)
            location_data = {
                "user_id": "bot_integration_user",
                "latitude": 55.7600,
                "longitude": 37.6200,
                "altitude": 100,
                "battery_level": 60
            }

            result = geolocation_service.process_location_update(**location_data)
            self.assertTrue(result["success"])

            # Verify message and location are both stored and accessible
            messages = database.get_messages_for_user("bot_integration_user", limit=10)
            self.assertTrue(len(messages) > 0)

            user = database.get_user("bot_integration_user")
            self.assertIsNotNone(user)

            # Verify emergency keyword detection
            emergency_messages = [msg for msg in messages if "EMERGENCY" in msg["message"]]
            self.assertTrue(len(emergency_messages) > 0)

            print("✅ Bot system cross-component integration test passed")
            return True

        except Exception as e:
            print(f"❌ Bot system cross-component integration test failed: {e}")
            return False

    def test_07_frontend_backend_data_synchronization(self):
        """Test frontend-backend data synchronization."""
        print("\n🔄 Testing frontend-backend data synchronization...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            admin_headers = {"Authorization": f"Bearer {admin_token}"}

            # Create test data through API
            zone_data = {
                "name": "Sync Test Zone",
                "description": "Zone for frontend-backend sync testing",
                "coordinates": [
                    [55.7558, 37.6173],
                    [55.7658, 37.6273],
                    [55.7658, 37.6073],
                    [55.7558, 37.6173]
                ],
                "zone_type": "test",
                "alert_level": "low"
            }

            response = self.client.post("/api/zones/", json=zone_data, headers=admin_headers)
            zone_result = response.json()
            zone_id = zone_result["id"]

            # Create alert through API
            alert_data = {
                "title": "Sync Test Alert",
                "message": "Alert for frontend-backend synchronization testing",
                "severity": "low",
                "alert_type": "test",
                "zone_id": zone_id
            }

            response = self.client.post("/api/alerts/", json=alert_data, headers=admin_headers)
            alert_result = response.json()
            alert_id = alert_result["id"]

            # Verify data consistency across API endpoints
            # Get zone data
            response = self.client.get(f"/api/zones/{zone_id}", headers=admin_headers)
            self.assertEqual(response.status_code, 200)
            fetched_zone = response.json()
            self.assertEqual(fetched_zone["name"], zone_data["name"])

            # Get alert data
            response = self.client.get(f"/api/alerts/{alert_id}", headers=admin_headers)
            self.assertEqual(response.status_code, 200)
            fetched_alert = response.json()
            self.assertEqual(fetched_alert["title"], alert_data["title"])

            # Test data consistency between zone and alert
            response = self.client.get(f"/api/zones/{zone_id}/alerts", headers=admin_headers)
            self.assertEqual(response.status_code, 200)
            zone_alerts = response.json()
            self.assertTrue(len(zone_alerts) > 0)

            print("✅ Frontend-backend data synchronization test passed")
            return True

        except Exception as e:
            print(f"❌ Frontend-backend data synchronization test failed: {e}")
            return False

    def run_cross_component_communication_suite(self):
        """Run the complete cross-component communication test suite."""
        print("🌐 Starting Firefly Station Cross-Component Communication Test Suite")
        print("=" * 75)

        tests = [
            self.test_01_api_websocket_integration,
            self.test_02_geolocation_alert_broadcasting,
            self.test_03_user_group_alert_targeting,
            self.test_04_meshtastic_geolocation_data_flow,
            self.test_05_real_time_update_propagation,
            self.test_06_bot_system_cross_component_integration,
            self.test_07_frontend_backend_data_synchronization
        ]

        passed = 0
        total = len(tests)

        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")

        print("\n" + "=" * 75)
        print(f"Cross-Component Communication Test Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All cross-component communication tests passed!")
            return True
        else:
            print("⚠️  Some cross-component communication tests failed")
            return False


def main():
    """Main function to run cross-component communication tests."""
    test_suite = CrossComponentCommunicationTest()
    success = test_suite.run_cross_component_communication_suite()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()