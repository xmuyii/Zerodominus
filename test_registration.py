#!/usr/bin/env python3
"""
Test script to verify new player registration works without shield_cooldown errors.
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test with Supabase
print("=" * 60)
print("TESTING SUPABASE REGISTRATION")
print("=" * 60)

try:
    from supabase_db import register_user, get_user
    
    # Test registration with a new user
    test_user_id = "9999999999"
    test_username = "TestPlayer_" + str(int(__import__('time').time()) % 10000)
    
    print(f"\n1. Attempting to register user: {test_user_id} as '{test_username}'")
    result = register_user(test_user_id, test_username)
    print(f"   Registration result: {result}")
    
    if result:
        print("\n2. Verifying registration - fetching user...")
        user = get_user(test_user_id)
        if user:
            print(f"   ✅ User found in database!")
            print(f"   Username: {user.get('username')}")
            print(f"   Level: {user.get('level')}")
            print(f"   XP: {user.get('xp')}")
            print(f"   Bitcoin: {user.get('bitcoin')}")
            print(f"   Base Name: {user.get('base_name')}")
            print(f"\n✅ SUPABASE REGISTRATION SUCCESSFUL!")
        else:
            print(f"   ❌ User NOT found after registration")
    else:
        print(f"   ❌ Registration returned False")
        
except Exception as e:
    print(f"\n❌ ERROR with Supabase: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
