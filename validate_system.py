#!/usr/bin/env python3
"""
System Validation Script for Firefly Station
Validates system state and ensures all components are working correctly.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from backend.main import app
from backend import database
from backend.geolocation import geolocation_service


@dataclass
class ValidationResult:
    """Result of a validation check."""
    check_name: str
    status: str  # "passed", "failed", "warning", "error"
    message: str
    details: Dict = None
    timestamp: str = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class SystemValidator:
    """Comprehensive system validation suite."""

    def __init__(self):
        self.client = TestClient(app)
        self.results: List[ValidationResult] = []
        self.start_time = datetime.now()

    def add_result(self, check_name: str, status: str, message: str, details: Dict = None):
        """Add a validation result."""
        result = ValidationResult(
            check_name=check_name,
            status=status,
            message=message,
            details=details or {}
        )
        self.results.append(result)
        print(f"  {status.upper()}: {check_name} - {message}")

    def validate_database_integrity(self) -> bool:
        """Validate database integrity and schema."""
        print("\n🗄️  Validating database integrity...")

        try:
            # Test database connection
            database.init_db()

            # Test basic operations
            stats = database.get_bot_stats()
            if not isinstance(stats, dict):
                self.add_result("database_stats", "failed", "Invalid stats format")
                return False

            # Test user operations
            test_user_data = {
                "user": {"longName": "Validation User", "shortName": "VU"},
                "position": {"latitude": 55.7558, "longitude": 37.6173},
                "deviceMetrics": {"batteryLevel": 80}
            }
            database.insert_or_update_user("validation_test_user", test_user_data)

            user = database.get_user("validation_test_user")
            if not user or user['long_name'] != "Validation User":
                self.add_result("database_user_ops", "failed", "User operations failed")
                return False

            # Test message operations
            database.insert_message("sender", "receiver", "Validation message", "incoming")
            messages = database.get_messages_for_user("sender", limit=10)
            if not messages:
                self.add_result("database_message_ops", "failed", "Message operations failed")
                return False

            self.add_result("database_integrity", "passed", "Database integrity validated")
            return True

        except Exception as e:
            self.add_result("database_integrity", "error", f"Database error: {str(e)}")
            return False

    def validate_api_endpoints(self) -> bool:
        """Validate all API endpoints are accessible."""
        print("\n🔗 Validating API endpoints...")

        try:
            # Test root endpoint
            response = self.client.get("/")
            if response.status_code != 200:
                self.add_result("api_root", "failed", f"Root endpoint returned {response.status_code}")
                return False

            # Test key API endpoints
            endpoints = [
                "/api/auth/register",
                "/api/auth/login",
                "/api/users/",
                "/api/zones/",
                "/api/alerts/",
                "/api/geolocation/test",
                "/api/websocket/test"
            ]

            failed_endpoints = []
            for endpoint in endpoints:
                response = self.client.get(endpoint)
                if response.status_code == 404:
                    failed_endpoints.append(endpoint)

            if failed_endpoints:
                self.add_result("api_endpoints", "failed", f"Missing endpoints: {failed_endpoints}")
                return False

            self.add_result("api_endpoints", "passed", "All API endpoints accessible")
            return True

        except Exception as e:
            self.add_result("api_endpoints", "error", f"API validation error: {str(e)}")
            return False

    def validate_configuration(self) -> bool:
        """Validate system configuration."""
        print("\n⚙️  Validating system configuration...")

        try:
            import yaml

            if not os.path.exists("config.yaml"):
                self.add_result("config_file", "failed", "config.yaml not found")
                return False

            with open("config.yaml", 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Validate required sections
            required_sections = ["web_server", "llm_provider", "model"]
            missing_sections = [s for s in required_sections if s not in config]

            if missing_sections:
                self.add_result("config_sections", "failed", f"Missing sections: {missing_sections}")
                return False

            # Validate web server config
            web_config = config["web_server"]
            required_web_keys = ["host", "port", "cors_origins"]
            missing_web_keys = [k for k in required_web_keys if k not in web_config]

            if missing_web_keys:
                self.add_result("config_web", "failed", f"Missing web config keys: {missing_web_keys}")
                return False

            self.add_result("configuration", "passed", "Configuration is valid")
            return True

        except Exception as e:
            self.add_result("configuration", "error", f"Configuration error: {str(e)}")
            return False

    def validate_dependencies(self) -> bool:
        """Validate system dependencies."""
        print("\n📦 Validating system dependencies...")

        try:
            critical_modules = [
                "fastapi", "uvicorn", "websockets", "requests", "yaml", "meshtastic"
            ]

            missing_modules = []
            for module in critical_modules:
                try:
                    __import__(module)
                except ImportError:
                    missing_modules.append(module)

            if missing_modules:
                self.add_result("dependencies", "failed", f"Missing modules: {missing_modules}")
                return False

            self.add_result("dependencies", "passed", "All dependencies available")
            return True

        except Exception as e:
            self.add_result("dependencies", "error", f"Dependency check error: {str(e)}")
            return False

    def validate_geolocation_service(self) -> bool:
        """Validate geolocation service functionality."""
        print("\n📍 Validating geolocation service...")

        try:
            # Test location processing
            test_location = {
                "user_id": "geo_validation_user",
                "latitude": 55.7558,
                "longitude": 37.6173,
                "altitude": 100,
                "battery_level": 85
            }

            result = geolocation_service.process_location_update(**test_location)

            if not result.get("success", False):
                self.add_result("geolocation_service", "failed", "Location processing failed")
                return False

            # Validate result structure
            required_keys = ["success", "is_moving", "speed_mps", "zone_changes", "alerts"]
            missing_keys = [k for k in required_keys if k not in result]

            if missing_keys:
                self.add_result("geolocation_service", "failed", f"Missing result keys: {missing_keys}")
                return False

            self.add_result("geolocation_service", "passed", "Geolocation service functional")
            return True

        except Exception as e:
            self.add_result("geolocation_service", "error", f"Geolocation error: {str(e)}")
            return False

    def validate_file_structure(self) -> bool:
        """Validate required files and directories exist."""
        print("\n📁 Validating file structure...")

        try:
            required_files = [
                "main.py",
                "config.yaml",
                "requirements.txt",
                "backend/main.py",
                "backend/database.py",
                "frontend/package.json"
            ]

            missing_files = []
            for file_path in required_files:
                if not os.path.exists(file_path):
                    missing_files.append(file_path)

            if missing_files:
                self.add_result("file_structure", "failed", f"Missing files: {missing_files}")
                return False

            # Check database file
            if not os.path.exists("meshtastic_llm.db"):
                self.add_result("file_structure", "warning", "Database file not found (will be created)")

            self.add_result("file_structure", "passed", "File structure is valid")
            return True

        except Exception as e:
            self.add_result("file_structure", "error", f"File structure error: {str(e)}")
            return False

    def validate_security_configuration(self) -> bool:
        """Validate security-related configurations."""
        print("\n🔒 Validating security configuration...")

        try:
            import yaml

            with open("config.yaml", 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Check CORS configuration
            cors_origins = config.get("web_server", {}).get("cors_origins", [])
            if not cors_origins:
                self.add_result("security_cors", "warning", "No CORS origins configured")
            elif "*" in cors_origins:
                self.add_result("security_cors", "warning", "CORS allows all origins (*)")

            # Check for default passwords or keys
            if "api_key" in config.get("model", {}).get("openrouter", {}):
                api_key = config["model"]["openrouter"]["api_key"]
                if api_key.startswith("sk-") and len(api_key) > 10:
                    self.add_result("security_api_key", "passed", "API key configured")
                else:
                    self.add_result("security_api_key", "warning", "API key may not be properly configured")

            self.add_result("security_configuration", "passed", "Security configuration reviewed")
            return True

        except Exception as e:
            self.add_result("security_configuration", "error", f"Security validation error: {str(e)}")
            return False

    def validate_performance_baselines(self) -> bool:
        """Validate system meets basic performance baselines."""
        print("\n⚡ Validating performance baselines...")

        try:
            # Test API response time
            start_time = time.time()
            response = self.client.get("/api/zones/")
            response_time = time.time() - start_time

            if response_time > 1.0:  # Should respond within 1 second
                self.add_result("performance_api", "warning", f"Slow API response: {response_time:.3f}s")
            else:
                self.add_result("performance_api", "passed", f"API response time: {response_time:.3f}s")

            # Test database operation time
            start_time = time.time()
            database.get_bot_stats()
            db_time = time.time() - start_time

            if db_time > 0.1:  # Should be fast
                self.add_result("performance_db", "warning", f"Slow database: {db_time:.3f}s")
            else:
                self.add_result("performance_db", "passed", f"Database response time: {db_time:.3f}s")

            self.add_result("performance_baselines", "passed", "Performance baselines validated")
            return True

        except Exception as e:
            self.add_result("performance_baselines", "error", f"Performance validation error: {str(e)}")
            return False

    def generate_validation_report(self) -> Dict:
        """Generate comprehensive validation report."""
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        warnings = sum(1 for r in self.results if r.status == "warning")
        errors = sum(1 for r in self.results if r.status == "error")

        report = {
            "summary": {
                "total_checks": len(self.results),
                "passed": passed,
                "failed": failed,
                "warnings": warnings,
                "errors": errors,
                "success_rate": passed / len(self.results) if self.results else 0,
                "validation_time": datetime.now().isoformat(),
                "duration": (datetime.now() - self.start_time).total_seconds()
            },
            "results": [asdict(result) for result in self.results]
        }

        return report

    def print_validation_report(self, report: Dict):
        """Print formatted validation report."""
        summary = report["summary"]

        print("\n" + "=" * 80)
        print("🔍 FIREFLY STATION - SYSTEM VALIDATION REPORT")
        print("=" * 80)
        print(f"Generated: {summary['validation_time']}")
        print(f"Duration: {summary['duration']:.2f}s")
        print()

        # Overall results
        print("📊 VALIDATION SUMMARY:")
        print(f"  Total Checks: {summary['total_checks']}")
        print(f"  ✅ Passed: {summary['passed']}")
        print(f"  ❌ Failed: {summary['failed']}")
        print(f"  ⚠️  Warnings: {summary['warnings']}")
        print(f"  💥 Errors: {summary['errors']}")
        print(f"  📈 Success Rate: {summary['success_rate']:.1%}")
        print()

        # Detailed results
        if report["results"]:
            print("📋 DETAILED RESULTS:")

            # Group by status
            for status in ["error", "failed", "warning", "passed"]:
                status_results = [r for r in report["results"] if r["status"] == status]
                if status_results:
                    status_icon = {"error": "💥", "failed": "❌", "warning": "⚠️", "passed": "✅"}[status]
                    print(f"\n  {status_icon} {status.upper()} ({len(status_results)}):")
                    for result in status_results:
                        print(f"    • {result['check_name']}: {result['message']}")

        print("\n" + "=" * 80)

        # Overall assessment
        if summary["failed"] == 0 and summary["errors"] == 0:
            if summary["warnings"] == 0:
                print("🎉 EXCELLENT: System is fully validated and ready!")
            else:
                print("👍 GOOD: System is validated with minor warnings.")
        elif summary["failed"] == 0:
            print("⚠️  ACCEPTABLE: System has errors but no failures.")
        else:
            print("🚨 CRITICAL: System has failures that need attention!")

    def run_validation_suite(self) -> bool:
        """Run complete validation suite."""
        print("🔍 Starting Firefly Station System Validation Suite")
        print("=" * 60)

        # Run all validation checks
        validation_checks = [
            ("File Structure", self.validate_file_structure),
            ("Dependencies", self.validate_dependencies),
            ("Configuration", self.validate_configuration),
            ("Database Integrity", self.validate_database_integrity),
            ("API Endpoints", self.validate_api_endpoints),
            ("Geolocation Service", self.validate_geolocation_service),
            ("Security Configuration", self.validate_security_configuration),
            ("Performance Baselines", self.validate_performance_baselines)
        ]

        for check_name, check_func in validation_checks:
            print(f"\n🔍 Validating {check_name}...")
            try:
                check_func()
            except Exception as e:
                self.add_result(check_name.lower().replace(" ", "_"), "error",
                              f"Validation check failed: {str(e)}")

        # Generate and print report
        report = self.generate_validation_report()
        self.print_validation_report(report)

        # Return success based on critical issues
        summary = report["summary"]
        critical_issues = summary["failed"] + summary["errors"]

        return critical_issues == 0


def main():
    """Main function to run system validation."""
    validator = SystemValidator()
    success = validator.run_validation_suite()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()