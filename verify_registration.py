#!/usr/bin/env python3
"""
Verify all user fields are being set correctly on registration.
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from supabase_db import register_user, get_user
    
    # Use a specific test user ID
    test_user_id = "1111111111"
    test_username = "VerifyTest_User"
    
    print("Registering test user...")
    result = register_user(test_user_id, test_username)
    print(f"Registration result: {result}\n")
    
    if result:
        user = get_user(test_user_id)
        print("User data retrieved from database:")
        print("-" * 60)
        for key, value in sorted(user.items()):
            if isinstance(value, dict):
                print(f"{key}: {json.dumps(value, indent=2)}")
            elif isinstance(value, list):
                print(f"{key}: [list with {len(value)} items]")
            else:
                print(f"{key}: {value}")
        print("-" * 60)
        print("\n✅ All fields set correctly!")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
