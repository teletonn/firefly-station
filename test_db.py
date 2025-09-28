#!/usr/bin/env python3
"""Test script for database operations."""

import database

def test_database_operations():
    print("Testing database operations...")

    # Test init_db
    try:
        database.init_db()
        print("✓ Database initialization successful")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return

    # Test get_bot_stats
    try:
        stats = database.get_bot_stats()
        print(f"✓ Bot stats retrieved: {stats}")
    except Exception as e:
        print(f"✗ Bot stats retrieval failed: {e}")

    # Test insert_or_update_user
    try:
        test_user_data = {
            "user": {"longName": "Test User", "shortName": "TU"},
            "position": {"latitude": 55.7558, "longitude": 37.6173, "altitude": 100},
            "deviceMetrics": {"batteryLevel": 85}
        }
        database.insert_or_update_user("test_user_123", test_user_data)
        print("✓ User insertion/update successful")
    except Exception as e:
        print(f"✗ User insertion/update failed: {e}")

    # Test get_user
    try:
        user = database.get_user("test_user_123")
        if user:
            print(f"✓ User retrieval successful: {user['long_name']}")
        else:
            print("✗ User not found")
    except Exception as e:
        print(f"✗ User retrieval failed: {e}")

    # Test insert_message
    try:
        database.insert_message("sender_123", "receiver_456", "Test message", "outgoing")
        print("✓ Message insertion successful")
    except Exception as e:
        print(f"✗ Message insertion failed: {e}")

    # Test get_messages_for_user
    try:
        messages = database.get_messages_for_user("sender_123", limit=10)
        print(f"✓ Messages retrieval successful: {len(messages)} messages found")
    except Exception as e:
        print(f"✗ Messages retrieval failed: {e}")

    # Test register_user
    try:
        public_key = database.register_user("test_user_123", "TestNick")
        if public_key:
            print("✓ User registration successful")
        else:
            print("✗ User registration failed")
    except Exception as e:
        print(f"✗ User registration failed: {e}")

    print("Database operations test completed.")

if __name__ == "__main__":
    test_database_operations()