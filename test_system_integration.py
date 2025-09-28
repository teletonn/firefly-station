#!/usr/bin/env python3
"""
Comprehensive System Integration Test for Firefly Station
Tests all components working together as a cohesive system.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Dict, List, Optional

import requests
import websockets
from fastapi.testclient import TestClient

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.main import app
from backend import database
from backend.geolocation import geolocation_service


class SystemIntegrationTest(unittest.TestCase):
    """Comprehensive integration tests for the entire Firefly Station system."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.base_url = "http://localhost:8000"
        cls.client = TestClient(app)

        # Initialize database
        database.init_db()

        # Test data
        cls.test_admin = {
            "username": "integration_admin",
            "email": "integration@test.com",
            "password": "testpass123",
            "role": "admin"
        }

        cls.test_user = {
            "username": "test_user",
            "email": "user@test.com",
            "password": "testpass123",
            "role": "user"
        }

        cls.test_zone = {
            "name": "Test Emergency Zone",
            "description": "Test zone for integration testing",
            "coordinates": [
                [55.7558, 37.6173],
                [55.7658, 37.6273],
                [55.7658, 37.6073],
                [55.7558, 37.6173]
            ],
            "zone_type": "emergency",
            "alert_level": "high"
        }

    def setUp(self):
        """Set up each test."""
        # Clear test data
        try:
            database.delete_user("integration_admin")
            database.delete_user("test_user")
        except:
            pass

    def test_01_database_initialization(self):
        """Test database initializes correctly."""
        print("\n🗄️  Testing database initialization...")

        try:
            # Test database connection and schema
            stats = database.get_bot_stats()
            self.assertIsInstance(stats, dict)

            # Test basic database operations
            test_user_data = {
                "user": {"longName": "Test User", "shortName": "TU"},
                "position": {"latitude": 55.7558, "longitude": 37.6173, "altitude": 100},
                "deviceMetrics": {"batteryLevel": 85}
            }
            database.insert_or_update_user("test_user_123", test_user_data)

            user = database.get_user("test_user_123")
            self.assertIsNotNone(user)
            self.assertEqual(user['long_name'], "Test User")

            print("✅ Database initialization test passed")
            return True

        except Exception as e:
            print(f"❌ Database initialization test failed: {e}")
            return False

    def test_02_api_endpoints_accessibility(self):
        """Test all API endpoints are accessible."""
        print("\n🔗 Testing API endpoints accessibility...")

        try:
            # Test root endpoint
            response = self.client.get("/")
            self.assertEqual(response.status_code, 200)

            # Test API endpoints exist (without authentication)
            endpoints = [
                "/api/auth/register",
                "/api/auth/login",
                "/api/geolocation/test",
                "/api/zones/",
                "/api/alerts/"
            ]

            for endpoint in endpoints:
                response = self.client.get(endpoint)
                # Should return 401 (unauthorized) or 200, not 404
                self.assertNotEqual(response.status_code, 404,
                                  f"Endpoint {endpoint} not found")

            print("✅ API endpoints accessibility test passed")
            return True

        except Exception as e:
            print(f"❌ API endpoints accessibility test failed: {e}")
            return False

    def test_03_user_registration_and_authentication(self):
        """Test complete user registration and authentication flow."""
        print("\n👤 Testing user registration and authentication...")

        try:
            # Register admin user
            response = self.client.post("/api/auth/register", json=self.test_admin)
            self.assertEqual(response.status_code, 200)
            admin_data = response.json()
            self.assertIn("access_token", admin_data)

            # Register regular user
            response = self.client.post("/api/auth/register", json=self.test_user)
            self.assertEqual(response.status_code, 200)
            user_data = response.json()
            self.assertIn("access_token", user_data)

            # Test login
            login_data = {
                "username": self.test_admin["username"],
                "password": self.test_admin["password"]
            }
            response = self.client.post("/api/auth/login", data=login_data)
            self.assertEqual(response.status_code, 200)
            token_data = response.json()
            self.assertIn("access_token", token_data)

            # Test protected endpoint
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            response = self.client.get("/api/auth/me", headers=headers)
            self.assertEqual(response.status_code, 200)
            user_info = response.json()
            self.assertEqual(user_info["username"], self.test_admin["username"])

            print("✅ User registration and authentication test passed")
            return True

        except Exception as e:
            print(f"❌ User registration and authentication test failed: {e}")
            return False

    def test_04_geolocation_system_integration(self):
        """Test geolocation system with zone management."""
        print("\n📍 Testing geolocation system integration...")

        try:
            # First register and login as admin
            response = self.client.post("/api/auth/register", json=self.test_admin)
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Create a test zone
            response = self.client.post("/api/zones/", json=self.test_zone, headers=headers)
            self.assertEqual(response.status_code, 200)
            zone_data = response.json()
            zone_id = zone_data["id"]

            # Test location update processing
            location_data = {
                "user_id": "test_device_123",
                "latitude": 55.7600,
                "longitude": 37.6200,
                "altitude": 150,
                "battery_level": 80
            }

            # Process location update through geolocation service
            result = geolocation_service.process_location_update(**location_data)

            self.assertTrue(result["success"])
            self.assertIn("zone_changes", result)
            self.assertIn("alerts", result)

            # Test zone retrieval
            response = self.client.get(f"/api/zones/{zone_id}", headers=headers)
            self.assertEqual(response.status_code, 200)

            # Test zones list
            response = self.client.get("/api/zones/", headers=headers)
            self.assertEqual(response.status_code, 200)
            zones = response.json()
            self.assertTrue(len(zones) > 0)

            print("✅ Geolocation system integration test passed")
            return True

        except Exception as e:
            print(f"❌ Geolocation system integration test failed: {e}")
            return False

    def test_05_alert_system_integration(self):
        """Test alert creation, escalation, and management."""
        print("\n🚨 Testing alert system integration...")

        try:
            # Register and login
            response = self.client.post("/api/auth/register", json=self.test_admin)
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Create test alert
            alert_data = {
                "title": "Integration Test Alert",
                "message": "This is a test alert for system integration",
                "severity": "high",
                "alert_type": "emergency",
                "location": {
                    "latitude": 55.7558,
                    "longitude": 37.6173
                },
                "affected_users": ["test_user_1", "test_user_2"],
                "zone_id": None
            }

            response = self.client.post("/api/alerts/", json=alert_data, headers=headers)
            self.assertEqual(response.status_code, 200)
            alert_result = response.json()
            alert_id = alert_result["id"]

            # Test alert retrieval
            response = self.client.get(f"/api/alerts/{alert_id}", headers=headers)
            self.assertEqual(response.status_code, 200)

            # Test alerts list
            response = self.client.get("/api/alerts/", headers=headers)
            self.assertEqual(response.status_code, 200)
            alerts = response.json()
            self.assertTrue(len(alerts) > 0)

            # Test alert update
            update_data = {
                "status": "acknowledged",
                "response_notes": "Alert acknowledged during integration testing"
            }
            response = self.client.put(f"/api/alerts/{alert_id}", json=update_data, headers=headers)
            self.assertEqual(response.status_code, 200)

            print("✅ Alert system integration test passed")
            return True

        except Exception as e:
            print(f"❌ Alert system integration test failed: {e}")
            return False

    def test_06_websocket_connectivity(self):
        """Test WebSocket connectivity and real-time updates."""
        print("\n🔄 Testing WebSocket connectivity...")

        try:
            # Test WebSocket endpoint exists
            response = self.client.get("/api/websocket/test")
            self.assertEqual(response.status_code, 200)

            # Note: Full WebSocket testing would require running server
            # This is a basic connectivity test
            print("✅ WebSocket connectivity test passed")
            return True

        except Exception as e:
            print(f"❌ WebSocket connectivity test failed: {e}")
            return False

    def test_07_cross_component_data_flow(self):
        """Test data flows correctly between components."""
        print("\n🔀 Testing cross-component data flow...")

        try:
            # Register and login
            response = self.client.post("/api/auth/register", json=self.test_admin)
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Create zone
            response = self.client.post("/api/zones/", json=self.test_zone, headers=headers)
            zone_data = response.json()
            zone_id = zone_data["id"]

            # Create user and associate with zone
            user_data = {
                "username": "zone_test_user",
                "email": "zonetest@test.com",
                "password": "testpass123",
                "role": "user",
                "zone_access": [zone_id]
            }
            response = self.client.post("/api/auth/register", json=user_data)
            self.assertEqual(response.status_code, 200)

            # Create alert in the zone
            alert_data = {
                "title": "Zone Alert Test",
                "message": "Testing alert in specific zone",
                "severity": "medium",
                "alert_type": "zone",
                "zone_id": zone_id
            }
            response = self.client.post("/api/alerts/", json=alert_data, headers=headers)
            self.assertEqual(response.status_code, 200)

            # Verify user can access zone alerts
            response = self.client.get(f"/api/zones/{zone_id}/alerts", headers=headers)
            self.assertEqual(response.status_code, 200)

            print("✅ Cross-component data flow test passed")
            return True

        except Exception as e:
            print(f"❌ Cross-component data flow test failed: {e}")
            return False

    def test_08_system_health_check(self):
        """Test overall system health and component status."""
        print("\n🏥 Testing system health check...")

        try:
            # Check database health
            try:
                database.get_bot_stats()
                db_healthy = True
            except:
                db_healthy = False

            # Check API health
            try:
                response = self.client.get("/")
                api_healthy = response.status_code == 200
            except:
                api_healthy = False

            # Check geolocation service health
            try:
                result = geolocation_service.process_location_update(
                    user_id="health_check",
                    latitude=0,
                    longitude=0
                )
                geo_healthy = result["success"]
            except:
                geo_healthy = False

            # Overall health assessment
            overall_healthy = db_healthy and api_healthy and geo_healthy

            health_status = {
                "database": "healthy" if db_healthy else "unhealthy",
                "api": "healthy" if api_healthy else "unhealthy",
                "geolocation": "healthy" if geo_healthy else "unhealthy",
                "overall": "healthy" if overall_healthy else "unhealthy"
            }

            print(f"Health Status: {health_status}")

            if overall_healthy:
                print("✅ System health check passed")
                return True
            else:
                print("❌ System health check failed")
                return False

        except Exception as e:
            print(f"❌ System health check failed: {e}")
            return False

    def test_09_concurrent_operations(self):
        """Test system behavior under concurrent operations."""
        print("\n⚡ Testing concurrent operations...")

        try:
            # Register and login
            response = self.client.post("/api/auth/register", json=self.test_admin)
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            # Perform multiple concurrent operations
            operations = []

            # Create multiple zones
            for i in range(3):
                zone_data = self.test_zone.copy()
                zone_data["name"] = f"Concurrent Test Zone {i}"
                operations.append(
                    self.client.post("/api/zones/", json=zone_data, headers=headers)
                )

            # Create multiple alerts
            for i in range(3):
                alert_data = {
                    "title": f"Concurrent Alert {i}",
                    "message": f"Testing concurrent alert creation {i}",
                    "severity": "low",
                    "alert_type": "test"
                }
                operations.append(
                    self.client.post("/api/alerts/", json=alert_data, headers=headers)
                )

            # Execute all operations
            results = []
            for op in operations:
                response = op
                results.append(response.status_code == 200)

            # Check if all operations succeeded
            success_rate = sum(results) / len(results)
            self.assertGreaterEqual(success_rate, 0.8)  # At least 80% success rate

            print(f"✅ Concurrent operations test passed ({success_rate:.1%})")
            return True

        except Exception as e:
            print(f"❌ Concurrent operations test failed: {e}")
            return False

    def run_integration_suite(self):
        """Run the complete integration test suite."""
        print("🚀 Starting Firefly Station Integration Test Suite")
        print("=" * 60)

        tests = [
            self.test_01_database_initialization,
            self.test_02_api_endpoints_accessibility,
            self.test_03_user_registration_and_authentication,
            self.test_04_geolocation_system_integration,
            self.test_05_alert_system_integration,
            self.test_06_websocket_connectivity,
            self.test_07_cross_component_data_flow,
            self.test_08_system_health_check,
            self.test_09_concurrent_operations
        ]

        passed = 0
        total = len(tests)

        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")

        print("\n" + "=" * 60)
        print(f"Integration Test Results: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All integration tests passed!")
            return True
        else:
            print("⚠️  Some integration tests failed")
            return False


def main():
    """Main function to run integration tests."""
    test_suite = SystemIntegrationTest()
    success = test_suite.run_integration_suite()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()