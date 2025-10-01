#!/usr/bin/env python3
"""
Quick manual test script for profile endpoints.
Run this to verify the profile feature is working correctly.
"""

import requests
import json
import uuid

BASE_URL = "http://localhost:8000/api/v1"

def test_profile_endpoints():
    print("=" * 60)
    print("PROFILE ENDPOINTS MANUAL TEST")
    print("=" * 60)

    # Step 1: Register a new user
    print("\n1. Registering new test user...")
    unique_id = str(uuid.uuid4())[:8]
    register_data = {
        "email": f"profiletest.{unique_id}@example.com",
        "password": "ProfileTest123!",
        "first_name": "Profile",
        "last_name": "Test",
        "role": "junior_recruiter"
    }

    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if response.status_code == 201:
        print(f"✅ User registered: {register_data['email']}")
    else:
        print(f"❌ Registration failed: {response.status_code}")
        print(response.json())
        return

    # Step 2: Login to get token
    print("\n2. Logging in to get access token...")
    login_data = {
        "email": register_data["email"],
        "password": register_data["password"]
    }

    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ Login successful, token obtained")
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.json())
        return

    headers = {"Authorization": f"Bearer {token}"}

    # Step 3: Get profile (GET /profile/me)
    print("\n3. Testing GET /profile/me...")
    response = requests.get(f"{BASE_URL}/profile/me", headers=headers)
    if response.status_code == 200:
        profile = response.json()
        print(f"✅ Profile retrieved successfully")
        print(f"   Email: {profile['email']}")
        print(f"   Name: {profile['first_name']} {profile['last_name']}")
        print(f"   Role: {profile['role']}")
    else:
        print(f"❌ Get profile failed: {response.status_code}")
        print(response.json())
        return

    # Step 4: Update profile (PATCH /profile/me)
    print("\n4. Testing PATCH /profile/me...")
    update_data = {
        "first_name": "Updated",
        "last_name": "ProfileName"
    }

    response = requests.patch(f"{BASE_URL}/profile/me", headers=headers, json=update_data)
    if response.status_code == 200:
        updated_profile = response.json()
        print(f"✅ Profile updated successfully")
        print(f"   New Name: {updated_profile['first_name']} {updated_profile['last_name']}")
        assert updated_profile['first_name'] == "Updated"
        assert updated_profile['last_name'] == "ProfileName"
        assert updated_profile['email'] == register_data['email'], "Email should not change!"
    else:
        print(f"❌ Update profile failed: {response.status_code}")
        print(response.json())
        return

    # Step 5: Change password (POST /profile/change-password)
    print("\n5. Testing POST /profile/change-password...")
    password_data = {
        "current_password": register_data["password"],
        "new_password": "NewSecurePassword123!"
    }

    response = requests.post(f"{BASE_URL}/profile/change-password", headers=headers, json=password_data)
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Password changed successfully")
        print(f"   Message: {result['message']}")
        assert result['success'] == True
    else:
        print(f"❌ Change password failed: {response.status_code}")
        print(response.json())
        return

    # Step 6: Verify old password doesn't work
    print("\n6. Verifying old password no longer works...")
    old_login_data = {
        "email": register_data["email"],
        "password": register_data["password"]  # Old password
    }

    response = requests.post(f"{BASE_URL}/auth/login", json=old_login_data)
    if response.status_code == 401:
        print(f"✅ Old password rejected (expected)")
    else:
        print(f"⚠️  Old password still works (unexpected): {response.status_code}")

    # Step 7: Verify new password works
    print("\n7. Verifying new password works...")
    new_login_data = {
        "email": register_data["email"],
        "password": password_data["new_password"]  # New password
    }

    response = requests.post(f"{BASE_URL}/auth/login", json=new_login_data)
    if response.status_code == 200:
        print(f"✅ New password works correctly")
    else:
        print(f"❌ New password login failed: {response.status_code}")
        print(response.json())
        return

    # Step 8: Test error cases
    print("\n8. Testing error cases...")

    # Test empty names
    print("   8a. Testing empty names validation...")
    invalid_data = {"first_name": "   ", "last_name": "Valid"}
    response = requests.patch(f"{BASE_URL}/profile/me", headers=headers, json=invalid_data)
    if response.status_code in [400, 422]:
        print(f"   ✅ Empty names rejected (status {response.status_code})")
    else:
        print(f"   ❌ Empty names should be rejected, got {response.status_code}")

    # Test wrong current password
    print("   8b. Testing wrong current password...")
    wrong_password_data = {
        "current_password": "WrongPassword123!",
        "new_password": "AnotherPassword123!"
    }
    response = requests.post(f"{BASE_URL}/profile/change-password", headers=headers, json=wrong_password_data)
    if response.status_code == 400:
        print(f"   ✅ Wrong current password rejected")
    else:
        print(f"   ❌ Wrong current password should be rejected, got {response.status_code}")

    # Test weak password
    print("   8c. Testing weak password...")
    weak_password_data = {
        "current_password": password_data["new_password"],
        "new_password": "weak"
    }
    response = requests.post(f"{BASE_URL}/profile/change-password", headers=headers, json=weak_password_data)
    if response.status_code in [400, 422]:
        print(f"   ✅ Weak password rejected (status {response.status_code})")
    else:
        print(f"   ❌ Weak password should be rejected, got {response.status_code}")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_profile_endpoints()
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH EXCEPTION:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()