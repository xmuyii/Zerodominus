#!/usr/bin/env python3
"""Quick test of gspread sync without SSL issues"""
import sys
sys.path.insert(0, '/c/Users/xmuyii/Documents/The64')

from sync_to_sheets import validate_config, get_weekly_leaderboard

validate_config()
print("\n📊 Fetching leaderboard from Supabase...")
leaderboard = get_weekly_leaderboard()

if leaderboard:
    print(f"✅ Found {len(leaderboard)} players\n   Top 5:")
    for p in leaderboard[:5]:
        print(f"      #{p['rank']} {p['username']:20} {p['points']:>6} pts")
else:
    print("⚠️  No leaderboard data found")

print("\n✅ Configuration and data fetch successful!")
print("   Next: Run 'python sync_to_sheets.py' to sync to Google Sheets")
