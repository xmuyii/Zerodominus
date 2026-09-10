# -*- coding: utf-8 -*-
"""
supabase_db_patch.py — Patch instructions for supabase_db.py
=============================================================
This file contains the EXACT changes to make to supabase_db.py
to wire in Phase 1 & 2 systems. Do NOT copy this file as-is —
apply the changes described below to the existing supabase_db.py.

CHANGE 1: Add import at the top of supabase_db.py
──────────────────────────────────────────────────
Add after existing imports:

    from teleport_system import on_user_load

CHANGE 2: Modify get_user() to call on_user_load
─────────────────────────────────────────────────
Find your existing get_user() function. It likely looks like:

    def get_user(user_id: str) -> dict | None:
        try:
            r = supabase.table(DB_TABLE).select("*").eq("user_id", str(user_id)).execute()
            if r.data:
                return r.data[0]
            return None
        except Exception as e:
            print(f"[DB ERROR] get_user: {e}")
            return None

Change it to:

    def get_user(user_id: str) -> dict | None:
        try:
            r = supabase.table(DB_TABLE).select("*").eq("user_id", str(user_id)).execute()
            if r.data:
                user = r.data[0]
                # Run all passive migrations and ticks on every load
                user = on_user_load(user)
                return user
            return None
        except Exception as e:
            print(f"[DB ERROR] get_user: {e}")
            return None

CHANGE 3: Add a getter-pattern helper used by teleport/march systems
─────────────────────────────────────────────────────────────────────
Some systems need to both get AND save users via a single callable.
Add this function anywhere in supabase_db.py:

    def get_or_save_user(user_id: str, data: dict | None) -> dict | None:
        '''
        If data is None: acts as getter — returns user dict.
        If data is dict: acts as setter — saves and returns None.
        Used by systems that need to inject DB access without circular imports.
        '''
        if data is None:
            return get_user(user_id)
        else:
            save_user(user_id, data)
            return None

CHANGE 4: register_user() — ensure credits field is set
────────────────────────────────────────────────────────
(This was the bug that blocked all Fusion players.)
Make sure register_user() includes credits: 0 in the initial record:

    def register_user(user_id, username, ...):
        user_data = {
            "user_id":      str(user_id),
            "username":     username,
            "credits":      0,           # ← REQUIRED — was missing, caused NULL errors
            "xp":           0,
            "level":        1,
            "bitcoin":      0,
            "military":     {"pawns": 5},
            "buildings":    {},
            "researches":   {},
            "inventory":    {},          # ← New stacked format from day one
            "unclaimed_items": [],
            "teleport_charges": 0,
            "home_sector":  None,        # Set when player chooses base plot
            "commander_location": {"sector_id": 1},  # Start in Sector 1
            "base_shielded": False,
            "shield_expires_at": None,
            "active_suit":  None,
            "energy":       100,         # Start with 100 energy
            "energy_last_regen": None,
            "march_queue":  [],
            "research_queue": {},
            "banishments":  {},
            "visas":        {},
            "alliance_id":  None,
            "alliance_role": None,
        }
        ...

THAT'S IT. Four changes to supabase_db.py.
Everything else in Phase 1 & 2 is self-contained.
"""

# ═══════════════════════════════════════════════════════════════════════════
#  STANDALONE VALIDATION — Run this to test all Phase 2 systems together
# ═══════════════════════════════════════════════════════════════════════════

def run_phase2_validation():
    """
    Self-contained validation of all Phase 2 systems.
    Run with: python3 supabase_db_patch.py
    """
    import sys, types
    sys.path.insert(0, '.')

    # Mock supabase_db
    mock_db = types.ModuleType('supabase_db')
    mock_db.get_user  = lambda uid: None
    mock_db.save_user = lambda uid, data: None
    sys.modules['supabase_db'] = mock_db

    # Mock sectors_system
    mock_sec = types.ModuleType('sectors_system')
    mock_sec.get_sector_info = lambda sid: {
        "name": f"Sector {sid}", "emoji": "🌍", "lore": "Ancient lands."
    }
    sys.modules['sectors_system'] = mock_sec

    from datetime import datetime, timedelta

    print("=" * 55)
    print("PHASE 2 VALIDATION")
    print("=" * 55)

    # ── 1. March Queue ────────────────────────────────────────
    print("\n1. MARCH QUEUE")
    from march_queue import (
        create_march, get_arrived_marches, format_march_queue_display,
        apply_speedup_to_march, cancel_march, purge_old_marches
    )

    user = {
        "user_id": "p1", "username": "TestCommander",
        "military": {"footmen": 200, "archers": 100, "lancers": 50},
        "inventory": {"speedup_5m": {"qty": 3, "display": "5min Speedup", "emoji": "⏩", "category": "utility"}},
        "researches": {"siege_tactics": True, "basic_military": True},
        "march_queue": [],
    }

    ok, msg, user = create_march(
        user, "occupy", 3, "A", "The Ironjaw Tunnels",
        {"footmen": 50, "archers": 20}, "same_sector"
    )
    print(f"  Create march (occupy): {'✅' if ok else '❌'} {msg[:60]}")
    assert ok, "march creation failed"
    assert user["military"]["footmen"] == 150, "troops not deducted"

    # Apply speedup
    march_id = user["march_queue"][0]["march_id"]
    ok2, msg2, user = apply_speedup_to_march(user, march_id, "speedup_5m")
    print(f"  Apply speedup: {'✅' if ok2 else '❌'} {msg2[:60]}")
    assert ok2
    assert user["inventory"]["speedup_5m"]["qty"] == 2, "speedup not consumed"

    # Cancel march
    ok3, msg3, user = cancel_march(user, march_id)
    print(f"  Cancel march: {'✅' if ok3 else '❌'} {msg3[:60]}")
    assert ok3
    assert user["military"]["footmen"] == 200, "troops not returned"
    print("  March queue: PASS ✅")

    # ── 2. Suit System ────────────────────────────────────────
    print("\n2. SUIT SYSTEM")
    from suit_system import (
        equip_suit, get_active_suit, is_protected_against,
        can_enter_node, format_suit_status, apply_hazard_penalty,
        get_suit_time_remaining
    )

    user2 = {
        "user_id": "p2", "username": "SuitTester",
        "researches": {"hazard_awareness": True},
        "inventory": {
            "basic_suit": {"qty": 2, "display": "Basic Suit", "emoji": "🧪", "category": "protective_item"}
        },
        "active_suit": None,
        "military": {"footmen": 100},
        "home_sector": 1,
        "commander_location": {"sector_id": 6},
        "current_node": None,
    }

    ok, msg, user2 = equip_suit(user2, "basic_suit")
    print(f"  Equip basic_suit: {'✅' if ok else '❌'} {msg[:60]}")
    assert ok
    assert user2["inventory"]["basic_suit"]["qty"] == 1, "suit not consumed"
    assert get_active_suit(user2) is not None, "suit not active"

    protected = is_protected_against(user2, "lethal_heat")
    print(f"  Protected vs lethal_heat: {'✅' if protected else '❌'}")
    assert protected

    not_protected = is_protected_against(user2, "void_radiation")
    print(f"  Not protected vs void_radiation: {'✅' if not not_protected else '❌'}")
    assert not not_protected

    # Stack prevention
    ok2, msg2, user2 = equip_suit(user2, "basic_suit")
    print(f"  Stack prevention: {'✅' if not ok2 else '❌'}")
    assert not ok2, "should not allow stacking"

    suit_display = format_suit_status(user2)
    print(f"  Suit display: {suit_display[:60]}")
    assert "remaining" in suit_display
    print("  Suit system: PASS ✅")

    # ── 3. Teleport System ────────────────────────────────────
    print("\n3. TELEPORT SYSTEM")
    from teleport_system import (
        claim_daily_teleports, get_daily_claim_status,
        can_teleport_to, purchase_teleport_charges,
        format_teleport_menu, post_sector_chat, read_sector_chat,
        get_sector_intelligence_from_chat, set_alliance_safe_sector,
        set_visa_policy, check_visa_required, format_charge_status
    )

    user3 = {
        "user_id": "p3", "username": "TeleportTester",
        "teleport_charges": 0,
        "researches": {},
        "banishments": {},
        "inventory": {},
        "home_sector": 1,
    }

    # Claim daily
    ok, msg, user3 = claim_daily_teleports(user3)
    print(f"  Claim daily: {'✅' if ok else '❌'} {msg[:60]}")
    assert ok
    assert user3["teleport_charges"] == 3

    # Double claim
    ok2, msg2, user3 = claim_daily_teleports(user3)
    print(f"  Double claim blocked: {'✅' if not ok2 else '❌'}")
    assert not ok2

    # Can teleport check
    can, reason = can_teleport_to(user3, 1)
    print(f"  Can teleport to S1: {'✅' if can else '❌'}")
    assert can

    # Research-locked sector
    can2, reason2 = can_teleport_to(user3, 9)
    print(f"  S9 locked (no void_theory): {'✅' if not can2 else '❌'} {reason2[:50]}")
    assert not can2

    # Sector chat
    sector_state = {"sector_chat": [], "active_jam": None}
    sector_state, _ = post_sector_chat(sector_state, "p3", "TeleportTester", "Anyone here?")
    sector_state, _ = post_sector_chat(sector_state, "p4", "OtherPlayer", "Just arrived!")
    sector_state, _ = post_sector_chat(sector_state, "SYSTEM", "SYSTEM", "Phase changed: Iron Surge", is_system=True)

    chat_display = read_sector_chat(sector_state, "p3", user3, limit=10)
    print(f"  Sector chat ({len(sector_state['sector_chat'])} msgs): ✅")
    assert len(sector_state["sector_chat"]) == 3

    # Intelligence from chat
    intel = get_sector_intelligence_from_chat(sector_state)
    print(f"  Chat intel extracted: {list(intel.keys())} ✅")
    assert "p3" in intel and "p4" in intel

    # Alliance safe zone
    leader = {"user_id": "l1", "username": "AllianceLeader", "alliance_role": "LEADER"}
    alliance = {"safe_sectors": []}
    ok3, msg3, alliance = set_alliance_safe_sector(leader, 3, alliance, safe=True)
    print(f"  Set safe zone: {'✅' if ok3 else '❌'} {msg3[:50]}")
    assert 3 in alliance["safe_sectors"]

    # Visa policy
    sector_state2 = {"dominance": {"ruler_id": "l1", "ruler_name": "AllianceLeader"}}
    ok4, msg4, sector_state2 = set_visa_policy(leader, 3, sector_state2, [2, 4])
    print(f"  Set visa policy: {'✅' if ok4 else '❌'} {msg4[:50]}")
    assert sector_state2["dominance"]["visa_policy"]["enabled"]

    # Visa check
    user_from_s2 = {"user_id": "p5", "home_sector": 2, "visas": {}}
    needs_visa, visa_msg = check_visa_required(user_from_s2, 3, sector_state2)
    print(f"  Visa required for S2 player: {'✅' if needs_visa else '❌'}")
    assert needs_visa

    user_from_s1 = {"user_id": "p6", "home_sector": 1, "visas": {}}
    needs_visa2, _ = check_visa_required(user_from_s1, 3, sector_state2)
    print(f"  S1 player exempt from visa: {'✅' if not needs_visa2 else '❌'}")
    assert not needs_visa2

    print("  Teleport system: PASS ✅")

    # ── 4. on_user_load migration ─────────────────────────────
    print("\n4. ON_USER_LOAD / MIGRATION")
    from teleport_system import on_user_load

    old_user = {
        "user_id": "p7",
        "username": "OldFormatPlayer",
        "unclaimed_items": [
            {"key": "xp_small", "amount": 21},
            {"key": "xp_small", "amount": 21},
            {"key": "iron",     "amount": 5},
            {"key": "iron",     "amount": 3},
            {"key": "basic_suit", "amount": 1},
        ],
        "researches": {},
        "research_queue": {},
        "base_resources": {"resources": {"wood": 100}},
        "energy": 50,
        "energy_last_regen": None,
    }

    migrated = on_user_load(old_user)
    print(f"  Inventory migrated: {'✅' if isinstance(migrated['inventory'], dict) else '❌'}")
    assert isinstance(migrated["inventory"], dict)
    assert migrated["inventory"]["xp_small"]["qty"] == 42, f"got {migrated['inventory'].get('xp_small')}"
    assert migrated["inventory"]["iron"]["qty"] == 8
    assert migrated["unclaimed_items"] == []
    print(f"  XP stacked: xp_small ×{migrated['inventory']['xp_small']['qty']} ✅")
    print(f"  Iron stacked: iron ×{migrated['inventory']['iron']['qty']} ✅")
    print("  Migration: PASS ✅")

    print("\n" + "=" * 55)
    print("ALL PHASE 2 TESTS PASSED ✅")
    print("=" * 55)
    print("\nFiles ready to deploy:")
    print("  phase2/march_queue.py")
    print("  phase2/suit_system.py")
    print("  phase2/teleport_system.py")
    print("  Apply 4 changes from supabase_db_patch.py to supabase_db.py")


