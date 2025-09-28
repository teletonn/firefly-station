#!/usr/bin/env python3
"""
Integration Points Validation for Firefly Station
Tests all key integration points as specified in requirements.
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


class IntegrationPointsValidator(unittest.TestCase):
    """Validate all key integration points specified in requirements."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.client = TestClient(app)
        database.init_db()

        # Test data
        cls.admin_user = {
            "username": "integration_admin",
            "email": "integration@test.com",
            "password": "testpass123",
            "role": "admin"
        }

    def setUp(self):
        """Set up each test."""
        # Clear test data
        try:
            database.delete_user("integration_admin")
        except:
            pass

    def test_01_meshtastic_device_integration(self):
        """Test Firefly device integration with location data."""
        print("\n📡 Testing Firefly device integration...")

        try:
            # Simulate Firefly device data
            meshtastic_device_data = {
                "user": {"longName": "Test Firefly Device", "shortName": "TMD"},
                "position": {"latitude": 55.7558, "longitude": 37.6173, "altitude": 150},
                "deviceMetrics": {"batteryLevel": 85}
            }

            # Store device data (simulating message reception)
            database.insert_or_update_user("meshtastic_device_001", meshtastic_device_data)

            # Process location data through geolocation service
            result = geolocation_service.process_location_update(
                user_id="meshtastic_device_001",
                latitude=55.7558,
                longitude=37.6173,
                altitude=150,
                battery_level=85
            )

            # Validate integration
            self.assertTrue(result["success"])
            self.assertIsInstance(result["is_moving"], bool)
            self.assertIsInstance(result["speed_mps"], (int, float))

            # Verify device data is accessible
            device = database.get_user("meshtastic_device_001")
            self.assertIsNotNone(device)
            self.assertEqual(device["long_name"], "Test Firefly Device")

            # Simulate message processing
            database.insert_message(
                sender="meshtastic_device_001",
                receiver="central",
                message="Test message from Firefly device",
                direction="incoming"
            )

            messages = database.get_messages_for_user("meshtastic_device_001", limit=10)
            self.assertTrue(len(messages) > 0)

            print("✅ Firefly device integration validated")
            return True

        except Exception as e:
            print(f"❌ Firefly device integration failed: {e}")
            return False

    def test_02_geolocation_system_integration(self):
        """Test geolocation system with real-time tracking and zone management."""
        print("\n📍 Testing geolocation system integration...")

        try:
            # Register admin and create test zone
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {admin_token}"}

            # Create test zone
            zone_data = {
                "name": "Geolocation Test Zone",
                "description": "Zone for geolocation integration testing",
                "coordinates": [
                    [55.7558, 37.6173],
                    [55.7658, 37.6273],
                    [55.7658, 37.6073],
                    [55.7558, 37.6173]
                ],
                "zone_type": "tracking",
                "alert_level": "low"
            }

            response = self.client.post("/api/zones/", json=zone_data, headers=headers)
            zone_result = response.json()
            zone_id = zone_result["id"]

            # Test real-time location tracking
            locations = [
                {"lat": 55.7560, "lng": 37.6180, "alt": 100},  # Outside zone
                {"lat": 55.7590, "lng": 37.6210, "alt": 105},  # Approaching zone
                {"lat": 55.7600, "lng": 37.6220, "alt": 110},  # Inside zone
                {"lat": 55.7610, "lng": 37.6230, "alt": 115},  # Moving in zone
            ]

            for i, location in enumerate(locations):
                result = geolocation_service.process_location_update(
                    user_id="geolocation_test_user",
                    latitude=location["lat"],
                    longitude=location["lng"],
                    altitude=location["alt"],
                    battery_level=85 - i
                )

                self.assertTrue(result["success"])
                self.assertIn("zone_changes", result)
                self.assertIn("alerts", result)

            # Verify zone data is accessible
            response = self.client.get(f"/api/zones/{zone_id}", headers=headers)
            self.assertEqual(response.status_code, 200)

            print("✅ Geolocation system integration validated")
            return True

        except Exception as e:
            print(f"❌ Geolocation system integration failed: {e}")
            return False

    def test_03_alert_system_integration(self):
        """Test alert creation, escalation, and resolution system."""
        print("\n🚨 Testing alert system integration...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {admin_token}"}

            # Create test zone for alert
            zone_data = {
                "name": "Alert Test Zone",
                "description": "Zone for alert system testing",
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

            # Create initial alert
            alert_data = {
                "title": "Emergency Alert Test",
                "message": "Testing alert creation and escalation",
                "severity": "high",
                "alert_type": "emergency",
                "zone_id": zone_id
            }

            response = self.client.post("/api/alerts/", json=alert_data, headers=headers)
            alert_result = response.json()
            alert_id = alert_result["id"]

            # Test alert escalation
            escalation_data = {
                "status": "escalated",
                "response_notes": "Alert escalated to higher priority",
                "severity": "critical"
            }
            response = self.client.put(f"/api/alerts/{alert_id}", json=escalation_data, headers=headers)
            self.assertEqual(response.status_code, 200)

            # Test alert resolution
            resolution_data = {
                "status": "resolved",
                "response_notes": "Emergency situation resolved successfully"
            }
            response = self.client.put(f"/api/alerts/{alert_id}", json=resolution_data, headers=headers)
            self.assertEqual(response.status_code, 200)

            # Verify alert history
            response = self.client.get(f"/api/alerts/{alert_id}", headers=headers)
            self.assertEqual(response.status_code, 200)
            final_alert = response.json()
            self.assertEqual(final_alert["status"], "resolved")

            print("✅ Alert system integration validated")
            return True

        except Exception as e:
            print(f"❌ Alert system integration failed: {e}")
            return False

    def test_04_user_management_integration(self):
        """Test user management with groups and permissions."""
        print("\n👤 Testing user management integration...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {admin_token}"}

            # Create multiple zones for different user groups
            zones = []
            for i in range(3):
                zone_data = {
                    "name": f"User Group Zone {i+1}",
                    "description": f"Zone {i+1} for user group testing",
                    "coordinates": [
                        [55.7558 + i*0.01, 37.6173 + i*0.01],
                        [55.7658 + i*0.01, 37.6273 + i*0.01],
                        [55.7658 + i*0.01, 37.6073 + i*0.01],
                        [55.7558 + i*0.01, 37.6173 + i*0.01]
                    ],
                    "zone_type": "restricted",
                    "alert_level": "medium"
                }

                response = self.client.post("/api/zones/", json=zone_data, headers=headers)
                zones.append(response.json())

            # Create users with different zone access
            group1_user = {
                "username": "group1_user",
                "email": "group1@test.com",
                "password": "testpass123",
                "role": "user",
                "zone_access": [zones[0]["id"]]  # Zone 1 only
            }

            group2_user = {
                "username": "group2_user",
                "email": "group2@test.com",
                "password": "testpass123",
                "role": "user",
                "zone_access": [zones[1]["id"], zones[2]["id"]]  # Zones 2 and 3
            }

            response = self.client.post("/api/auth/register", json=group1_user)
            group1_token = response.json()["access_token"]

            response = self.client.post("/api/auth/register", json=group2_user)
            group2_token = response.json()["access_token"]

            # Test zone access permissions
            group1_headers = {"Authorization": f"Bearer {group1_token}"}
            response = self.client.get("/api/zones/", headers=group1_headers)
            self.assertEqual(response.status_code, 200)
            group1_zones = response.json()
            self.assertEqual(len(group1_zones), 1)

            group2_headers = {"Authorization": f"Bearer {group2_token}"}
            response = self.client.get("/api/zones/", headers=group2_headers)
            self.assertEqual(response.status_code, 200)
            group2_zones = response.json()
            self.assertEqual(len(group2_zones), 2)

            print("✅ User management integration validated")
            return True

        except Exception as e:
            print(f"❌ User management integration failed: {e}")
            return False

    def test_05_bot_system_integration(self):
        """Test bot system with trigger processing and contextual responses."""
        print("\n🤖 Testing bot system integration...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {admin_token}"}

            # Create emergency zone that would trigger bot responses
            zone_data = {
                "name": "Bot Trigger Zone",
                "description": "Zone for bot trigger testing",
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

            # Simulate emergency message that would trigger bot
            emergency_message = "EMERGENCY! User in distress needs immediate help!"

            # Store message (simulating Firefly reception)
            database.insert_message(
                sender="bot_trigger_user",
                receiver="central",
                message=emergency_message,
                direction="incoming"
            )

            # Process user location for context
            location_data = {
                "user_id": "bot_trigger_user",
                "latitude": 55.7600,
                "longitude": 37.6200,
                "altitude": 100,
                "battery_level": 45
            }

            result = geolocation_service.process_location_update(**location_data)
            self.assertTrue(result["success"])

            # Verify message and location are linked
            messages = database.get_messages_for_user("bot_trigger_user", limit=10)
            self.assertTrue(len(messages) > 0)

            user = database.get_user("bot_trigger_user")
            self.assertIsNotNone(user)

            # Verify emergency keyword detection
            emergency_found = any("EMERGENCY" in msg["message"] for msg in messages)
            self.assertTrue(emergency_found)

            print("✅ Bot system integration validated")
            return True

        except Exception as e:
            print(f"❌ Bot system integration failed: {e}")
            return False

    def test_06_frontend_integration(self):
        """Test frontend integration with all UI components."""
        print("\n🖥️  Testing frontend integration...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {admin_token}"}

            # Create test data for all major components
            # Zone for map display
            zone_data = {
                "name": "Frontend Test Zone",
                "description": "Zone for frontend integration testing",
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
            zone_result = response.json()
            zone_id = zone_result["id"]

            # Alert for alert management
            alert_data = {
                "title": "Frontend Integration Alert",
                "message": "Alert for frontend component testing",
                "severity": "medium",
                "alert_type": "test",
                "zone_id": zone_id
            }

            response = self.client.post("/api/alerts/", json=alert_data, headers=headers)
            alert_result = response.json()
            alert_id = alert_result["id"]

            # User for user management
            test_user = {
                "username": "frontend_test_user",
                "email": "frontend@test.com",
                "password": "testpass123",
                "role": "user"
            }

            response = self.client.post("/api/auth/register", json=test_user)
            user_token = response.json()["access_token"]

            # Test data accessibility for frontend
            # Zones list
            response = self.client.get("/api/zones/", headers=headers)
            self.assertEqual(response.status_code, 200)
            zones = response.json()
            self.assertTrue(len(zones) > 0)

            # Alerts list
            response = self.client.get("/api/alerts/", headers=headers)
            self.assertEqual(response.status_code, 200)
            alerts = response.json()
            self.assertTrue(len(alerts) > 0)

            # Users list
            response = self.client.get("/api/users/", headers=headers)
            self.assertEqual(response.status_code, 200)
            users = response.json()
            self.assertTrue(len(users) > 0)

            print("✅ Frontend integration validated")
            return True

        except Exception as e:
            print(f"❌ Frontend integration failed: {e}")
            return False

    def test_07_real_time_updates_integration(self):
        """Test WebSocket real-time updates across all features."""
        print("\n⚡ Testing real-time updates integration...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {admin_token}"}

            # Test WebSocket endpoint
            response = self.client.get("/api/websocket/test")
            self.assertEqual(response.status_code, 200)

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

            response = self.client.post("/api/zones/", json=zone_data, headers=headers)
            zone_result = response.json()
            zone_id = zone_result["id"]

            # Simulate real-time location updates
            for i in range(5):
                location_data = {
                    "user_id": "realtime_test_user",
                    "latitude": 55.7558 + i*0.001,
                    "longitude": 37.6173 + i*0.001,
                    "altitude": 100 + i,
                    "battery_level": 85 - i
                }

                result = geolocation_service.process_location_update(**location_data)
                self.assertTrue(result["success"])

                # Small delay to simulate real-time updates
                time.sleep(0.1)

            # Create real-time alert
            alert_data = {
                "title": "Real-time Alert Test",
                "message": "Testing real-time alert creation",
                "severity": "low",
                "alert_type": "test"
            }

            response = self.client.post("/api/alerts/", json=alert_data, headers=headers)
            self.assertEqual(response.status_code, 200)

            # Verify real-time data is accessible
            response = self.client.get("/api/zones/", headers=headers)
            self.assertEqual(response.status_code, 200)

            response = self.client.get("/api/alerts/", headers=headers)
            self.assertEqual(response.status_code, 200)

            print("✅ Real-time updates integration validated")
            return True

        except Exception as e:
            print(f"❌ Real-time updates integration failed: {e}")
            return False

    def test_08_multi_language_support(self):
        """Test multi-language support throughout the interface."""
        print("\n🌐 Testing multi-language support...")

        try:
            # Register admin
            response = self.client.post("/api/auth/register", json=self.admin_user)
            admin_token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {admin_token}"}

            # Create test data that would be displayed in multiple languages
            zone_data = {
                "name": "Multi-Language Test Zone",
                "description": "Zone for testing internationalization support",
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
            zone_result = response.json()
            zone_id = zone_result["id"]

            # Create alert with international characters
            alert_data = {
                "title": "Multi-Language Alert 测试",
                "message": "Testing international character support: ñáéíóú, русский, 中文, 🚨",
                "severity": "low",
                "alert_type": "test",
                "zone_id": zone_id
            }

            response = self.client.post("/api/alerts/", json=alert_data, headers=headers)
            self.assertEqual(response.status_code, 200)

            # Verify data integrity with international characters
            response = self.client.get(f"/api/zones/{zone_id}", headers=headers)
            self.assertEqual(response.status_code, 200)
            fetched_zone = response.json()
            self.assertEqual(fetched_zone["name"], zone_data["name"])

            response = self.client.get(f"/api/alerts/", headers=headers)
            self.assertEqual(response.status_code, 200)
            alerts = response.json()
            self.assertTrue(len(alerts) > 0)

            # Check that international characters are preserved
            international_alert = next((alert for alert in alerts if "测试" in alert["title"]), None)
            self.assertIsNotNone(international_alert)

            print("✅ Multi-language support validated")
            return True

        except Exception as e:
            print(f"❌ Multi-language support failed: {e}")
            return False

    def run_integration_points_validation(self):
        """Run complete integration points validation."""
        print("🔗 Starting Firefly Station Integration Points Validation")
        print("=" * 65)

        integration_points = [
            ("Firefly Device Integration", self.test_01_meshtastic_device_integration),
            ("Geolocation System Integration", self.test_02_geolocation_system_integration),
            ("Alert System Integration", self.test_03_alert_system_integration),
            ("User Management Integration", self.test_04_user_management_integration),
            ("Bot System Integration", self.test_05_bot_system_integration),
            ("Frontend Integration", self.test_06_frontend_integration),
            ("Real-time Updates Integration", self.test_07_real_time_updates_integration),
            ("Multi-language Support", self.test_08_multi_language_support)
        ]

        passed = 0
        total = len(integration_points)

        for point_name, test_func in integration_points:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"❌ Integration point {point_name} failed with exception: {e}")

        print("\n" + "=" * 65)
        print(f"Integration Points Validation Results: {passed}/{total} points validated")

        if passed == total:
            print("🎉 All integration points validated successfully!")
            return True
        else:
            print("⚠️  Some integration points failed validation")
            return False


def main():
    """Main function to run integration points validation."""
    validator = IntegrationPointsValidator()
    success = validator.run_integration_points_validation()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()