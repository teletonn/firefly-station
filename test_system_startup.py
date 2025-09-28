#!/usr/bin/env python3
"""
System Startup Validation Script for Firefly Station
Validates that all system components start up correctly.
"""

import asyncio
import os
import subprocess
import sys
import time
import signal
import threading
from contextlib import contextmanager
from typing import Dict, List, Optional

import requests
from fastapi.testclient import TestClient

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.main import app


class SystemStartupValidator:
    """Validates system startup and component initialization."""

    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.client = TestClient(app)
        self.process = None
        self.shutdown_event = threading.Event()

    @contextmanager
    def managed_process(self, command: List[str]):
        """Context manager for running and cleaning up processes."""
        try:
            print(f"Starting process: {' '.join(command)}")
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Give the process time to start
            time.sleep(3)
            yield self.process

        finally:
            if self.process and self.process.poll() is None:
                print("Terminating process...")
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    print("Force killing process...")
                    self.process.kill()
                    self.process.wait()

    def wait_for_service(self, url: str, timeout: int = 30) -> bool:
        """Wait for a service to become available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code > 0:  # Any response means service is up
                    print(f"Service available at {url}")
                    return True
            except:
                pass
            time.sleep(1)
        return False

    def validate_database_initialization(self) -> bool:
        """Validate database initializes correctly."""
        print("\n🗄️  Validating database initialization...")

        try:
            from backend import database

            # Test database connection
            database.init_db()

            # Test basic operations
            stats = database.get_bot_stats()
            print(f"Database stats: {stats}")

            # Test user operations
            test_user_data = {
                "user": {"longName": "Startup Test", "shortName": "ST"},
                "position": {"latitude": 55.7558, "longitude": 37.6173},
                "deviceMetrics": {"batteryLevel": 100}
            }
            database.insert_or_update_user("startup_test_user", test_user_data)

            user = database.get_user("startup_test_user")
            if user and user['long_name'] == "Startup Test":
                print("✅ Database initialization validated")
                return True
            else:
                print("❌ Database initialization failed")
                return False

        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            return False

    def validate_api_endpoints(self) -> bool:
        """Validate all API endpoints are accessible."""
        print("\n🔗 Validating API endpoints...")

        try:
            # Test root endpoint
            response = self.client.get("/")
            if response.status_code != 200:
                print(f"❌ Root endpoint failed: {response.status_code}")
                return False

            # Test key API endpoints
            endpoints = [
                "/api/auth/register",
                "/api/auth/login",
                "/api/users/",
                "/api/zones/",
                "/api/alerts/",
                "/api/geolocation/test"
            ]

            for endpoint in endpoints:
                response = self.client.get(endpoint)
                if response.status_code == 404:
                    print(f"❌ Endpoint {endpoint} not found")
                    return False

            print("✅ API endpoints validated")
            return True

        except Exception as e:
            print(f"❌ API endpoints validation error: {e}")
            return False

    def validate_geolocation_service(self) -> bool:
        """Validate geolocation service functionality."""
        print("\n📍 Validating geolocation service...")

        try:
            from backend.geolocation import geolocation_service

            # Test location processing
            test_location = {
                "user_id": "validation_test_user",
                "latitude": 55.7558,
                "longitude": 37.6173,
                "altitude": 100,
                "battery_level": 85
            }

            result = geolocation_service.process_location_update(**test_location)

            if result.get("success", False):
                print("✅ Geolocation service validated")
                return True
            else:
                print(f"❌ Geolocation service failed: {result}")
                return False

        except Exception as e:
            print(f"❌ Geolocation service validation error: {e}")
            return False

    def validate_websocket_service(self) -> bool:
        """Validate WebSocket service is configured."""
        print("\n🔄 Validating WebSocket service...")

        try:
            # Test WebSocket endpoint exists
            response = self.client.get("/api/websocket/test")
            if response.status_code == 200:
                print("✅ WebSocket service validated")
                return True
            else:
                print(f"❌ WebSocket service failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ WebSocket service validation error: {e}")
            return False

    def validate_configuration(self) -> bool:
        """Validate system configuration."""
        print("\n⚙️  Validating system configuration...")

        try:
            import yaml

            # Check config file exists and is valid
            if not os.path.exists("config.yaml"):
                print("❌ config.yaml not found")
                return False

            with open("config.yaml", 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Validate required config sections
            required_sections = [
                "web_server", "llm_provider", "model"
            ]

            for section in required_sections:
                if section not in config:
                    print(f"❌ Missing config section: {section}")
                    return False

            # Validate web server config
            web_config = config["web_server"]
            required_web_keys = ["host", "port", "cors_origins"]
            for key in required_web_keys:
                if key not in web_config:
                    print(f"❌ Missing web config key: {key}")
                    return False

            print("✅ System configuration validated")
            return True

        except Exception as e:
            print(f"❌ Configuration validation error: {e}")
            return False

    def validate_dependencies(self) -> bool:
        """Validate system dependencies are available."""
        print("\n📦 Validating system dependencies...")

        try:
            # Test critical imports
            critical_modules = [
                "fastapi",
                "uvicorn",
                "meshtastic",
                "websockets",
                "requests",
                "yaml"
            ]

            missing_modules = []
            for module in critical_modules:
                try:
                    __import__(module)
                except ImportError:
                    missing_modules.append(module)

            if missing_modules:
                print(f"❌ Missing modules: {missing_modules}")
                return False

            print("✅ System dependencies validated")
            return True

        except Exception as e:
            print(f"❌ Dependencies validation error: {e}")
            return False

    def validate_full_system_startup(self) -> bool:
        """Validate complete system startup with all components."""
        print("\n🚀 Validating full system startup...")

        try:
            # Test with actual server startup
            with self.managed_process([sys.executable, "main.py"]):
                # Wait for server to be ready
                if not self.wait_for_service(self.base_url):
                    print("❌ Server failed to start")
                    return False

                # Test all components
                tests = [
                    self.validate_database_initialization,
                    self.validate_api_endpoints,
                    self.validate_geolocation_service,
                    self.validate_websocket_service
                ]

                results = []
                for test in tests:
                    results.append(test())

                success_rate = sum(results) / len(results)
                if success_rate >= 0.8:  # 80% success rate
                    print(f"✅ Full system startup validated ({success_rate:.1%})")
                    return True
                else:
                    print(f"❌ Full system startup failed ({success_rate:.1%})")
                    return False

        except Exception as e:
            print(f"❌ Full system startup validation error: {e}")
            return False

    def run_startup_validation_suite(self) -> bool:
        """Run complete startup validation suite."""
        print("🔍 Firefly Station Startup Validation Suite")
        print("=" * 50)

        # Basic validation tests (don't require running server)
        basic_tests = [
            ("Dependencies", self.validate_dependencies),
            ("Configuration", self.validate_configuration),
        ]

        print("\n📋 Running basic validation tests...")
        basic_results = []
        for test_name, test_func in basic_tests:
            print(f"\n🔍 Testing {test_name}...")
            basic_results.append(test_func())

        # Component validation tests
        component_tests = [
            ("Database", self.validate_database_initialization),
            ("API Endpoints", self.validate_api_endpoints),
            ("Geolocation", self.validate_geolocation_service),
            ("WebSocket", self.validate_websocket_service),
        ]

        print("\n🔧 Running component validation tests...")
        component_results = []
        for test_name, test_func in component_tests:
            print(f"\n🔍 Testing {test_name}...")
            component_results.append(test_func())

        # Full system test
        print("\n🚀 Running full system validation...")
        full_system_result = self.validate_full_system_startup()

        # Overall results
        all_results = basic_results + component_results + [full_system_result]
        passed = sum(all_results)
        total = len(all_results)

        print("\n" + "=" * 50)
        print("Startup Validation Results:")
        print(f"Basic Tests: {sum(basic_results)}/{len(basic_results)} passed")
        print(f"Component Tests: {sum(component_results)}/{len(component_results)} passed")
        print(f"Full System Test: {'✅ Passed' if full_system_result else '❌ Failed'}")
        print(f"Overall: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All startup validation tests passed!")
            return True
        else:
            print("⚠️  Some startup validation tests failed")
            return False


def main():
    """Main function to run startup validation."""
    validator = SystemStartupValidator()
    success = validator.run_startup_validation_suite()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()