if __name__ == "__main__":
    run_phase2_validation()
"""
supabase_db.py — Supabase persistence layer for The 64 Game
============================================================
Key fixes vs previous version:
  - add_points: accumulates; never resets within same week; week key is ISO date
  - add_unclaimed_item: xp_reward stored correctly on each item
  - claim_item: moves item by its unique 'id', not fragile list index
  - remove_inventory_item: uses unique item 'id'
  - Shield: stored with expiry timestamp; is_shielded() helper
  - Crate XP: super_crate=50-200, wood=50-100, bronze=100-150, iron=150-200
"""
from typing import Tuple
import os
import json
import random
from datetime import datetime, timedelta, UTC
from supabase import create_client, Client
from base_layout import get_default_base_layout
from teleport_system import on_user_load
from config import DB_TABLE, SUPABASE_URL as CONFIG_SUPABASE_URL, SUPABASE_KEY as CONFIG_SUPABASE_KEY, ENV_NAME

SUPABASE_URL = os.environ.get('SUPABASE_URL', CONFIG_SUPABASE_URL).rstrip('/')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', CONFIG_SUPABASE_KEY)
SECTORS_FILE = os.environ.get('SECTORS_FILE', 'sectors.txt')

# Items that stack into a single inventory slot.
# Claiming more of a stackable just increments quantity on the existing slot —
# no extra backpack space consumed. Add new item types here as needed.
STACKABLE_ITEMS = {
    'super_crate', 'wood_crate', 'bronze_crate', 'iron_crate',
    'shield_potion', 'free_teleport', 'teleport', 'shield',
}

# Initialize Supabase with error handling for invalid credentials
supabase: Client = None
try:
    if SUPABASE_URL and SUPABASE_KEY and 'your' not in SUPABASE_KEY.lower():
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"[OK] Supabase module loaded (Environment: {ENV_NAME}, Table: {DB_TABLE})")
    else:
        print(f"[WARNING] Supabase credentials not configured - running in offline mode")
except Exception as e:
    print(f"[WARNING] Supabase connection failed: {e} - running in offline mode")


# ── Random Base Names ──────────────────────────────────────────────────────

DEFAULT_BASE_NAMES = [
    "Iron Fortress", "Stone Keep", "Bronze Citadel", "The Stronghold",
    "Crystal Tower", "Shadow Bastion", "Eagle's Nest", "Dragon's Lair",
    "Obsidian Hall", "Midnight Manor", "The Throne", "Kingdom's Crown",
    "Warrior's Peak", "Sentinel Post", "The Ramparts", "Silver Spire",
    "Timber Lodge", "Crimson Hold", "The Garrison", "Paladin's Rest",
    "Raven's Keep", "Phoenix Rising", "Stormhold", "Avalon Castle",
    "Winterfort", "Sunkeep", "Moonlight Bridge", "Starlight Citadel",
    "Ironheart Keep", "Ravenstorm", "The Bulwark", "Dreadfort",
    "Whitewall", "Blackthorne", "Mystic Tower", "The Sanctuary",
    "Skyward Spire", "Earthen Vault", "Twilight Realm", "The Citadel",
]


# ═══════════════════════════════════════════════════════════════════════════
# PASTE BLOCK 3 — safe_json and normalize_user (fixes the append crash)
# ═══════════════════════════════════════════════════════════════════════════

import json as _json

# ── Week helper ────────────────────────────────────────────────────────────

def _current_week_key() -> str:
    """ISO date string of the Monday that starts this week (Mon-Sun). Resets Monday 00:00 WAT (Sunday 11:59 PM)."""
    today = datetime.now(UTC) + timedelta(hours=1)
    days_since_monday = today.weekday()   # Monday=0 … Sunday=6
    monday = today - timedelta(days=days_since_monday)
    return monday.date().isoformat()


def _fix_item_ids(items_list: list) -> list:
    """Fix items with None/missing IDs by assigning them proper sequential IDs."""
    if not items_list:
        return []
    
    # Find the highest existing ID
    valid_ids = [it.get('id') for it in items_list if it.get('id') is not None]
    next_id = (max(valid_ids) if valid_ids else 0) + 1
    
    # Fix items with None IDs
    for item in items_list:
        if item.get('id') is None:
            item['id'] = next_id
            next_id += 1
    
    return items_list


def _next_id(lst: list) -> int:
    """Generate a unique integer ID that is 1 higher than any existing id."""
    if not lst:
        return 1
    # Get max ID, treating None as 0
    valid_ids = [it.get('id', 0) for it in lst if it.get('id') is not None]
    if not valid_ids:
        return 1
    return max(valid_ids) + 1


# ── Raw DB helpers ─────────────────────────────────────────────────────────

def _row_to_user(row: dict) -> dict:
    """Normalise a raw Supabase row into the in-memory user dict."""
    u = dict(row)
    # Integers
    for k, default in [('weekly_points', 0), ('all_time_points', 0),
                        ('total_words', 0), ('xp', 0), ('bitcoin', 0),
                        ('level', 1), ('last_level', 1), ('backpack_slots', 5)]:
        u[k] = int(u.get(k) or default)
    # Normalize week_start to just the date part (Supabase may return full timestamp)
    if u.get('week_start'):
        u['week_start'] = u['week_start'].split('T')[0]
    
    # JSONB fields may arrive as string or list/dict
    for k in ('inventory', 'unclaimed_items'):
        val = u.get(k, '[]')
        if isinstance(val, str):
            try:
                u[k] = json.loads(val)
            except Exception:
                u[k] = []
        elif val is None:
            u[k] = []
        # Defensive: ensure it's always a list (e.g. registered as {} by old code)
        if not isinstance(u.get(k), list):
            u[k] = []
    
    # Parse military, traps, buffs, buildings, weapons JSONB fields
    for k in ('military', 'traps', 'buffs', 'weapons', 'buildings', 'building_queue'):
        val = u.get(k, '{}')
        if isinstance(val, str):
            try:
                u[k] = json.loads(val)
            except Exception:
                u[k] = {}
        elif val is None:
            u[k] = {}
    
    # Parse base_resources JSONB field with COMPLETE structure
    val = u.get('base_resources', '{}')
    if isinstance(val, str):
        try:
            base_res = json.loads(val)
        except Exception:
            base_res = {}
    elif val is None:
        base_res = {}
    else:
        base_res = dict(val) if val else {}
    
    # CRITICAL: Ensure base_resources has complete resource types (wood, bronze, iron, stone, relics)
    # NOT silver - we use stone as the 4th tier
    if 'resources' not in base_res or not isinstance(base_res.get('resources'), dict):
        base_res['resources'] = {}
    
    # Ensure ALL resource types exist (don't rely on stored value which might have old structure)
    default_resources = {'wood': 0, 'bronze': 0, 'iron': 0, 'stone': 0, 'relics': 0, 'incubus': 0}
    stored_resources = base_res.get('resources', {})
    
    # Merge: keep stored values but ensure all keys exist
    for res_type, default_val in default_resources.items():
        if res_type not in stored_resources:
            stored_resources[res_type] = default_val
    
   
   
    
    base_res['resources'] = stored_resources
    
    # Ensure food and streak exist
    if 'food' not in base_res:
        base_res['food'] = 0
    if 'current_streak' not in base_res:
        base_res['current_streak'] = 0
    
    u['base_resources'] = base_res
     # Handle base_layout
    if isinstance(u.get("base_layout"), str):
        try:
            u["base_layout"] = json.loads(u["base_layout"])
        except:
            u["base_layout"] = get_default_base_layout()
    elif not u.get("base_layout"):
        u["base_layout"] = get_default_base_layout()
    
    
    return u


