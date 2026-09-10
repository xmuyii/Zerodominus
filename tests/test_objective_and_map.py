import os

os.environ.setdefault("API_TOKEN", "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789")

from main import get_hud_objective, get_objective_action_buttons
from base_layout import render_tactical_map, get_default_base_layout


def test_objective_action_buttons_prioritize_claims():
    buttons = get_objective_action_buttons("🎁 Claim 2 rewards now.")
    flat = [button.callback_data for row in buttons for button in row]
    assert "menu_claims" in flat


def test_tactical_map_renders_a_readable_grid():
    map_text = render_tactical_map(get_default_base_layout())
    assert "TACTICAL BASE PLOT" in map_text
    assert "HQ Core" in map_text
    assert "Front Gate" in map_text
    assert "Shelter" in map_text
    assert "NW" in map_text and "C" in map_text and "SE" in map_text
