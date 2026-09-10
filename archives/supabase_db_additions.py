# -*- coding: utf-8 -*-
"""
supabase_db_additions_v2.py
===========================
PASTE THE CONTENTS OF THIS FILE AT THE BOTTOM OF supabase_db.py

Adds every function that main.py imports from supabase_db
but that doesn't currently exist there. Safe to paste even if
some already exist — Python will just use the last definition.

Functions added:
  Credits:      get_credits, add_credits, spend_credits,
                claim_daily_login_credits, award_scoreboard_credits,
                CREDITS_TO_PLAY, CREDITS_RANK_REWARDS, CREDITS_DAILY_LOGIN
  Teleports:    grant_free_teleports_to_all
  Shields:      grant_free_shields_to_all, give_automatic_shield,
                deactivate_shield, disrupt_shield, restore_shield_after_attack
  Misc:         add_randomized_gift, reset_all_streaks (stubs if not present)
  JSON safety:  safe_json, normalize_user
"""

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

    dict_fields = [
        "inventory", "military", "buildings", "building_queue",
        "researches", "research_queue", "base_resources", "traps",
        "weapons", "buffs", "banishments", "visas", "visa_applications",
        "commander_location", "current_node", "active_suit",
        "skill_points_spent", "dominance_scores",
    ]
    for field in dict_fields:
        user[field] = safe_json(user.get(field), default={})

    list_fields = [
        "unclaimed_items", "march_queue", "eject_log",
        "teleport_history", "visa_queue",
    ]
    for field in list_fields:
        user[field] = safe_json(user.get(field), default=[])

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


def claim_daily_login_credits(user_id: str) -> tuple:
    """Returns (awarded: bool, amount: int, new_balance: int)."""
    user = get_user(str(user_id))
    if not user:
        return False, 0, 0

    today      = _dt.utcnow().strftime("%Y-%m-%d")
    last_claim = user.get("last_daily_credit_claim", "")

    if last_claim == today:
        return False, 0, int(user.get("credits", 0) or 0)

    amount  = CREDITS_DAILY_LOGIN
    current = int(user.get("credits", 0) or 0)
    new_bal = current + amount

    save_user(str(user_id), {
        **user,
        "credits":                 new_bal,
        "last_daily_credit_claim": today,
    })
    return True, amount, new_bal


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
