#!/usr/bin/env python3
"""
Test script for the geolocation system.
This script tests the core functionality of the geolocation system.
"""

import sys
import os
import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend import database
from backend.geolocation import geolocation_service

def test_database_initialization():
    """Test database initialization and table creation."""
    print("Testing database initialization...")
    try:
        database.init_db()
        print("✅ Database initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def test_zone_creation():
    """Test zone creation functionality."""
    print("Testing zone creation...")
    try:
        # Create a test zone
        zone_id = database.create_zone(
            name="Test Zone",
            description="A test zone for geolocation",
            center_latitude=55.7558,
            center_longitude=37.6176,
            radius_meters=1000,
            created_by=1
        )

        if zone_id:
            print(f"✅ Zone created successfully with ID: {zone_id}")

            # Test zone retrieval
            zone = database.get_zone(zone_id)
            if zone and zone['name'] == "Test Zone":
                print("✅ Zone retrieval working correctly")
                return True
            else:
                print("❌ Zone retrieval failed")
                return False
        else:
            print("❌ Zone creation failed")
            return False
    except Exception as e:
        print(f"❌ Zone creation test failed: {e}")
        return False

def test_geolocation_service():
    """Test geolocation service functionality."""
    print("Testing geolocation service...")
    try:
        # Test location processing
        result = geolocation_service.process_location_update(
            user_id="test_user_001",
            latitude=55.7558,
            longitude=37.6176,
            altitude=100,
            accuracy=10,
            battery_level=85
        )

        if result['success']:
            print("✅ Location processing working correctly")
            print(f"   - Motion state: {result['is_moving']}")
            print(f"   - Speed: {result['speed_mps']:.2f} m/s")
            print(f"   - Alerts created: {result['alerts_created']}")
            return True
        else:
            print("❌ Location processing failed")
            return False
    except Exception as e:
        print(f"❌ Geolocation service test failed: {e}")
        return False

def test_user_group_creation():
    """Test user group creation functionality."""
    print("Testing user group creation...")
    try:
        # Create a test user group
        group_id = database.create_user_group(
            name="Test Group",
            description="A test group for users",
            created_by=1
        )

        if group_id:
            print(f"✅ User group created successfully with ID: {group_id}")

            # Test adding user to group
            success = database.add_user_to_group("test_user_001", group_id, 1)
            if success:
                print("✅ User added to group successfully")
                return True
            else:
                print("❌ Failed to add user to group")
                return False
        else:
            print("❌ User group creation failed")
            return False
    except Exception as e:
        print(f"❌ User group test failed: {e}")
        return False

def test_location_history():
    """Test location history functionality."""
    print("Testing location history...")
    try:
        # Insert location history
        success = database.insert_location_history(
            user_id="test_user_001",
            latitude=55.7558,
            longitude=37.6176,
            altitude=100,
            accuracy=10,
            speed=5.5,
            battery_level=85,
            is_moving=True
        )

        if success:
            print("✅ Location history insertion working correctly")

            # Test retrieval
            history = database.get_location_history("test_user_001", limit=5)
            if history and len(history) > 0:
                print(f"✅ Location history retrieval working (found {len(history)} records)")
                return True
            else:
                print("❌ Location history retrieval failed")
                return False
        else:
            print("❌ Location history insertion failed")
            return False
    except Exception as e:
        print(f"❌ Location history test failed: {e}")
        return False

def test_offline_support():
    """Test offline support functionality."""
    print("Testing offline support...")
    try:
        # Test offline location storage
        result = geolocation_service.process_offline_location_update(
            user_id="test_user_002",
            latitude=55.7558,
            longitude=37.6176,
            altitude=95,
            accuracy=15,
            battery_level=70
        )

        if result['success']:
            print("✅ Offline location storage working correctly")

            # Test offline queue status
            status = geolocation_service.get_offline_queue_status()
            if 'total_unsynced_entries' in status:
                print(f"✅ Offline queue status working (entries: {status['total_unsynced_entries']})")

                # Test sync functionality
                sync_result = geolocation_service.sync_offline_data()
                if sync_result['success']:
                    print(f"✅ Offline sync working (synced: {sync_result.get('synced_count', 0)})")
                    return True
                else:
                    print("❌ Offline sync failed")
                    return False
            else:
                print("❌ Offline queue status failed")
                return False
        else:
            print("❌ Offline location storage failed")
            return False
    except Exception as e:
        print(f"❌ Offline support test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Starting Geolocation System Tests")
    print("=" * 50)

    tests = [
        test_database_initialization,
        test_zone_creation,
        test_geolocation_service,
        test_user_group_creation,
        test_location_history,
        test_offline_support,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        print()
        if test():
            passed += 1
        print("-" * 30)

    print()
    print("=" * 50)
    print(f"🧪 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Geolocation system is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)