#!/usr/bin/env python3
"""
Create test users in Cloud SQL staging database.

This script creates test users for staging environment with secure bcrypt
password hashing using the same password utilities as the application.
"""

import sys
import os
import uuid
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

# Import database and security utilities
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.security import PasswordHasher
from app.core.datetime_utils import utc_now

# Color codes for output
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
NC = '\033[0m'  # No Color


def log_info(msg: str):
    """Log info message."""
    print(f"{BLUE}ℹ {NC}{msg}")


def log_success(msg: str):
    """Log success message."""
    print(f"{GREEN}✓ {NC}{msg}")


def log_error(msg: str):
    """Log error message."""
    print(f"{RED}✗ {NC}{msg}")


def log_warning(msg: str):
    """Log warning message."""
    print(f"{YELLOW}⚠ {NC}{msg}")


def create_database_url(password: str) -> str:
    """Create PostgreSQL database URL for staging."""
    return f"postgresql://postgres:{password}@127.0.0.1:5432/ai_resume_review_staging"


def create_user(session, email: str, password: str, first_name: str, last_name: str, role: str = "consultant"):
    """
    Create a test user with secure password hashing.

    Args:
        session: SQLAlchemy session
        email: User email
        password: Plain text password (will be hashed)
        first_name: User first name
        last_name: User last name
        role: User role (default: consultant)
    """
    log_info(f"Creating test user: {email} (role: {role})")

    # Check if user already exists
    result = session.execute(
        text("SELECT id, email FROM users WHERE email = :email"),
        {"email": email}
    )
    existing_user = result.fetchone()

    if existing_user:
        log_warning(f"User already exists: {email}")
        return False

    # Hash password using application's password hasher
    try:
        password_hasher = PasswordHasher()
        password_hash = password_hasher.hash_password(password)
        log_success("Password hashed successfully (bcrypt, 12 rounds)")
    except Exception as e:
        log_error(f"Password hashing failed: {e}")
        return False

    # Generate UUID for user
    user_id = uuid.uuid4()
    now = utc_now()

    # Insert user
    try:
        session.execute(
            text("""
                INSERT INTO users (
                    id, email, password_hash, first_name, last_name,
                    role, is_active, email_verified,
                    created_at, updated_at, password_changed_at,
                    failed_login_attempts
                ) VALUES (
                    :id, :email, :password_hash, :first_name, :last_name,
                    :role, :is_active, :email_verified,
                    :created_at, :updated_at, :password_changed_at,
                    :failed_login_attempts
                )
            """),
            {
                "id": str(user_id),
                "email": email,
                "password_hash": password_hash,
                "first_name": first_name,
                "last_name": last_name,
                "role": role,
                "is_active": True,
                "email_verified": True,
                "created_at": now,
                "updated_at": now,
                "password_changed_at": now,
                "failed_login_attempts": 0
            }
        )
        session.commit()
        log_success(f"User created: {email} (ID: {user_id}, Role: {role})")
        return True
    except Exception as e:
        session.rollback()
        log_error(f"Failed to create user: {e}")
        return False


def verify_users(session, emails: list):
    """Verify that users were created successfully."""
    log_info("Verifying created users...")

    for email in emails:
        result = session.execute(
            text("""
                SELECT email, first_name, last_name, role, is_active, email_verified, created_at
                FROM users
                WHERE email = :email
            """),
            {"email": email}
        )
        user = result.fetchone()

        if user:
            log_success(f"✓ {user[0]} - {user[1]} {user[2]} ({user[3]})")
        else:
            log_error(f"✗ User not found: {email}")


def main():
    """Main function to create test users."""
    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}Create Staging Test Users{NC}")
    print(f"{BLUE}========================================{NC}")
    print()

    # Get database password from environment
    db_password = os.environ.get("DB_PASSWORD")
    if not db_password:
        log_error("DB_PASSWORD environment variable not set")
        sys.exit(1)

    # Create database connection
    database_url = create_database_url(db_password)
    log_info("Connecting to staging database...")

    try:
        engine = create_engine(database_url, echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()
        log_success("Database connection established")
    except Exception as e:
        log_error(f"Database connection failed: {e}")
        sys.exit(1)

    print()
    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}Creating Test Users{NC}")
    print(f"{BLUE}========================================{NC}")
    print()

    # Define test users for staging
    test_users = [
        {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "first_name": "Test",
            "last_name": "User",
            "role": "consultant"
        },
        {
            "email": "admin@example.com",
            "password": "AdminPassword123!",
            "first_name": "Admin",
            "last_name": "User",
            "role": "admin"
        }
    ]

    created_count = 0
    created_emails = []

    # Create each test user
    for user in test_users:
        if create_user(
            session,
            user["email"],
            user["password"],
            user["first_name"],
            user["last_name"],
            user["role"]
        ):
            created_count += 1
            created_emails.append(user["email"])
        print()

    # Verify users
    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}Verification{NC}")
    print(f"{BLUE}========================================{NC}")
    print()

    verify_users(session, [user["email"] for user in test_users])

    # Summary
    print()
    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}Summary{NC}")
    print(f"{BLUE}========================================{NC}")
    print()

    log_info(f"Test users created: {created_count}/{len(test_users)}")
    print()

    if created_count > 0:
        print(f"{GREEN}Test User Credentials:{NC}")
        print()
        for i, user in enumerate(test_users, 1):
            if user["email"] in created_emails or created_count == 0:  # Show all if some already existed
                print(f"  {BLUE}User {i} ({user['role']}):{NC}")
                print(f"    Email:    {user['email']}")
                print(f"    Password: {user['password']}")
                print()

        log_info("These are test credentials for staging environment only")
        log_warning("Do NOT use these credentials in production!")

    # Close connection
    session.close()
    engine.dispose()

    print()
    log_success("Test user creation complete!")
    print(f"{BLUE}You can now login at: https://ai-resume-review-v2-frontend-staging-wnjxxf534a-uc.a.run.app{NC}")
    print()


if __name__ == "__main__":
    main()