def get_user(user_id: str) -> dict | None:
    try:
        r = supabase.table(DB_TABLE).select("*").eq(
            "user_id", str(user_id)
        ).execute()
        if r.data:
            user = r.data[0]
            user = normalize_user(user)      # Fix all JSON fields
            from teleport_system import on_user_load
            user = on_user_load(user)        # Run passive ticks
            user = sync_player_passive_energy(user)  # Recalculate energy every load, not just on use
            return user
        return None
    except Exception as e:
        print(f"[DB ERROR] get_user: {e}")
        return None
    
def get_or_save_user(user_id: str, data: dict | None) -> dict | None:
    '''
    If data is None: acts as getter — returns user dict.
    If data is dict: acts as setter — saves and returns None.
    Used by systems that need to inject DB access without circular imports.
    '''
    if data is None:
        return get_user(user_id)
    else:
        save_user(user_id, data)
        return None
    
def save_user(user_id, data: dict):
    d = dict(data)
    d.pop('id', None)
    # Extract base/resources data to save separately
    base_data = d.pop('base', None)
    resources_data = d.pop('resources', None)
    
    # Exclude fields that don't exist in DB schema
    # These are tracked in memory but not persisted to database
    d.pop('challenges', None)
    d.pop('metadata', None)
    d.pop('training_queue', None)
    d.pop('shield_cooldown', None)  # Shield cooldown doesn't exist in schema
    d.pop('prestige', None)  # Prestige tier is in-memory only, not in DB
    
    # Serialize JSONB fields (inventory, unclaimed_items, military, traps, buffs, base_resources, weapons, buildings, building_queue)
    for k in ('inventory', 'unclaimed_items', 'military', 'traps', 'buffs', 'weapons', 'buildings', 'building_queue'):
        if isinstance(d.get(k), (list, dict)):
            d[k] = json.dumps(d[k])
    
    # Serialize base resources data if present
    if base_data or resources_data:
        # Combine base and resources into one structure
        base_structure = base_data or {}
        if resources_data and 'resources' not in base_structure:
            base_structure['resources'] = resources_data
        if base_structure:
            d['base_resources'] = json.dumps(base_structure)
    
    # Also serialize base_resources if it's a dict (not already JSON string)
    if isinstance(d.get('base_resources'), dict):
        d['base_resources'] = json.dumps(d['base_resources'])
    
    supabase.table(DB_TABLE).update(d).eq('user_id', str(user_id)).execute()


