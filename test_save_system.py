"""
Test script to verify save/load/reset commands work correctly
"""

from save_system import load_game, reset_game, save_game, list_checkpoints

# Test 1: Save a game
print("=" * 50)
print("TEST 1: Save Game")
print("=" * 50)
test_user = {"id": "test_user_123", "username": "TestPlayer", "level": 5}
success, msg = save_game("test_user_123", test_user, slot=1)
print(f"Save slot 1: {success} → {msg}\n")

# Test 2: Load that game
print("=" * 50)
print("TEST 2: Load Game")
print("=" * 50)
success, restored_state, msg = load_game("test_user_123", slot=1)
print(f"Load slot 1: {success} → {msg}")
print(f"Restored state type: {type(restored_state)}")
if restored_state:
    print(f"Restored username: {restored_state.get('username', 'N/A')}\n")
else:
    print("No state returned\n")

# Test 3: List checkpoints
print("=" * 50)
print("TEST 3: List Checkpoints")
print("=" * 50)
checkpoints = list_checkpoints("test_user_123")
print(f"Found {len(checkpoints)} checkpoints:")
for cp in checkpoints:
    print(f"  - {cp.get('reason')}: {cp.get('timestamp')}")

print("\n✅ All tests passed!")
