#!/usr/bin/env python3
"""
Comprehensive Test Suite Runner for Firefly Station
Executes all test suites and provides detailed reporting.
"""

import argparse
import os
import subprocess
import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    name: str
    status: TestStatus
    duration: float
    message: str = ""
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class TestSuite:
    name: str
    results: List[TestResult]
    total_duration: float

    def get_summary(self) -> Dict:
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
        errors = sum(1 for r in self.results if r.status == TestStatus.ERROR)

        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
            "success_rate": passed / len(self.results) if self.results else 0
        }


class ComprehensiveTestRunner:
    """Runs comprehensive test suite for Firefly Station."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.start_time = time.time()
        self.test_suites: List[TestSuite] = []

        # Available test files
        self.test_files = {
            "database": "test_db.py",
            "api": "test_api.py",
            "geolocation": "test_geolocation_system.py",
            "integration": "test_system_integration.py",
            "startup": "test_system_startup.py"
        }

    def run_test_file(self, test_file: str, suite_name: str) -> TestSuite:
        """Run a single test file and return results."""
        print(f"\n🧪 Running {suite_name} tests...")
        print("-" * 50)

        suite_start_time = time.time()
        results = []

        if not os.path.exists(test_file):
            print(f"⚠️  Test file {test_file} not found, skipping...")
            results.append(TestResult(
                name=f"{suite_name}_availability",
                status=TestStatus.SKIPPED,
                duration=0,
                message=f"Test file {test_file} not found"
            ))
        else:
            try:
                # Run the test file
                test_start_time = time.time()
                result = subprocess.run(
                    [sys.executable, test_file],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                test_duration = time.time() - test_start_time

                # Parse results
                if result.returncode == 0:
                    status = TestStatus.PASSED
                    message = "All tests passed"
                    details = {"stdout": result.stdout}
                else:
                    status = TestStatus.FAILED
                    message = f"Tests failed with exit code {result.returncode}"
                    details = {
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    }

                results.append(TestResult(
                    name=suite_name,
                    status=status,
                    duration=test_duration,
                    message=message,
                    details=details
                ))

                if self.verbose:
                    print(result.stdout)
                    if result.stderr:
                        print("STDERR:", result.stderr)

            except subprocess.TimeoutExpired:
                results.append(TestResult(
                    name=suite_name,
                    status=TestStatus.ERROR,
                    duration=300,
                    message="Test timed out after 5 minutes"
                ))
            except Exception as e:
                results.append(TestResult(
                    name=suite_name,
                    status=TestStatus.ERROR,
                    duration=time.time() - suite_start_time,
                    message=f"Error running tests: {str(e)}"
                ))

        suite_duration = time.time() - suite_start_time

        return TestSuite(
            name=suite_name,
            results=results,
            total_duration=suite_duration
        )

    def run_system_health_check(self) -> TestSuite:
        """Run system health check."""
        print("\n🏥 Running system health check...")
        print("-" * 50)

        suite_start_time = time.time()
        results = []

        try:
            # Test database connectivity
            try:
                from backend import database
                database.init_db()
                stats = database.get_bot_stats()
                db_status = TestStatus.PASSED
                db_message = f"Database healthy, stats: {stats}"
            except Exception as e:
                db_status = TestStatus.FAILED
                db_message = f"Database error: {e}"

            results.append(TestResult(
                name="database_health",
                status=db_status,
                duration=0,
                message=db_message
            ))

            # Test API availability
            try:
                import requests
                response = requests.get("http://localhost:8000/", timeout=5)
                api_status = TestStatus.PASSED if response.status_code == 200 else TestStatus.FAILED
                api_message = f"API responded with status {response.status_code}"
            except Exception as e:
                api_status = TestStatus.FAILED
                api_message = f"API unavailable: {e}"

            results.append(TestResult(
                name="api_health",
                status=api_status,
                duration=0,
                message=api_message
            ))

            # Test configuration validity
            try:
                import yaml
                with open("config.yaml", 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                required_keys = ["web_server", "llm_provider", "model"]
                missing_keys = [key for key in required_keys if key not in config]

                if missing_keys:
                    config_status = TestStatus.FAILED
                    config_message = f"Missing config keys: {missing_keys}"
                else:
                    config_status = TestStatus.PASSED
                    config_message = "Configuration is valid"

            except Exception as e:
                config_status = TestStatus.FAILED
                config_message = f"Configuration error: {e}"

            results.append(TestResult(
                name="configuration_health",
                status=config_status,
                duration=0,
                message=config_message
            ))

        except Exception as e:
            results.append(TestResult(
                name="health_check_error",
                status=TestStatus.ERROR,
                duration=time.time() - suite_start_time,
                message=f"Health check error: {e}"
            ))

        suite_duration = time.time() - suite_start_time

        return TestSuite(
            name="system_health",
            results=results,
            total_duration=suite_duration
        )

    def run_all_tests(self) -> List[TestSuite]:
        """Run all available tests."""
        print("🚀 Starting Comprehensive Firefly Station Test Suite")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        test_suites = []

        # Run system health check first
        health_suite = self.run_system_health_check()
        test_suites.append(health_suite)

        # Run individual test files
        for suite_name, test_file in self.test_files.items():
            suite = self.run_test_file(test_file, suite_name)
            test_suites.append(suite)

        return test_suites

    def generate_report(self, test_suites: List[TestSuite]) -> Dict:
        """Generate comprehensive test report."""
        total_suites = len(test_suites)
        total_tests = sum(len(suite.results) for suite in test_suites)
        total_duration = sum(suite.total_duration for suite in test_suites)

        # Overall statistics
        all_passed = sum(1 for suite in test_suites
                        for result in suite.results
                        if result.status == TestStatus.PASSED)
        all_failed = sum(1 for suite in test_suites
                        for result in suite.results
                        if result.status == TestStatus.FAILED)
        all_skipped = sum(1 for suite in test_suites
                         for result in suite.results
                         if result.status == TestStatus.SKIPPED)
        all_errors = sum(1 for suite in test_suites
                        for result in suite.results
                        if result.status == TestStatus.ERROR)

        # Suite summaries
        suite_summaries = []
        for suite in test_suites:
            summary = suite.get_summary()
            summary["name"] = suite.name
            summary["duration"] = suite.total_duration
            suite_summaries.append(summary)

        # Failed tests details
        failed_tests = []
        for suite in test_suites:
            for result in suite.results:
                if result.status in [TestStatus.FAILED, TestStatus.ERROR]:
                    failed_tests.append({
                        "suite": suite.name,
                        "test": result.name,
                        "status": result.status.value,
                        "message": result.message,
                        "duration": result.duration
                    })

        report = {
            "summary": {
                "total_suites": total_suites,
                "total_tests": total_tests,
                "total_duration": total_duration,
                "passed": all_passed,
                "failed": all_failed,
                "skipped": all_skipped,
                "errors": all_errors,
                "success_rate": all_passed / total_tests if total_tests > 0 else 0,
                "timestamp": datetime.now().isoformat()
            },
            "suite_summaries": suite_summaries,
            "failed_tests": failed_tests
        }

        return report

    def print_report(self, report: Dict):
        """Print formatted test report to console."""
        summary = report["summary"]

        print("\n" + "=" * 80)
        print("🔬 FIREFLY STATION - COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        print(f"Generated: {summary['timestamp']}")
        print(f"Total Duration: {summary['total_duration']:.2f}s")
        print()

        # Overall results
        print("📊 OVERALL RESULTS:")
        print(f"  Suites: {summary['total_suites']}")
        print(f"  Tests:  {summary['total_tests']}")
        print(f"  ✅ Passed:  {summary['passed']}")
        print(f"  ❌ Failed:  {summary['failed']}")
        print(f"  ⏭️  Skipped: {summary['skipped']}")
        print(f"  💥 Errors:  {summary['errors']}")
        print(f"  📈 Success Rate: {summary['success_rate']:.1%}")
        print()

        # Suite details
        print("📋 SUITE DETAILS:")
        for suite_summary in report["suite_summaries"]:
            status_icon = "✅" if suite_summary["passed"] == suite_summary["total"] else "❌"
            print(f"  {status_icon} {suite_summary['name']}:")
            print(f"    Tests: {suite_summary['passed']}/{suite_summary['total']} passed")
            print(f"    Duration: {suite_summary['duration']:.2f}s")
            print(f"    Success Rate: {suite_summary['success_rate']:.1%}")
        print()

        # Failed tests details
        if report["failed_tests"]:
            print("❌ FAILED TESTS DETAILS:")
            for failed in report["failed_tests"]:
                print(f"  • {failed['suite']}.{failed['test']}:")
                print(f"    Status: {failed['status']}")
                print(f"    Message: {failed['message']}")
                print(f"    Duration: {failed['duration']:.2f}s")
            print()

        # Overall assessment
        if summary["success_rate"] >= 0.9:
            print("🎉 EXCELLENT: System is ready for production!")
        elif summary["success_rate"] >= 0.7:
            print("👍 GOOD: System is functional with minor issues.")
        elif summary["success_rate"] >= 0.5:
            print("⚠️  FAIR: System needs attention before production.")
        else:
            print("🚨 POOR: System has significant issues that need fixing.")

        print("=" * 80)

    def save_report(self, report: Dict, filename: str = None):
        """Save test report to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"test_report_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"📄 Test report saved to: {filename}")

    def run(self, save_report: bool = True) -> bool:
        """Run complete test suite and return success status."""
        try:
            # Run all tests
            test_suites = self.run_all_tests()

            # Generate report
            report = self.generate_report(test_suites)

            # Print report
            self.print_report(report)

            # Save report if requested
            if save_report:
                self.save_report(report)

            # Return success based on overall results
            summary = report["summary"]
            return summary["failed"] == 0 and summary["errors"] == 0

        except Exception as e:
            print(f"💥 Fatal error running test suite: {e}")
            return False


def main():
    """Main function with command line arguments."""
    parser = argparse.ArgumentParser(description="Firefly Station Comprehensive Test Suite")
    parser.add_argument("--no-save", action="store_true",
                       help="Don't save test report to file")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    parser.add_argument("--quick", action="store_true",
                       help="Run only health check and integration tests")

    args = parser.parse_args()

    runner = ComprehensiveTestRunner(verbose=args.verbose)

    if args.quick:
        # Run only essential tests
        print("⚡ Running quick test suite...")
        health_suite = runner.run_system_health_check()
        integration_suite = runner.run_test_file("test_system_integration.py", "integration")

        test_suites = [health_suite, integration_suite]
        report = runner.generate_report(test_suites)
        runner.print_report(report)

        if not args.no_save:
            runner.save_report(report)
    else:
        # Run full test suite
        success = runner.run(save_report=not args.no_save)
        exit(0 if success else 1)


if __name__ == "__main__":
    main()