def register_user(user_id, username: str):
    """Create a fresh account. Returns True on success, False on failure."""
    try:
        uid = str(user_id)
        r = supabase.table(DB_TABLE).select('user_id, username').eq('user_id', uid).execute()
        if r.data:
            if r.data[0].get('username') != username:
                supabase.table(DB_TABLE).update({'username': username}).eq('user_id', uid).execute()
            return True  # Already registered
        
        random_base_name = random.choice(DEFAULT_BASE_NAMES)
        supabase.table(DB_TABLE).insert({
            'user_id': uid,
            'username': username,
            'all_time_points': 0,
            'weekly_points': 0,
            'week_start': _current_week_key(),
            'total_words': 0,
            'bitcoin': 0,
            'xp': 0,
            'energy': 100,
            'power': 0,
            'gold': 0,
            'level': 1,
            'last_level': 1,
            "teleport_charges": 0,
            "home_sector":  None, # Set when player chooses base plot
            "commander_location": {"sector_id": 1},  # Start in Sector 1
            "base_shielded": False,
            "shield_expires_at": None,
            "active_suit":  None,
            "energy_last_regen": None,
            "march_queue":  [],
            "research_queue": {},
            "banishments":  {},
            "visas":        {},
            "alliance_id":  None,
            "alliance_role": None,
            'backpack_slots': 5,
            'inventory': json.dumps([]),
            'unclaimed_items': json.dumps([]),
            "researches":   {},
            'sector': None,
            'completed_tutorial': False,
            'base_name': random_base_name,
            'base_hq_level': 1,
            'login_streak': 0,
            'buildings': json.dumps({}),
            'building_queue': json.dumps({}),
            'base_resources': json.dumps({
                'resources': {'wood': 0, 'bronze': 0, 'iron': 0, 'stone': 0, 'relics': 0, 'incubus': 0},
                'food': 0,
                'current_streak': 0
            }),
            'military': json.dumps({"pawns": 5}),
            'traps': json.dumps({"spike_pit": 0}),
            'shield_status': '⚠️ UNPROTECTED',
            'credits': 0,
            'active_perks': {},
            'chess_stats': json.dumps({
                'rating': 1000,
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'current_streak': 0,
                'best_streak': 0,
                'total_games': 0
            }),
        }).execute()
        print(f"[REGISTER SUCCESS] User {uid} ({username}) registered to Supabase")
        return True  # Registration succeeded
    except Exception as e:
        print(f"[REGISTER ERROR] Failed to register {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return False  # Registration failed
def global_weekly_reset() -> bool:
    """
    Hard-resets weekly_points for ALL players in the database.
    Run this at Sunday midnight WAT / Monday 00:00 AM via a cron scheduler.
    """
    this_week = _current_week_key()
    try:
        print("[RESET] Starting global weekly points reset...")
        
        # 1. Fetch all rows that currently have weekly points or game-specific weekly points > 0
        # (This prevents modifying every single row if your DB scales up)
        result = supabase.table(DB_TABLE).select("user_id").gt("weekly_points", 0).execute()
        players_to_reset = result.data or []
        
        if not players_to_reset:
            print("[RESET] No active weekly scores found to clear.")
            return True
            
        print(f"[RESET] Clearing weekly scores for {len(players_to_reset)} players...")
        
        # 2. Update their records globally
        for row in players_to_reset:
            uid = row.get("user_id")
            payload = {
                'weekly_points': 0,
                'week_start': this_week,
                # Clear game specific columns if you use them:
                'fusion_weekly_points': 0,
                'fusion_week_start': this_week
            }
            supabase.table(DB_TABLE).update(payload).eq('user_id', uid).execute()
            
        print("[RESET] Global weekly slate wiped successfully!")
        return True
    except Exception as e:
        print(f"[RESET ERROR] Failed global reset: {e}")
        return False
    
def get_game_weekly_leaderboard(game_type="fusion", limit=10):
    """
    Weekly leaderboard for a specific game type.
    Tries the game-specific column (e.g. fusion_weekly_points).
    If that column doesn't exist or is empty, falls back to shared weekly_points.
    No week_start filtering — trust the stored value.
    """
    game_field = f"{game_type}_weekly_points"

    try:
        r = supabase.table(DB_TABLE) \
            .select(f"user_id, username, {game_field}, shield_status, name_shield_until") \
            .gt(game_field, 0) \
            .order(game_field, desc=True) \
            .limit(limit) \
            .execute()

        raw = r.data or []
        print(f"[LB] {game_field}: {len(raw)} rows returned")

        results = []
        for p in raw:
            pts = int(p.get(game_field) or 0)
            if pts <= 0:
                continue
            results.append({
                'id':                p['user_id'],
                'username':          p.get('username', 'Unknown'),
                'points':            pts,
                'shield_status':     p.get('shield_status') or '⚠️ UNPROTECTED',
                'name_shield_until': p.get('name_shield_until') or "Expired",
            })

        if results:
            print(f"[LB] {game_field}: returning {len(results)} players")
            return results

    except Exception as e:
        print(f"[LB] {game_field} not available ({e}) — using shared weekly_points fallback")

    # Fallback: use shared weekly_points (guaranteed to exist)
    return get_weekly_leaderboard(limit=limit)


def get_game_alltime_leaderboard(game_type="fusion", limit=10):
    """
    All-time leaderboard for a specific game type.
    Tries the game-specific column (e.g. fusion_all_time_points).
    Falls back to shared all_time_points if missing or empty.
    """
    game_field = f"{game_type}_all_time_points"

    try:
        r = supabase.table(DB_TABLE) \
            .select(f"user_id, username, {game_field}, is_bot, shield_status, name_shield_until") \
            .gt(game_field, 0) \
            .order(game_field, desc=True) \
            .limit(limit) \
            .execute()

        raw = r.data or []
        print(f"[LB] {game_field}: {len(raw)} rows returned")

        results = []
        for p in raw:
            if p.get('is_bot'):
                continue
            pts = int(p.get(game_field) or 0)
            if pts <= 0:
                continue
            results.append({
                'id':                p['user_id'],
                'username':          p.get('username', 'Unknown'),
                'points':            pts,
                'shield_status':     p.get('shield_status') or '⚠️ UNPROTECTED',
                'name_shield_until': p.get('name_shield_until') or "Expired",
            })

        if results:
            print(f"[LB] {game_field}: returning {len(results)} players")
            return results

    except Exception as e:
        print(f"[LB] {game_field} not available ({e}) — using shared all_time_points fallback")

    # Fallback: shared all_time_points (guaranteed to exist)
    return get_alltime_leaderboard(limit=limit)


def ensure_bot_exists(username: str, initial_points: int = 0):
    """Ensure a bot account exists in the database. Returns user_id."""
    # First find by username and is_bot=True
    r = supabase.table(DB_TABLE).select('user_id').eq('username', username).eq('is_bot', True).execute()
    if r.data:
        return r.data[0]['user_id']
        
    # Generate a unique pseudo user_id for the bot
    import hashlib
    bot_id = "bot_" + hashlib.md5(username.encode()).hexdigest()[:12]
    
    random_base_name = random.choice(DEFAULT_BASE_NAMES)
    supabase.table(DB_TABLE).upsert({
        'user_id': bot_id,
        'username': username,
        'is_bot': True,
        'all_time_points': 0,
        'weekly_points': initial_points,
        'week_start': _current_week_key(),
        'total_words': 0,
        'bitcoin': 0,
        'xp': 0,
        'level': 1,
        'last_level': 1,
        'backpack_slots': 5,
        'backpack_image': 'normal_backpack',
        'inventory': json.dumps([]),
        'unclaimed_items': json.dumps([]),
        'base_name': random_base_name,
        'base_resources': json.dumps({
            'resources': {'wood': 0, 'bronze': 0, 'iron': 0, 'stone': 0, 'relics': 0},
            'food': 0,
            'current_streak': 0
        }),
        'military': json.dumps({}),
        'traps': json.dumps({}),
        'shield_status': 'UNPROTECTED'
    }).execute()
    
    return bot_id


# ── Points (weekly + all-time) ─────────────────────────────────────────────

def add_points(user_id, points: int, username: str = '', game_type: str = 'fusion'):
    """
    Persist points for a player. Uses read-compute-write with full logging
    so any failure is visible in the Railway logs immediately.
    """
    uid       = str(user_id)
    this_week = _current_week_key()

    try:
        # ── Read current state ─────────────────────────────────────────────
        user = get_user(uid)
        if not user:
            register_user(uid, username)
            user = get_user(uid)
        if not user:
            print(f"[ADD_POINTS] CRITICAL: cannot find or create user {uid}")
            return

        last_week_date = (user.get('week_start') or '').split('T')[0]
        old_weekly     = int(user.get('weekly_points') or 0)
        old_alltime    = int(user.get('all_time_points') or 0)
        old_words      = int(user.get('total_words') or 0)

        # Reset weekly if week has rolled over
        new_weekly  = points if last_week_date != this_week else old_weekly + points
        new_alltime = old_alltime + points
        new_words   = old_words + 1

        payload = {
            'weekly_points':   new_weekly,
            'all_time_points': new_alltime,
            'total_words':     new_words,
            'week_start':      this_week,
        }

        # ── Write ──────────────────────────────────────────────────────────
        result = supabase.table(DB_TABLE).update(payload).eq('user_id', uid).execute()

        if not (hasattr(result, 'data') and result.data):
            # Supabase returned empty — the user_id column value didn't match.
            # This happens when the PK column is named 'id' not 'user_id'.
            print(f"[ADD_POINTS] WARNING: eq('user_id') matched nothing for {uid} — checking DB schema")
            # Probe: fetch the row to see what column holds our ID
            probe = supabase.table(DB_TABLE).select('id, user_id').limit(1).execute()
            if probe.data:
                sample = probe.data[0]
                print(f"[ADD_POINTS] Sample row keys: {list(sample.keys())}")
                # If 'user_id' is a column but our value didn't match, the user might not exist
                # Try inserting a fresh registration then retrying
                register_user(uid, username or 'Player')
                supabase.table(DB_TABLE).update(payload).eq('user_id', uid).execute()
        else:
            print(f"[ADD_POINTS] ✅ {username or uid}: +{points}pts → weekly={new_weekly} alltime={new_alltime}")

        # ── Game-specific columns (best-effort, ignore if missing) ─────────
        gw_key  = f"{game_type}_weekly_points"
        ga_key  = f"{game_type}_all_time_points"
        gws_key = f"{game_type}_week_start"
        gw_prev = int(user.get(gw_key) or 0)
        ga_prev = int(user.get(ga_key) or 0)
        gw_date = (user.get(gws_key) or '').split('T')[0]

        new_gw = points if gw_date != this_week else gw_prev + points
        new_ga = ga_prev + points
        try:
            supabase.table(DB_TABLE).update({
                gw_key:  new_gw,
                ga_key:  new_ga,
                gws_key: this_week,
            }).eq('user_id', uid).execute()
        except Exception:
            pass  # columns don't exist yet — core points already saved

    except Exception as e:
        print(f"[ADD_POINTS] EXCEPTION for {uid}: {e}")
        import traceback
        traceback.print_exc()


def add_xp(user_id, amount: int) -> bool:
    user = get_user(str(user_id))
    if not user:
        return False
        
    user['xp'] = user.get('xp', 0) + amount
    
    # Simple Progressive Curve: Each level requires (Level * 150) XP
    # Level 1->2: 150 XP | Level 2->3: 300 XP | Level 10->11: 1500 XP
    current_xp = user['xp']
    lvl = 1
    while True:
        xp_needed_for_next = lvl * 150
        if current_xp >= xp_needed_for_next:
            current_xp -= xp_needed_for_next
            lvl += 1
        else:
            break
            
    user['level'] = lvl
    save_user(str(user_id), user)
    return True

def use_xp(user_id, amount: int) -> bool:
    user = get_user(str(user_id))
    if not user or user.get('xp', 0) < amount:
        return False
    user['xp'] -= amount
    save_user(str(user_id), user)
    return True


def add_bitcoin(user_id, amount: int, username: str = ''):
    user = get_user(str(user_id))
    if not user:
        register_user(user_id, username)
        user = get_user(str(user_id))
    user['bitcoin'] = user.get('bitcoin', 0) + amount
    save_user(str(user_id), user)


def award_word_score(user_id: str, pts: int, xp: int, bitcoin: int,
                     resources: dict, username: str = '', game_type: str = 'fusion', user_obj=None) -> dict:
    """
    ONE function, ONE DB read, ONE DB write for the entire word-score pipeline.
    Returns the updated user dict so the caller can use it without re-fetching.
    
    Pass user_obj to avoid redundant DB fetch if user was already loaded.
    
    Replaces: add_points() + add_xp() + add_bitcoin() + get_user() + save_user()
    That was 8-10 Supabase round-trips. This is 2 (read + write).
    """
    uid       = str(user_id)
    this_week = _current_week_key()

    # ── Single read ────────────────────────────────────────────────────────
    # Use passed user object if available, otherwise fetch from DB
    if user_obj:
        user = user_obj
    else:
        user = get_user(uid)
        if not user:
            register_user(uid, username)
            user = get_user(uid)
    if not user:
        return {}

    last_week_date = (user.get('week_start') or '').split('T')[0]
    old_weekly     = int(user.get('weekly_points') or 0)
    old_alltime    = int(user.get('all_time_points') or 0)
    old_words      = int(user.get('total_words') or 0)
    old_xp         = int(user.get('xp') or 0)
    old_bitcoin    = int(user.get('bitcoin') or 0)

    new_weekly     = pts if last_week_date != this_week else old_weekly + pts
    new_alltime    = old_alltime + pts
    new_words      = old_words + 1
    new_xp         = old_xp + xp
    new_level      = 1 + (new_xp // 100)
    new_bitcoin    = old_bitcoin + bitcoin

    # Game-specific weekly/alltime
    gw_key         = f"{game_type}_weekly_points"
    ga_key         = f"{game_type}_all_time_points"
    gw_date        = (user.get(f"{game_type}_week_start") or '').split('T')[0]
    gw_prev        = int(user.get(gw_key) or 0)
    ga_prev        = int(user.get(ga_key) or 0)
    new_gw         = pts if gw_date != this_week else gw_prev + pts
    new_ga         = ga_prev + pts

    # Resources
    base_res       = user.get('base_resources', {})
    if not isinstance(base_res, dict):
        base_res   = {}
    res_dict       = base_res.get('resources', {})
    if not isinstance(res_dict, dict):
        res_dict   = {}
    for rt, am in resources.items():
        res_dict[rt] = res_dict.get(rt, 0) + am
    base_res['resources'] = res_dict

    # ── Single write ───────────────────────────────────────────────────────
    payload = {
        'weekly_points':   new_weekly,
        'all_time_points': new_alltime,
        'total_words':     new_words,
        'week_start':      this_week,
        'xp':              new_xp,
        'level':           new_level,
        'bitcoin':         new_bitcoin,
        'base_resources':  json.dumps(base_res),
    }

    # Add game-specific fields (silently skipped by Supabase if columns missing)
    try:
        supabase.table(DB_TABLE).update({
            **payload,
            gw_key:                           new_gw,
            ga_key:                           new_ga,
            f"{game_type}_week_start":        this_week,
        }).eq('user_id', uid).execute()
    except Exception as e:
        # Game-specific columns don't exist — write core only
        try:
            supabase.table(DB_TABLE).update(payload).eq('user_id', uid).execute()
        except Exception as e:
            print(f"[AWARD_WORD] ❌ write failed for {uid}: {e}")
            return user

    # Update the in-memory user object for the caller
    user.update({
        'weekly_points':   new_weekly,
        'all_time_points': new_alltime,
        'total_words':     new_words,
        'week_start':      this_week,
        'xp':              new_xp,
        'level':           new_level,
        'bitcoin':         new_bitcoin,
        'base_resources':  base_res,
        gw_key:            new_gw,
        ga_key:            new_ga,
    })

    print(f"[AWARD_WORD] ✅ {username or uid}: +{pts}pts +{xp}xp +{bitcoin}btc "
          f"(weekly={new_weekly} alltime={new_alltime})")
    return user


def use_bitcoin(user_id, amount: int) -> bool:
    user = get_user(str(user_id))
    if not user or user.get('bitcoin', 0) < amount:
        return False
    user['bitcoin'] -= amount
    save_user(str(user_id), user)
    return True


def add_resources_from_word_length(user_id, word_length: int, username: str = '') -> dict:
    """Award resources based on word length: 3L→Wood, 4L→Bronze, 5L→Iron, 6L→Stone, 7L→Relics"""
    uid = str(user_id)
    user = get_user(uid)
    if not user:
        register_user(uid, username)
        user = get_user(uid)
    
    # Initialize resources if not present
    if 'resources' not in user or not isinstance(user.get('resources'), dict):
        user['resources'] = {'wood': 0, 'bronze': 0, 'iron': 0, 'stone': 0, 'relics': 0, 'incubus': 0}
    
    resources_awarded = {}
    
    # Award resources based on word length
    if word_length == 3:
        user['resources']['wood'] = user['resources'].get('wood', 0) + 1
        resources_awarded['wood'] = 1
    elif word_length == 4:
        user['resources']['bronze'] = user['resources'].get('bronze', 0) + 1
        resources_awarded['bronze'] = 1
    elif word_length == 5:
        user['resources']['iron'] = user['resources'].get('iron', 0) + 1
        resources_awarded['iron'] = 1
    elif word_length == 6:
        user['resources']['stone'] = user['resources'].get('stone', 0) + 1
        resources_awarded['stone'] = 1  # Different from the 'bitcoin' currency
    elif word_length >= 7:
        user['resources']['relics'] = user['resources'].get('relics', 0) + 1
        resources_awarded['relics'] = 1
    
    save_user(uid, user)
    return resources_awarded


def update_streak_and_award_food(user_id, correct: bool, username: str = '', user_obj=None) -> dict:
    """Track consecutive correct words and award food when streak >= 3.
    Store streak and food in base_resources JSONB, not as separate columns.
    
    Pass user_obj to avoid redundant DB fetch if user was already loaded."""
    uid = str(user_id)
    
    # Use passed user object if available, otherwise fetch from DB
    if user_obj:
        user = user_obj
    else:
        user = get_user(uid)
        if not user:
            register_user(uid, username)
            user = get_user(uid)
    
    # Initialize base_resources if not present
    if not user.get('base_resources'):
        user['base_resources'] = {
            'resources': {'wood': 0, 'bronze': 0, 'iron': 0, 'stone': 0, 'relics': 0, 'incubus': 0},
            'food': 0,
            'current_streak': 0
        }
    
    base_res = user['base_resources']
    if not isinstance(base_res, dict):
        base_res = {
            'resources': {'wood': 0, 'bronze': 0, 'iron': 0, 'stone': 0, 'relics': 0, 'incubus': 0},
            'food': 0,
            'current_streak': 0
        }
        user['base_resources'] = base_res
    
    food_awarded = 0
    streak_status = "broken"
    old_streak = base_res.get('current_streak', 0)
    old_food = base_res.get('food', 0)
    
    if correct:
        base_res['current_streak'] = base_res.get('current_streak', 0) + 1
        current_streak = base_res['current_streak']
        
        # Award food based on streak
        if current_streak >= 3:
            # Award 1 food per streak (so 3-streak = 1 food, 4-streak = 2 food, etc.)
            food_to_award = current_streak - 2
            base_res['food'] = base_res.get('food', 0) + food_to_award
            food_awarded = food_to_award
            streak_status = f"streak_{current_streak}"
            print(f"[STREAK_CALC] Streak {old_streak}→{current_streak}, Rations: {old_food}→{base_res['food']} (+{food_to_award})")
        else:
            print(f"[STREAK_CALC] Streak {old_streak}→{current_streak}, Rations: 0 (need 3)")
    else:
        # Wrong word - reset streak
        base_res['current_streak'] = 0
        streak_status = "broken"
        print(f"[STREAK_CALC] Reset streak from {old_streak} to 0")
    
    user['base_resources'] = base_res
    save_user(uid, user)
    
    return {
        "streak": base_res.get('current_streak', 0),
        "food_awarded": food_awarded,
        "status": streak_status
    }


def set_sector(user_id, sector_id):
    user = get_user(str(user_id))
    if user:
        user['sector'] = sector_id
        save_user(str(user_id), user)


# ── Leaderboards ───────────────────────────────────────────────────────────

def get_weekly_leaderboard(limit: int = 10) -> list:
    """
    Return top players by weekly_points.
    Shows anyone with weekly_points > 0.
    We trust the stored value — add_points resets it when the week rolls over.
    No week_start filter here (that was hiding valid scores due to timezone drift).
    """
    try:
        r = supabase.table(DB_TABLE) \
            .select('user_id, username, weekly_points, shield_status, name_shield_until') \
            .gt('weekly_points', 0) \
            .order('weekly_points', desc=True) \
            .limit(limit) \
            .execute()

        raw = r.data or []
        print(f"[LB] weekly: {len(raw)} rows returned")

        results = []
        for p in raw:
            pts = int(p.get('weekly_points') or 0)
            if pts <= 0:
                continue
            results.append({
                'id':                p['user_id'],
                'username':          p.get('username', 'Unknown'),
                'points':            pts,
                'shield_status':     p.get('shield_status') or '⚠️ UNPROTECTED',
                'name_shield_until': p.get('name_shield_until') or "Expired",
            })

        print(f"[LB] weekly: returning {len(results)} players")
        return results

    except Exception as e:
        print(f"[ERROR] get_weekly_leaderboard: {e}")
        import traceback
        traceback.print_exc()
        return []


def get_alltime_leaderboard(limit: int = 10) -> list:
    try:
        r = supabase.table(DB_TABLE) \
            .select('user_id, username, all_time_points, total_words, is_bot, shield_status, name_shield_until') \
            .gt('all_time_points', 0) \
            .order('all_time_points', desc=True) \
            .limit(limit * 5) \
            .execute()

        raw = r.data or []
        print(f"[LB] alltime: {len(raw)} rows returned")
        results = [
            {
                'id':                p['user_id'],
                'username':          p.get('username', 'Unknown'),
                'points':            int(p.get('all_time_points') or 0),
                'words':             int(p.get('total_words') or 0),
                'shield_status':     p.get('shield_status') or '⚠️ UNPROTECTED',
                'name_shield_until': p.get('name_shield_until') or "Expired",
            }
            for p in raw
            if not p.get('is_bot') and int(p.get('all_time_points') or 0) > 0
        ]
        return results[:limit]
    except Exception as e:
        print(f"[ERROR] get_alltime_leaderboard: {e}")
        import traceback
        traceback.print_exc()
        return []


# ── Inventory ──────────────────────────────────────────────────────────────
def get_inventory_item(user: dict, item_key: str) -> dict:
    """Safely retrieves an item from the user's inventory list array.
    Matches on either 'item_key' (Schema A) or 'type' (Schema B) since
    both field names can appear on inventory rows.
    """
    inventory = user.get("inventory", []) or []
    for item in inventory:
        if isinstance(item, dict) and (item.get("item_key") == item_key or item.get("type") == item_key):
            return item
    return {}

def add_inventory_item(user: dict, item_key: str, qty: int, display_name: str, category: str = "consumable", xp_reward: int = 0, multiplier_value: int = 0) -> dict:
    """Adds an item or increments its quantity safely, ensuring no data loss.
    Writes BOTH field-name schemas so every inventory-reading code path works:
      Schema A: item_key / qty / display   (used by get_inventory_item, store purchases)
      Schema B: type / quantity            (used by claim_item, most of main.py's display/use code)
    """
    if not isinstance(user.get("inventory"), list):
        user["inventory"] = []  # never silently accept a dict/None here

    # Check if the player already owns at least one copy of this item
    item = get_inventory_item(user, item_key)
    if item:
        new_qty = item.get("qty", item.get("quantity", 0)) + qty
        item["qty"]      = new_qty
        item["quantity"] = new_qty
    else:
        from supabase_db import _next_id
        user["inventory"].append({
            "id": _next_id(user["inventory"]),
            # Schema A
            "item_key": item_key,
            "qty": qty,
            "display": display_name,
            "category": category,
            # Schema B aliases
            "type": item_key,
            "quantity": qty,
            "name": display_name,
            "xp_reward": xp_reward,
            "multiplier_value": multiplier_value,
            "acquired": datetime.utcnow().isoformat(),
        })
    return user

def remove_inventory_item(user: Dict[str, Any], item_key: str) -> Dict[str, Any]:
    """Removes one instance of an item by key."""
    inventory = user.get("inventory", [])
    
    for item in inventory:
        if item.get("item_key") == item_key:
            if item.get("quantity", 1) > 1:
                item["quantity"] -= 1
            else:
                inventory.remove(item)
            break
            
    user["inventory"] = inventory
    return user

def get_max_slots(user: dict) -> int:
    """Helper to return max backpack slots, defaulting to 20 if missing."""
    return int(user.get('backpack_slots', 5))

def is_backpack_full(user: dict) -> bool:
    """
    Checks if the total unique item slots used exceeds the maximum allowed slots.
    Note: Stackable items grouped in a single dictionary count as 1 slot.
    """
    current_slots_used = len(user.get('inventory', []) or [])
    max_slots = get_max_slots(user)
    return current_slots_used >= max_slots

def upgrade_backpack(user_id, additional_slots: int = 5) -> Tuple[bool, str]:
    """
    Increases the player's total storage cap and updates their backpack tier aesthetics.
    """
    user = get_user(str(user_id))
    if not user:
        return False, "❌ Player profile not found."
        
    current_slots = get_max_slots(user)
    new_slots = current_slots + additional_slots
    
    user['backpack_slots'] = new_slots
    
    # Dynamically scale tiers based on slot sizes
    if new_slots >= 40:
        user['backpack_image'] = 'military_tactical_pack'
    elif new_slots >= 30:
        user['backpack_image'] = 'premium_vault_backpack'
    else:
        user['backpack_image'] = 'normal_backpack'
        
    save_user(str(user_id), user)
    return True, f"✅ Backpack upgraded successfully! Max capacity increased from {current_slots} ➡️ {new_slots} slots."
# ── Shield helpers ──────────────────────────────────────────────────────

def is_shielded(user: dict) -> bool:
    """Return True if user has an active (non-disrupted) shield.
    
    Shield statuses:
    - UNPROTECTED: No shield active
    - ACTIVE: Shield is on
    - DISRUPTED: Shield was hit, no protection for 1 attack
    """
    shield_status = user.get('shield_status', 'UNPROTECTED')
    
    # Only ACTIVE shields provide protection
    if shield_status == 'ACTIVE':
        return True
    
    # DISRUPTED or UNPROTECTED = no shield
    if shield_status in ['DISRUPTED', 'UNPROTECTED']:
        return False
    
    # Legacy support for old fields
    exp = user.get('shield_expires')
    if exp and exp != 'permanent':
        # Check if expiry time has passed
        try:
            if datetime.utcnow() < datetime.fromisoformat(exp):
                return True
        except Exception:
            pass
    
    return False


def activate_shield(user_id: str, item_key: str) -> tuple[bool, str]:
    """
    Activate a shield from the player's backpack.
    Completely replaces old timers with a clean current window duration (Overwrites).
    Returns (success_boolean, status_message).
    """
    user = get_user(user_id)
    if not user:
        return False, "❌ User profile not found."

    # Fetch item configuration from catalog
    from store_system import STORE_ITEMS
    shield_data = STORE_ITEMS.get(item_key)
    if not shield_data:
        return False, "❌ Shield configurations not found."
        
    shield_status = user.get('shield_status', 'UNPROTECTED')
    
    # Can't activate if shield is DISRUPTED (recently hit)
    if shield_status == 'DISRUPTED':
        return False, "⚠️ Your shield is DISRUPTED from an attack. Wait for it to auto-restore."
    
    # ── OVERWRITE LOGIC ──
    # Note: We removed the block that stops players if shield_status == 'ACTIVE'.
    # This allows a new shield item to completely replace the previous time duration window.

    hours = shield_data.get("duration_h", 8)
    now = datetime.utcnow()
    
    # 💥 CRITICAL OVERWRITE FIX: Calculate from right now, replacing any existing expiration
    new_expiration = (now + timedelta(hours=hours)).isoformat()
    
    # Update user object values
    user['shield_status'] = 'ACTIVE'
    user["base_shielded"] = True
    user["shield_expires_at"] = new_expiration
    user.pop('shield_cooldown', None)  # Clear old structural cooldown tracking flags safely
    
    # Save back to database
    save_user(user_id, user)
    
    return True, f"🛡️ Shield activated successfully! Base protected for the next {hours} hours."

def reset_all_shields():
    """Reset all players' shields to UNPROTECTED (in-memory only)."""
    try:
        users = supabase.table(DB_TABLE).select('user_id').execute().data
        reset_count = 0
        for user_data in users:
            try:
                user_id = user_data.get('user_id')
                user = get_user(user_id)
                if user:
                    # Reset shield status in-memory (not saved to DB)
                    user['shield_status'] = 'UNPROTECTED'
                    user.pop('shield_expires', None)  # Remove legacy permanent shield
                    user.pop('shield_cooldown', None)  # Clear any cooldowns
                    # NOTE: These changes are NOT persisted to database
                    # (shield_status column doesn't exist in schema)
                    reset_count += 1
            except Exception as e:
                # Silently continue - in-memory operations don't fail on DB issues
                continue
        print(f"[OK] All shields reset to UNPROTECTED status (in-memory)")
        return reset_count
    except Exception as e:
        print(f"[ERROR] reset_all_shields failed: {e}")
        return 0


# ── Unclaimed items ────────────────────────────────────────────────────────

def _crate_xp(item_type: str) -> int:
    """Return a proper random XP value for a given crate type."""
    t = item_type.lower()
    if 'super' in t:
        return random.randint(50, 200)
    elif 'wood' in t:
        return random.randint(50, 100)
    elif 'bronze' in t:
        return random.randint(100, 150)
    elif 'iron' in t:
        return random.randint(150, 200)
    return random.randint(30, 80)


def add_unclaimed_item(user_id, item_type: str, amount: int = 1,
                        xp_reward: int = None, multiplier_value: int = 0):
    """Add an unclaimed reward. xp_reward is auto-set for crates if not supplied."""
    user = get_user(str(user_id))
    if not user:
        return
    unclaimed = user.get('unclaimed_items', [])
    # Ensure unclaimed is a list (defensive: could be dict from old registrations or bad DB state)
    if not isinstance(unclaimed, list):
        unclaimed = list(unclaimed.values()) if isinstance(unclaimed, dict) else []
    # Auto-assign XP for crates
    if xp_reward is None:
        xp_reward = _crate_xp(item_type) if 'crate' in item_type.lower() else 0

    unclaimed.append({
        'id':               _next_id(unclaimed),
        'type':             item_type,
        'amount':           amount,
        'xp_reward':        xp_reward,
        'multiplier_value': multiplier_value,
        'created_at':       datetime.utcnow().isoformat(),
    })
    user['unclaimed_items'] = unclaimed
    save_user(str(user_id), user)

def get_unclaimed_items(user_id) -> list:
    user = get_user(str(user_id))
    if not user:
        return []
    unclaimed = user.get('unclaimed_items', [])
    # Fix any items with None IDs
    unclaimed = _fix_item_ids(unclaimed)
    # Save the fixed unclaimed back if any items were fixed
    if any(it.get('id') is None for it in user.get('unclaimed_items', [])):
        user['unclaimed_items'] = unclaimed
        save_user(str(user_id), user)
    return unclaimed


def claim_item(user_id, item_id: int):
    """
    Claim ONE unclaimed item identified by its unique 'id' field.
    - Stackable items (crates, shields, teleports) merge into one inventory slot.
    - Non-stackable items require a free backpack slot.
    - Backpack items increase backpack_slots instead of entering inventory.
    Returns (True, msg) or (False, reason).
    """
    uid = str(user_id)
    user = get_user(uid)
    if not user:
        return False, "Not registered"

    unclaimed = user.get('unclaimed_items', [])
    item = next((it for it in unclaimed if it.get('id') == item_id), None)
    if not item:
        return False, "Item not found"

    item_type = item.get('type', '')
    inv = user.get('inventory', [])
    if not isinstance(inv, list):
        inv = []

    # Special handling: backpack upgrades don't enter inventory
    if 'backpack' in item_type.lower():
        old_slots = user.get('backpack_slots', 5)
        new_slots = old_slots + 15
        user['backpack_slots'] = new_slots
        user['unclaimed_items'] = [it for it in unclaimed if it.get('id') != item_id]
        save_user(uid, user)
        return True, f"Backpack upgraded! Capacity: {old_slots} → {new_slots} slots"

    # Stackable items: merge into existing slot or use one slot for all of this type
    if item_type in STACKABLE_ITEMS:
        existing = next((s for s in inv if s.get('type') == item_type or s.get('item_key') == item_type), None)
        if existing:
            # Increment quantity on the existing stack — no new slot needed
            new_qty = existing.get('quantity', existing.get('qty', 1)) + 1
            existing['quantity'] = new_qty
            existing['qty'] = new_qty
        else:
            # No existing stack — needs a free slot
            if len(inv) >= user.get('backpack_slots', 5):
                return False, "Inventory full — buy more backpack slots or use an item first"
            inv.append({
                'id':       _next_id(inv),
                'type':     item_type,
                'quantity': 1,
                'item_key': item_type,
                'qty':      1,
                'display':  item_type.replace('_', ' ').title(),
                'category': 'consumable',
                'xp_reward':        item.get('xp_reward', 0),
                'multiplier_value': item.get('multiplier_value', 0),
                'acquired': datetime.utcnow().isoformat(),
            })
        user['inventory']       = inv
        user['unclaimed_items'] = [it for it in unclaimed if it.get('id') != item_id]
        save_user(uid, user)
        return True, f"{item_type.replace('_', ' ').title()} added to stack"

    # Non-stackable: requires a free slot
    if len(inv) >= user.get('backpack_slots', 5):
        return False, "Inventory full — buy more backpack slots or use an item first"

    inv.append({
        'id':               _next_id(inv),
        'type':             item_type,
        'quantity':         1,
        'item_key':         item_type,
        'qty':              1,
        'display':          item_type.replace('_', ' ').title(),
        'category':         'consumable',
        'xp_reward':        item.get('xp_reward', 0),
        'multiplier_value': item.get('multiplier_value', 0),
        'acquired':         datetime.utcnow().isoformat(),
    })
    user['inventory']       = inv
    user['unclaimed_items'] = [it for it in unclaimed if it.get('id') != item_id]
    save_user(uid, user)
    return True, "Item claimed successfully"


def remove_unclaimed_item(user_id, item_id: int):
    user = get_user(str(user_id))
    if not user:
        return
    user['unclaimed_items'] = [it for it in user.get('unclaimed_items', []) if it.get('id') != item_id]
    save_user(str(user_id), user)


# ── Levels ─────────────────────────────────────────────────────────────────

def calculate_level(xp: int) -> int:
    return 1 + (xp // 100)


def check_level_up(user_id):
    """Return (old_level, new_level) if leveled up, else (None, None)."""
    user = get_user(str(user_id))
    if not user:
        return None, None
    old = user.get('last_level', 1)
    new = user.get('level', 1)
    if new > old:
        user['last_level'] = new
        save_user(str(user_id), user)
        return old, new
    return None, None


# ── Profile ────────────────────────────────────────────────────────────────

def get_profile(user_id) -> dict | None:
    user = get_user(str(user_id))
    if not user:
        return None
    inv      = user.get('inventory', [])
    uncl     = user.get('unclaimed_items', [])
    xp       = user.get('xp', 0)
    energy   = user.get('energy', 0)
    gold   = user.get('gold', 0)
    level    = user.get('level', 1)
    xp_prog  = xp % 100
    shielded = is_shielded(user)
    
    # Get resources and food from base_resources
    base_res = user.get('base_resources', {})
    resources_dict = base_res.get('resources', {})
    food = base_res.get('food', 0)
    
    return {
        'username':        user.get('username', 'Unknown'),
        'level':           level,
        'xp':              xp,
        'xp_progress':     xp_prog,
        'xp_needed':       100,
        'bitcoin':          user.get('bitcoin', 0),
        'all_time_points': user.get('all_time_points', 0),
        'weekly_points':   user.get('weekly_points', 0),
        'total_words':     user.get('total_words', 0),
        'sector':          user.get('sector'),
        'energy':          user.get('energy'),
        'power':           user.get('power'),
        'buildings':       user.get('buildings', {}),
        'gold':            user.get('gold'),
        'sector_display':  get_sector_display(user.get('sector')),
        'backpack_slots':  user.get('backpack_slots', 5),
        'inventory_count': len(inv),
        'unclaimed_count': len(uncl),
        'crate_count':     sum(1 for i in inv if 'crate' in i.get('type','').lower()),
        'shield_count':    sum(1 for i in inv if i.get('type','') == 'shield'),
        'shielded':        shielded,
        'shield_expires':  user.get('shield_expires'),
        'base_name':       user.get('base_name'),
        'base_resources':  resources_dict,
        'base_food':       food,
    }


# ── Sectors ────────────────────────────────────────────────────────────────

def load_sectors() -> dict:
    sectors = {}
    if not os.path.exists(SECTORS_FILE):
        return sectors
    try:
        with open(SECTORS_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except OSError:
        return sectors
    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith('SectorID'):
            continue
        parts = line.split('\t')
        if len(parts) >= 4:
            try:
                sid = int(parts[0])
                sectors[sid] = {
                    'name':        parts[3].strip(),
                    'environment': parts[1].strip() if len(parts) > 1 else '',
                    'energy':      parts[2].strip() if len(parts) > 2 else '',
                    'perks':       parts[4].strip() if len(parts) > 4 else '',
                }
            except Exception:
                pass
    return sectors


def get_sector_display(sector_id, sectors=None) -> str:
    if sector_id is None:
        return 'Not Assigned'
    if sectors is None:
        sectors = load_sectors()
    try:
        sid  = int(sector_id)
        info = sectors.get(sid)
        return f'#{sid} {info["name"]}' if info else f'Sector {sid}'
    except (TypeError, ValueError):
        return f'Sector {sector_id}'


# ── Powerful milestone items ───────────────────────────────────────────────

def award_powerful_locked_item(user_id):
    items = [
        ('legendary_artifact', '⚔️ LEGENDARY ARTIFACT', 'An ancient weapon of unimaginable power.'),
        ('mythical_crown',     '👑 MYTHICAL CROWN',      'The crown of a forgotten god.'),
        ('void_stone',         '🌑 VOID STONE',          'A stone from beyond the stars.'),
        ('eternal_flame',      '🔥 ETERNAL FLAME',       'A flame that never dies.'),
        ('celestial_key',      '🗝️ CELESTIAL KEY',       'A key to dimensions you cannot yet comprehend.'),
    ]
    item_type, display, desc = random.choice(items)
    add_unclaimed_item(user_id, f'locked_{item_type}', 1, xp_reward=0)
    return display, desc


# ── Round management (streak resets every 120s) ─────────────────────────────

def get_all_users() -> list:
    """Fetch all users from database for roundly streak reset."""
    try:
        r = supabase.table(DB_TABLE).select('*').execute()
        return r.data if r.data else []
    except Exception as e:
        print(f"[ERROR] get_all_users failed: {e}")
        return []

# ═══════════════════════════════════════════════════════════════════════════
# PASTE BLOCK 2 — Teleport grant (replaces the broken version)
# main.py imports: grant_free_teleports_to_all
# ═══════════════════════════════════════════════════════════════════════════
def get_sector_state(sector_id: int) -> dict:
    try:
        r = supabase.table("sector_state").select("*").eq(
            "sector_id", sector_id
        ).execute()
        if r.data:
            state = r.data[0]
            # Normalize JSON fields
            for field in ["occupancy", "roaming", "dominance", "active_predators",
                          "pending_notifications", "incoming_marches"]:
                state[field] = safe_json(state.get(field), default={})
            for field in ["sector_chat", "pending_ruler_alerts"]:
                state[field] = safe_json(state.get(field), default=[])
            return state
        # Return empty state if not seeded yet
        return {"sector_id": sector_id, "occupancy": {}, "roaming": {},
                "sector_chat": [], "dominance": {}, "active_predators": {}}
    except Exception as e:
        print(f"[DB ERROR] get_sector_state {sector_id}: {e}")
        return {"sector_id": sector_id, "occupancy": {}, "roaming": {},
                "sector_chat": [], "dominance": {}, "active_predators": {}}

def save_sector_state(sector_id: int, state: dict) -> None:
    try:
        state["last_updated"] = datetime.utcnow().isoformat()
        supabase.table("sector_state").upsert(
            {"sector_id": sector_id, **state}
        ).execute()
    except Exception as e:
        print(f"[DB ERROR] save_sector_state {sector_id}: {e}")

import json as _json
from datetime import datetime as _dt, timedelta as _td


# ═══════════════════════════════════════════════════════════════════════════
#  JSON SAFETY — fixes 'str object has no attribute append'
# ═══════════════════════════════════════════════════════════════════════════

def safe_json(value, default=None):
    """Parse a value that might be a JSON string or already parsed dict/list."""
    if default is None:
        default = {}
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        v = value.strip()
        if not v or v in ('null', 'None', ''):
            return default
        try:
            return _json.loads(v)
        except Exception:
            return default
    return default


def normalize_user(user: dict) -> dict:
    """Normalize all JSON fields on a user dict from Supabase."""
    if not user:
        return user

    # NOTE: inventory is a LIST not a dict — kept in list_fields
    dict_fields = [
        "military", "buildings", "building_queue",
        "researches", "research_queue", "base_resources", "traps",
        "weapons", "buffs", "banishments", "visas", "visa_applications",
        "commander_location", "current_node", "active_suit",
        "skill_points_spent", "dominance_scores",
    ]
    for field in dict_fields:
        user[field] = safe_json(user.get(field), default={})

    list_fields = [
        "inventory", "unclaimed_items", "march_queue", "eject_log",
        "teleport_history", "visa_queue",
    ]
    for field in list_fields:
        val = safe_json(user.get(field), default=[])
        user[field] = val if isinstance(val, list) else (list(val.values()) if isinstance(val, dict) else [])

    if not user.get("commander_location"):
        user["commander_location"] = {"sector_id": 1}

    base_res = user.get("base_resources", {})
    if not isinstance(base_res, dict):
        base_res = {}
    if not isinstance(base_res.get("resources"), dict):
        base_res["resources"] = {}
    user["base_resources"] = base_res

    if user.get("credits") is None:
        user["credits"] = 0

    return user


# ═══════════════════════════════════════════════════════════════════════════
#  CREDITS SYSTEM
# ═══════════════════════════════════════════════════════════════════════════

CREDITS_TO_PLAY     = 10
CREDITS_DAILY_LOGIN = 50
CREDITS_RANK_REWARDS = {
    1: 50, 2: 45, 3: 30, 4: 20, 5: 10,
    6: 5,  7: 5,  8: 5,  9: 5,  10: 5,
}

# Telegram Stars exchange rates — Gold intentionally converts at a lower
# rate than Credits, since Gold is the scarce/premium currency and should
# never feel "worth less" than Credits per Star spent.
CREDITS_PER_STAR = 30
GOLD_PER_STAR    = 10


def get_credits(user_id: str) -> int:
    user = get_user(str(user_id))
    if not user:
        return 0
    return int(user.get("credits", 0) or 0)


def add_credits(user_id: str, amount: int) -> int:
    user = get_user(str(user_id))
    if not user:
        return 0
    current = int(user.get("credits", 0) or 0)
    new_bal = current + amount
    save_user(str(user_id), {**user, "credits": new_bal})
    return new_bal


def spend_credits(user_id: str, amount: int) -> tuple:
    user = get_user(str(user_id))
    if not user:
        return False, 0
    current = int(user.get("credits", 0) or 0)
    if current < amount:
        return False, current
    new_bal = current - amount
    save_user(str(user_id), {**user, "credits": new_bal})
    return True, new_bal


def add_gold(user_id: str, amount: int) -> int:
    """Add gold to a player. Returns new balance."""
    user = get_user(str(user_id))
    if not user:
        return 0
    current = int(user.get("gold", 0) or 0)
    new_bal = current + amount
    save_user(str(user_id), {**user, "gold": new_bal})
    return new_bal


def spend_gold(user_id: str, amount: int) -> tuple:
    """Spend gold. Returns (success, new_balance). Fails if insufficient."""
    user = get_user(str(user_id))
    if not user:
        return False, 0
    current = int(user.get("gold", 0) or 0)
    if current < amount:
        return False, current
    new_bal = current - amount
    save_user(str(user_id), {**user, "gold": new_bal})
    return True, new_bal


def claim_daily_teleports(user_id: str) -> tuple:
    """
    Claim 3 free teleport charges. ADDS to existing balance — never overwrites.
    Once per UTC calendar day; if the player doesn't tap the claim button that
    day, that day's free teleports simply don't get granted — no stacking of
    missed days, but charges they already own are never touched.
    Returns (claimed: bool, message: str, new_charges: int).
    """
    user = get_user(str(user_id))
    if not user:
        return False, "❌ User not found.", 0

    today = datetime.utcnow().strftime("%Y-%m-%d")
    if user.get("teleport_daily_claimed_date") == today:
        current = int(user.get("teleport_charges", 0) or 0)
        return False, "⏳ Already claimed today — come back tomorrow!", current

    current = int(user.get("teleport_charges", 0) or 0)
    new_charges = current + 3
    save_user(str(user_id), {
        **user,
        "teleport_charges": new_charges,
        "teleport_daily_claimed_date": today,
    })
    return True, f"🌀 +3 Teleport Charges claimed! Total: {new_charges}", new_charges


def claim_daily_login_credits(user_id: str) -> tuple:
    """
    Claim daily login credits with a 7-day reward streak.
    Returns (awarded: bool, amount: int, new_balance: int, current_streak: int).
    Can only be claimed once per UTC day.
    """
    from datetime import datetime, timedelta, timezone
    from supabase_db import get_user as _get_user, save_user as _save_user
    
    user = _get_user(str(user_id))
    if not user:
        return False, 0, 0, 0

    # Define the 7-day credit reward matrix
    STREAK_REWARDS = {1: 50, 2: 60, 3: 75, 4: 100, 5: 125, 6: 150, 7: 200}

    # Use modern timezone-aware UTC dates to clear your terminal warnings
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    last_claim = user.get("last_credit_login", "")
    current_credits = int(user.get("credits", 0) or 0)
    login_streak = int(user.get("login_streak", 0) or 0)

    # 1. Block if already claimed today
    if last_claim == today:
        return False, 0, current_credits, login_streak

    # 2. Calculate the streak progress
    if last_claim == yesterday:
        # Progress streak, reset back to 1 if they completed day 7 yesterday
        if login_streak >= 7:
            new_streak = 1
        else:
            new_streak = login_streak + 1
    else:
        # Missed a day or brand new player -> Start at Day 1
        new_streak = 1

    # 3. Determine reward values
    amount = STREAK_REWARDS.get(new_streak, 50)
    new_bal = current_credits + amount

    # 4. Save updated payload back to Supabase
    updated_fields = {
        **user,
        "credits": new_bal,
        "last_credit_login": today,
        "login_streak": new_streak
    }

    # Optional: If Day 7, add your bronze crate item here!
    if new_streak == 7:
        from supabase_db import add_inventory_item
        user = add_inventory_item(user, "crt_brz", 1, "🥉 Bronze Crate", category="consumable")

    updated_fields = {
        **user,
        "credits": new_bal,
        "last_credit_login": today,
        "login_streak": new_streak
    }

    _save_user(str(user_id), updated_fields)
    
    return True, amount, new_bal, new_streak


def award_scoreboard_credits(user_id: str, rank: int) -> int:
    amount = CREDITS_RANK_REWARDS.get(rank, 0)
    if amount > 0:
        add_credits(str(user_id), amount)
    return amount


# ═══════════════════════════════════════════════════════════════════════════
#  TELEPORT GRANT
# ═══════════════════════════════════════════════════════════════════════════

def grant_free_teleports_to_all() -> int:
    """
    Grant 3 free teleport charges to all players who haven't claimed today.
    Uses teleport_charges integer column — never touches inventory list.
    Returns count granted. Safe to call synchronously at startup.
    """
    today   = _dt.utcnow().strftime("%Y-%m-%d")
    granted = 0

    try:
        result = supabase.table(DB_TABLE).select(
            "user_id, teleport_charges, teleport_daily_claimed_date"
        ).execute()

        for row in (result.data or []):
            try:
                uid = row.get("user_id")
                if not uid:
                    continue
                if row.get("teleport_daily_claimed_date") == today:
                    continue
                current = int(row.get("teleport_charges") or 0)
                supabase.table(DB_TABLE).update({
                    "teleport_charges":            current + 3,
                    "teleport_daily_claimed_date": today,
                }).eq("user_id", uid).execute()
                granted += 1
            except Exception as e:
                print(f"[WARN] teleport grant {row.get('user_id','?')}: {e}")

    except Exception as e:
        print(f"[ERROR] grant_free_teleports_to_all: {e}")

    return granted


# ═══════════════════════════════════════════════════════════════════════════
#  SHIELD FUNCTIONS
#  You said you don't want to give free shields automatically.
#  grant_free_shields_to_all is a no-op stub — it's imported by main.py
#  but does nothing. The other functions are real.
# ═══════════════════════════════════════════════════════════════════════════

def grant_free_shields_to_all() -> int:
    """
    Stub — free shields disabled by design.
    Players must purchase shields. This exists only so main.py import works.
    Returns 0.
    """
    print("[SHIELDS] Auto-grant disabled — players purchase shields.")
    return 0


def give_automatic_shield(user_id: str, duration_hours: int = 8) -> bool:
    """
    Give a timed shield to a specific player (e.g. after base siege, new player).
    Returns True if applied.
    """
    try:
        user = get_user(str(user_id))
        if not user:
            return False
        expires = (_dt.utcnow() + _td(hours=duration_hours)).isoformat()
        save_user(str(user_id), {
            **user,
            "base_shielded":    True,
            "shield_expires_at": expires,
        })
        return True
    except Exception as e:
        print(f"[SHIELD] give_automatic_shield error: {e}")
        return False


def deactivate_shield(user_id: str) -> tuple:
    """
    Manually deactivate a player's shield.
    Returns (success: bool, message: str)
    """
    try:
        user = get_user(str(user_id))
        if not user:
            return False, "Player not found"
        if not user.get("base_shielded"):
            return False, "No active shield to deactivate"
        save_user(str(user_id), {
            **user,
            "base_shielded":    False,
            "shield_expires_at": None,
        })
        return True, "🔓 Shield deactivated"
    except Exception as e:
        return False, f"Error: {e}"


def disrupt_shield(user_id: str, drain_hours: int = 2) -> tuple:
    """
    Attacker disrupts a defender's shield — reduces duration by drain_hours.
    Called when an attack on a shielded base lands.
    Returns (disrupted: bool, hours_remaining: float)
    """
    try:
        user = get_user(str(user_id))
        if not user:
            return False, 0

        if not user.get("base_shielded"):
            return False, 0

        exp_str = user.get("shield_expires_at")
        if not exp_str:
            return False, 0

        try:
            exp = _dt.fromisoformat(exp_str)
        except Exception:
            return False, 0

        now         = _dt.utcnow()
        if now >= exp:
            # Already expired
            save_user(str(user_id), {**user, "base_shielded": False, "shield_expires_at": None})
            return False, 0

        new_exp     = exp - _td(hours=drain_hours)
        hours_left  = max(0, (new_exp - now).total_seconds() / 3600)

        if new_exp <= now:
            # Shield fully drained
            save_user(str(user_id), {
                **user,
                "base_shielded":    False,
                "shield_expires_at": None,
                "shield_just_expired": True,
            })
            return True, 0
        else:
            save_user(str(user_id), {
                **user,
                "shield_expires_at": new_exp.isoformat(),
            })
            return True, round(hours_left, 1)

    except Exception as e:
        print(f"[SHIELD] disrupt_shield error: {e}")
        return False, 0


def restore_shield_after_attack(user_id: str) -> bool:
    """
    Called if an attack was defended successfully — attacker's disruption attempt failed.
    No change to shield needed, but logs the event.
    Returns True always.
    """
    print(f"[SHIELD] Attack on {user_id} defended — shield intact")
    return True


# ═══════════════════════════════════════════════════════════════════════════
#  MISC STUBS / WRAPPERS
#  These exist so main.py imports work. If you already have these
#  functions in supabase_db.py, the later definition wins — safe to paste.
# ═══════════════════════════════════════════════════════════════════════════

def add_randomized_gift(user_id: str) -> dict:
    """
    Award a random gift item to a player.
    Returns dict describing what was given, or {} if nothing.
    Extend this to add real gift logic when ready.
    """
    import random
    gifts = [
        {"type": "credits", "amount": 25,  "display": "+25 credits"},
        {"type": "credits", "amount": 50,  "display": "+50 credits"},
        {"type": "resource","resource": "iron",   "amount": 20, "display": "+20 iron"},
        {"type": "resource","resource": "bronze", "amount": 30, "display": "+30 bronze"},
        {"type": "teleport","amount": 1,   "display": "+1 teleport charge"},
    ]
    gift = random.choice(gifts)

    try:
        user = get_user(str(user_id))
        if not user:
            return {}

        if gift["type"] == "credits":
            add_credits(str(user_id), gift["amount"])

        elif gift["type"] == "resource":
            base_res = safe_json(user.get("base_resources"), default={})
            resources = safe_json(base_res.get("resources"), default={})
            resources[gift["resource"]] = resources.get(gift["resource"], 0) + gift["amount"]
            base_res["resources"] = resources
            save_user(str(user_id), {**user, "base_resources": base_res})

        elif gift["type"] == "teleport":
            current = int(user.get("teleport_charges") or 0)
            save_user(str(user_id), {**user, "teleport_charges": current + 1})

    except Exception as e:
        print(f"[GIFT] add_randomized_gift error: {e}")
        return {}

    return gift


def reset_all_streaks() -> None:
    """
    Reset all player current streaks (called at round end).
    Only resets current_streak, not all_time records.
    """
    try:
        # Batch update — set current_streak to 0 for all players
        # We do this via base_resources JSONB update
        result = supabase.table(DB_TABLE).select(
            "user_id, base_resources"
        ).execute()

        for row in (result.data or []):
            try:
                uid      = row.get("user_id")
                base_res = safe_json(row.get("base_resources"), default={})
                if base_res.get("current_streak", 0) > 0:
                    base_res["current_streak"] = 0
                    supabase.table(DB_TABLE).update({
                        "base_resources": base_res
                    }).eq("user_id", uid).execute()
            except Exception:
                pass

    except Exception as e:
        print(f"[STREAKS] reset_all_streaks error: {e}")

def sync_player_passive_energy(user: dict) -> dict:
    """
    Calculates passive energy recovery based on elapsed time.
    Regenerates up to a hard ceiling of 1000 energy in exactly 1 hour.
    """
    max_energy = 1000
    reg_rate_per_sec = 1000 / 3600  # 0.2778 per second
    
    current_energy = user.get("energy", 0)
    
    # If already at max capacity, update the tracking timestamp and return
    if current_energy >= max_energy:
        user["energy"] = max_energy
        user["energy_last_updated_at"] = datetime.utcnow().isoformat()
        return user

    last_update_str = user.get("energy_last_updated_at")
    if not last_update_str:
        # Fallback if the field doesn't exist yet
        user["energy_last_updated_at"] = datetime.utcnow().isoformat()
        return user

    try:
        last_update = datetime.fromisoformat(last_update_str)
        elapsed_seconds = (datetime.utcnow() - last_update).total_seconds()
        
        if elapsed_seconds > 0:
            # Calculate gained energy
            gained = elapsed_seconds * reg_rate_per_sec
            new_energy = min(max_energy, current_energy + gained)
            
            user["energy"] = int(new_energy)
            user["energy_last_updated_at"] = datetime.utcnow().isoformat()
    except Exception:
        pass

    return user

def activate_energy_cell_from_backpack(user_id: str, item_key: str) -> tuple[bool, str]:
    """
    Consumes an energy item from the player's backpack.
    Restricts total energy from exceeding the hard ceiling cap of 1000.
    """
    user = get_user(user_id)
    if not user:
        return False, "❌ User profile not found."

    # Force a passive regeneration sync first so their energy is up-to-date
    user = sync_player_passive_energy(user)

    current_energy = user.get("energy", 0)
    max_energy = 1000

    if current_energy >= max_energy:
        return False, f"⚠️ Your Energy Core is already completely filled! ({current_energy}/{max_energy})"

    # Fetch configuration properties from catalog
    from store_system import STORE_ITEMS
    item_data = STORE_ITEMS.get(item_key)
    if not item_data:
        return False, "❌ Item data configurations not found."

    # Determine how much energy this specific cell item restores (default to 250)
    energy_to_restore = item_data.get("energy", 250)

    # Apply boost capped at 1000 max
    user["energy"] = min(max_energy, current_energy + energy_to_restore)
    
    # Update timestamp so passive generation adjusts to the new value properly
    user["energy_last_updated_at"] = datetime.utcnow().isoformat()

    # Deduct 1 item from inventory backpack
    user = remove_inventory_item(user, item_key)

    save_user(user_id, user)
    return True, f"⚡ Charged up! Core energy updated to {user['energy']}/{max_energy}."


def use_energy(user_id: str, amount: int) -> tuple[bool, str, int]:
    """
    Spend energy on an action. NEVER refuses — players can always use energy,
    even if it drives their balance to 0 or negative, so they can waste it
    strategically or take a risk on a low tank.
    Returns (success: bool, message: str, new_energy: int).
    `success` is always True here; kept in the return signature so callers
    that check `ok, msg = use_energy(...)` style still work without changes.
    """
    user = get_user(user_id)
    if not user:
        return False, "❌ User profile not found.", 0

    # Sync passive regen first so the deduction starts from an accurate value
    user = sync_player_passive_energy(user)

    current_energy = user.get("energy", 0)
    new_energy = current_energy - amount   # intentionally allowed to go negative

    user["energy"] = new_energy
    user["energy_last_updated_at"] = datetime.utcnow().isoformat()
    save_user(user_id, user)

    if new_energy < 0:
        return True, f"⚡ Used {amount} energy. Core is now overdrawn: {new_energy}/1000.", new_energy
    return True, f"⚡ Used {amount} energy. Remaining: {new_energy}/1000.", new_energy