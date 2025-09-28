#!/usr/bin/env python3
"""
Performance and Load Testing for Firefly Station
Tests system performance under various load conditions.
"""

import asyncio
import json
import os
import sys
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from backend.main import app
from backend import database
from backend.geolocation import geolocation_service


@dataclass
class PerformanceMetrics:
    """Performance metrics for a test operation."""
    operation_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    min_response_time: float
    max_response_time: float
    avg_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    total_duration: float

    def success_rate(self) -> float:
        return (self.successful_requests / self.total_requests) * 100 if self.total_requests > 0 else 0


class PerformanceLoadTest:
    """Performance and load testing suite."""

    def __init__(self):
        self.client = TestClient(app)
        self.results: List[PerformanceMetrics] = []

        # Test data
        self.admin_user = {
            "username": "perf_admin",
            "email": "perf_admin@test.com",
            "password": "testpass123",
            "role": "admin"
        }

        self.test_users = [
            {
                "username": f"perf_user_{i}",
                "email": f"perf_user_{i}@test.com",
                "password": "testpass123",
                "role": "user"
            }
            for i in range(10)
        ]

    def setUp(self):
        """Set up test environment."""
        database.init_db()

        # Clear test data
        try:
            database.delete_user("perf_admin")
            for user in self.test_users:
                database.delete_user(user["username"])
        except:
            pass

        # Register admin
        response = self.client.post("/api/auth/register", json=self.admin_user)
        self.admin_token = response.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def measure_operation_performance(self, operation_func, operation_name: str,
                                    num_requests: int = 100, num_threads: int = 10) -> PerformanceMetrics:
        """Measure performance of a specific operation."""
        print(f"\n📊 Measuring {operation_name} performance...")
        print(f"   Requests: {num_requests}, Threads: {num_threads}")

        response_times = []
        successful_requests = 0
        failed_requests = 0

        start_time = time.time()

        def make_request(request_id):
            try:
                req_start_time = time.time()
                result = operation_func()
                req_end_time = time.time()

                response_time = req_end_time - req_start_time
                return response_time, True, None
            except Exception as e:
                req_end_time = time.time()
                response_time = req_end_time - req_start_time
                return response_time, False, str(e)

        # Execute requests using thread pool
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            future_to_request = {
                executor.submit(make_request, i): i
                for i in range(num_requests)
            }

            for future in as_completed(future_to_request):
                response_time, success, error = future.result()
                response_times.append(response_time)

                if success:
                    successful_requests += 1
                else:
                    failed_requests += 1

        end_time = time.time()
        total_duration = end_time - start_time

        # Calculate statistics
        if response_times:
            response_times.sort()
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            p95_index = int(0.95 * len(response_times))
            p99_index = int(0.99 * len(response_times))
            p95_response_time = response_times[p95_index] if p95_index < len(response_times) else response_times[-1]
            p99_response_time = response_times[p99_index] if p99_index < len(response_times) else response_times[-1]
        else:
            avg_response_time = median_response_time = p95_response_time = p99_response_time = 0

        requests_per_second = num_requests / total_duration if total_duration > 0 else 0

        metrics = PerformanceMetrics(
            operation_name=operation_name,
            total_requests=num_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            min_response_time=min(response_times) if response_times else 0,
            max_response_time=max(response_times) if response_times else 0,
            avg_response_time=avg_response_time,
            median_response_time=median_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            total_duration=total_duration
        )

        print(f"   ✅ Completed: {successful_requests}/{num_requests} successful")
        print(f"   ⏱️  Avg: {avg_response_time:.3f}s, P95: {p95_response_time:.3f}s")
        print(f"   🚀 RPS: {requests_per_second:.1f}")

        return metrics

    def test_api_endpoint_performance(self):
        """Test API endpoint performance under load."""
        print("\n🔗 Testing API endpoint performance...")

        def api_request():
            response = self.client.get("/api/zones/")
            return response.status_code == 200

        metrics = self.measure_operation_performance(
            lambda: api_request(),
            "API Zone Listing",
            num_requests=200,
            num_threads=20
        )

        self.results.append(metrics)
        return metrics.success_rate() >= 95  # 95% success rate

    def test_geolocation_processing_performance(self):
        """Test geolocation processing performance under load."""
        print("\n📍 Testing geolocation processing performance...")

        def geolocation_request():
            location_data = {
                "user_id": f"perf_user_{time.time()}",
                "latitude": 55.7558,
                "longitude": 37.6173,
                "altitude": 100,
                "battery_level": 80
            }
            result = geolocation_service.process_location_update(**location_data)
            return result["success"]

        metrics = self.measure_operation_performance(
            lambda: geolocation_request(),
            "Geolocation Processing",
            num_requests=150,
            num_threads=15
        )

        self.results.append(metrics)
        return metrics.success_rate() >= 95

    def test_database_operation_performance(self):
        """Test database operation performance under load."""
        print("\n🗄️  Testing database operation performance...")

        def database_request():
            # Test user insertion
            user_data = {
                "user": {"longName": "Perf Test User", "shortName": "PTU"},
                "position": {"latitude": 55.7558, "longitude": 37.6173},
                "deviceMetrics": {"batteryLevel": 80}
            }
            database.insert_or_update_user(f"perf_db_user_{time.time()}", user_data)

            # Test user retrieval
            user = database.get_user(f"perf_db_user_{time.time()}")
            return user is not None

        metrics = self.measure_operation_performance(
            lambda: database_request(),
            "Database Operations",
            num_requests=100,
            num_threads=10
        )

        self.results.append(metrics)
        return metrics.success_rate() >= 95

    def test_concurrent_user_registration_performance(self):
        """Test concurrent user registration performance."""
        print("\n👥 Testing concurrent user registration performance...")

        def registration_request():
            user_data = {
                "username": f"concurrent_user_{time.time()}_{threading.current_thread().ident}",
                "email": f"concurrent_{time.time()}_{threading.current_thread().ident}@test.com",
                "password": "testpass123",
                "role": "user"
            }
            response = self.client.post("/api/auth/register", json=user_data)
            return response.status_code == 200

        metrics = self.measure_operation_performance(
            lambda: registration_request(),
            "Concurrent User Registration",
            num_requests=50,
            num_threads=10
        )

        self.results.append(metrics)
        return metrics.success_rate() >= 90

    def test_memory_usage_monitoring(self):
        """Test system memory usage under load."""
        print("\n💾 Testing memory usage under load...")

        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Run memory-intensive operations
        for i in range(100):
            # Create test data
            user_data = {
                "user": {"longName": f"Memory Test User {i}", "shortName": f"MT{i}"},
                "position": {"latitude": 55.7558, "longitude": 37.6173},
                "deviceMetrics": {"batteryLevel": 80}
            }
            database.insert_or_update_user(f"memory_test_user_{i}", user_data)

            # Process location updates
            for j in range(10):
                geolocation_service.process_location_update(
                    user_id=f"memory_test_user_{i}",
                    latitude=55.7558 + j*0.001,
                    longitude=37.6173 + j*0.001,
                    altitude=100,
                    battery_level=80
                )

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"   Initial Memory: {initial_memory:.1f} MB")
        print(f"   Final Memory: {final_memory:.1f} MB")
        print(f"   Memory Increase: {memory_increase:.1f} MB")

        # Memory increase should be reasonable (less than 100MB for this test)
        memory_acceptable = memory_increase < 100

        if memory_acceptable:
            print("   ✅ Memory usage is acceptable")
        else:
            print("   ⚠️  High memory usage detected")

        return memory_acceptable

    def test_real_time_update_performance(self):
        """Test real-time update performance."""
        print("\n⚡ Testing real-time update performance...")

        def realtime_update_request():
            # Simulate real-time location updates
            for i in range(20):
                location_data = {
                    "user_id": f"realtime_user_{time.time()}",
                    "latitude": 55.7558 + i*0.001,
                    "longitude": 37.6173 + i*0.001,
                    "altitude": 100 + i,
                    "battery_level": 85 - i
                }
                result = geolocation_service.process_location_update(**location_data)
                if not result["success"]:
                    return False
            return True

        metrics = self.measure_operation_performance(
            lambda: realtime_update_request(),
            "Real-time Location Updates",
            num_requests=30,
            num_threads=5
        )

        self.results.append(metrics)
        return metrics.success_rate() >= 90

    def test_multi_user_scenario_performance(self):
        """Test performance under multi-user scenario."""
        print("\n👥 Testing multi-user scenario performance...")

        def multi_user_request():
            # Simulate multiple users performing operations simultaneously
            operations = []

            # User registrations
            for i in range(3):
                user_data = {
                    "username": f"multi_scenario_user_{time.time()}_{i}",
                    "email": f"multi_scenario_{time.time()}_{i}@test.com",
                    "password": "testpass123",
                    "role": "user"
                }
                response = self.client.post("/api/auth/register", json=user_data)
                operations.append(response.status_code == 200)

            # Zone operations
            zone_data = {
                "name": f"Multi User Zone {time.time()}",
                "description": "Zone for multi-user testing",
                "coordinates": [
                    [55.7558, 37.6173],
                    [55.7658, 37.6273],
                    [55.7658, 37.6073],
                    [55.7558, 37.6173]
                ],
                "zone_type": "test",
                "alert_level": "low"
            }
            response = self.client.post("/api/zones/", json=zone_data, headers=self.admin_headers)
            operations.append(response.status_code == 200)

            # Alert operations
            alert_data = {
                "title": f"Multi User Alert {time.time()}",
                "message": "Alert for multi-user scenario testing",
                "severity": "low",
                "alert_type": "test"
            }
            response = self.client.post("/api/alerts/", json=alert_data, headers=self.admin_headers)
            operations.append(response.status_code == 200)

            return all(operations)

        metrics = self.measure_operation_performance(
            lambda: multi_user_request(),
            "Multi-User Scenario",
            num_requests=20,
            num_threads=5
        )

        self.results.append(metrics)
        return metrics.success_rate() >= 85

    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report."""
        report = {
            "summary": {
                "total_operations": sum(r.total_requests for r in self.results),
                "total_duration": sum(r.total_duration for r in self.results),
                "overall_success_rate": 0,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "results": [asdict(result) for result in self.results]
        }

        # Calculate overall success rate
        total_successful = sum(r.successful_requests for r in self.results)
        total_requests = sum(r.total_requests for r in self.results)
        report["summary"]["overall_success_rate"] = (total_successful / total_requests * 100) if total_requests > 0 else 0

        return report

    def print_performance_report(self, report: Dict):
        """Print formatted performance report."""
        summary = report["summary"]

        print("\n" + "=" * 80)
        print("🚀 FIREFLY STATION - PERFORMANCE TEST REPORT")
        print("=" * 80)
        print(f"Generated: {summary['timestamp']}")
        print(f"Total Operations: {summary['total_operations']}")
        print(f"Total Duration: {summary['total_duration']:.2f}s")
        print(f"Overall Success Rate: {summary['overall_success_rate']:.1f}%")
        print()

        # Individual test results
        print("📊 DETAILED RESULTS:")
        for result in report["results"]:
            print(f"\n  📈 {result['operation_name']}:")
            print(f"    Success Rate: {result['successful_requests']}/{result['total_requests']} ({result['successful_requests']/result['total_requests']*100:.1f}%)")
            print(f"    Response Time: {result['avg_response_time']:.3f}s avg, {result['p95_response_time']:.3f}s p95")
            print(f"    Throughput: {result['requests_per_second']:.1f} RPS")
            print(f"    Duration: {result['total_duration']:.2f}s")

        print("\n" + "=" * 80)

        # Performance assessment
        if summary["overall_success_rate"] >= 95:
            print("🎉 EXCELLENT: System performance is excellent!")
        elif summary["overall_success_rate"] >= 85:
            print("👍 GOOD: System performance is acceptable.")
        elif summary["overall_success_rate"] >= 70:
            print("⚠️  FAIR: System performance needs optimization.")
        else:
            print("🚨 POOR: System performance has significant issues.")

    def run_performance_suite(self) -> bool:
        """Run complete performance test suite."""
        print("🔥 Starting Firefly Station Performance & Load Test Suite")
        print("=" * 70)

        # Set up test environment
        self.setUp()

        # Run performance tests
        tests = [
            self.test_api_endpoint_performance,
            self.test_geolocation_processing_performance,
            self.test_database_operation_performance,
            self.test_concurrent_user_registration_performance,
            self.test_real_time_update_performance,
            self.test_multi_user_scenario_performance
        ]

        passed = 0
        total = len(tests)

        for test in tests:
            try:
                if test():
                    passed += 1
            except Exception as e:
                print(f"❌ Performance test {test.__name__} failed with exception: {e}")

        # Memory usage test
        memory_ok = self.test_memory_usage_monitoring()

        # Generate and print report
        report = self.generate_performance_report()
        self.print_performance_report(report)

        # Overall success
        overall_success = passed >= total * 0.8 and memory_ok  # 80% pass rate + memory OK

        if overall_success:
            print("✅ Performance tests completed successfully!")
        else:
            print("⚠️  Some performance tests failed or memory usage is high")

        return overall_success


def main():
    """Main function to run performance tests."""
    test_suite = PerformanceLoadTest()
    success = test_suite.run_performance_suite()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()