#!/usr/bin/env python3
"""
Database initialization script to ensure an admin user exists.
This script checks if an admin user exists and creates one if none is found.
"""

import sys
import os
import logging
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database import get_connection, get_admin_user_by_username, create_admin_user
from backend.auth import get_password_hash

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_admin_user():
    """Initialize admin user if none exists."""
    try:
        # Check if admin user already exists
        existing_admin = get_admin_user_by_username('admin')

        if existing_admin:
            logger.info("✓ Admin user 'admin' already exists in database")
            logger.info(f"  - Username: {existing_admin['username']}")
            logger.info(f"  - Email: {existing_admin['email']}")
            logger.info(f"  - Role: {existing_admin['role']}")
            logger.info(f"  - Created: {existing_admin['created_at']}")
            if existing_admin['last_login']:
                logger.info(f"  - Last login: {existing_admin['last_login']}")
            return True

        # Admin user doesn't exist, create one
        logger.info("No admin user found. Creating default admin user...")

        # Hash the default password
        hashed_password = get_password_hash('admin123')

        # Create the admin user with super_admin role
        admin_id = create_admin_user(
            username='admin',
            email='admin@localhost',
            hashed_password=hashed_password,
            role='super_admin'
        )

        if admin_id:
            logger.info("✓ Successfully created admin user")
            logger.info("  - Username: admin")
            logger.info("  - Password: admin123")
            logger.info("  - Email: admin@localhost")
            logger.info("  - Role: super_admin")
            logger.info("  - User ID: " + str(admin_id))
            logger.warning("⚠️  IMPORTANT: Please change the default password after first login!")
            return True
        else:
            logger.error("✗ Failed to create admin user")
            return False

    except Exception as e:
        logger.error(f"✗ Error initializing admin user: {e}")
        return False

def main():
    """Main function to run the initialization."""
    print("=" * 60)
    print("ADMIN USER INITIALIZATION SCRIPT")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    success = init_admin_user()

    print()
    print("=" * 60)
    if success:
        print("✅ INITIALIZATION COMPLETED SUCCESSFULLY")
        print()
        print("You can now log in with:")
        print("  Username: admin")
        print("  Password: admin123")
        print()
        print("Don't forget to change the default password!")
    else:
        print("❌ INITIALIZATION FAILED")
        print("Please check the error messages above.")
        sys.exit(1)

    print("=" * 60)

if __name__ == "__main__":
    main()