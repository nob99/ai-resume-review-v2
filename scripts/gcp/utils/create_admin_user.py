#!/usr/bin/env python3
"""
Create admin users in Cloud SQL production database.

This script creates admin users with secure bcrypt password hashing
using the same password utilities as the application.
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
    """Create PostgreSQL database URL."""
    return f"postgresql://postgres:{password}@127.0.0.1:5432/ai_resume_review_prod"


def create_admin_user(session, email: str, password: str, first_name: str, last_name: str):
    """
    Create an admin user with secure password hashing.

    Args:
        session: SQLAlchemy session
        email: User email
        password: Plain text password (will be hashed)
        first_name: User first name
        last_name: User last name
    """
    log_info(f"Creating admin user: {email}")

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
                "role": "admin",
                "is_active": True,
                "email_verified": True,
                "created_at": now,
                "updated_at": now,
                "password_changed_at": now,
                "failed_login_attempts": 0
            }
        )
        session.commit()
        log_success(f"Admin user created: {email} (ID: {user_id})")
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
    """Main function to create admin users."""
    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}Create Admin Users{NC}")
    print(f"{BLUE}========================================{NC}")
    print()

    # Get database password from environment
    db_password = os.environ.get("DB_PASSWORD")
    if not db_password:
        log_error("DB_PASSWORD environment variable not set")
        sys.exit(1)

    # Create database connection
    database_url = create_database_url(db_password)
    log_info("Connecting to database...")

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
    print(f"{BLUE}Creating 3 Admin Users{NC}")
    print(f"{BLUE}========================================{NC}")
    print()

    # Define 3 admin users
    admin_users = [
        {
            "email": "admin1@airesumereview.com",
            "password": "Admin123!@#SecurePass",
            "first_name": "Primary",
            "last_name": "Administrator"
        },
        {
            "email": "admin2@airesumereview.com",
            "password": "Admin456!@#SecurePass",
            "first_name": "Secondary",
            "last_name": "Administrator"
        },
        {
            "email": "admin3@airesumereview.com",
            "password": "Admin789!@#SecurePass",
            "first_name": "Backup",
            "last_name": "Administrator"
        }
    ]

    created_count = 0
    created_emails = []

    # Create each admin user
    for admin in admin_users:
        if create_admin_user(
            session,
            admin["email"],
            admin["password"],
            admin["first_name"],
            admin["last_name"]
        ):
            created_count += 1
            created_emails.append(admin["email"])
        print()

    # Verify users
    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}Verification{NC}")
    print(f"{BLUE}========================================{NC}")
    print()

    verify_users(session, [admin["email"] for admin in admin_users])

    # Summary
    print()
    print(f"{BLUE}========================================{NC}")
    print(f"{BLUE}Summary{NC}")
    print(f"{BLUE}========================================{NC}")
    print()

    log_info(f"Admin users created: {created_count}/3")
    print()

    if created_count > 0:
        print(f"{GREEN}Admin Credentials:{NC}")
        print()
        for i, admin in enumerate(admin_users, 1):
            if admin["email"] in created_emails or created_count == 0:  # Show all if some already existed
                print(f"  {BLUE}Admin {i}:{NC}")
                print(f"    Email:    {admin['email']}")
                print(f"    Password: {admin['password']}")
                print()

        log_warning("IMPORTANT: Save these credentials securely!")
        log_warning("Consider changing passwords after first login")

    # Close connection
    session.close()
    engine.dispose()

    print()
    log_success("Admin user creation complete!")
    print()


if __name__ == "__main__":
    main()
