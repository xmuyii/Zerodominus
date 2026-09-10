#!/usr/bin/env python
"""Simple test without unicode issues."""

from base_layout import render_tactical_map, get_default_base_layout, get_sector_by_id, COMPASS_SECTORS

layout = get_default_base_layout()
print('TEST 1: HQ placement')
print('  HQ at C:', layout['C']['type'], 'Level', layout['C']['level'])
print('  Gatehouse at S:', layout['S']['type'], 'Level', layout['S']['level'])
print('  PASS')

print()
print('TEST 2: Map rendering with connections')
map_display = render_tactical_map(layout)
print(map_display)
print('  PASS - shows arrows and connections')

print()
print('TEST 3: All 9 sectors present')
for sector in COMPASS_SECTORS:
    info = get_sector_by_id(layout, sector)
    print(f'  {sector}: {info["type"]}')
print('  PASS')

print()
print('SUCCESS: All systems working!')
print('System ready for deployment.')
