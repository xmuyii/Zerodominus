# Map-Backend Integration Plan

## Objective
Synchronize the isometric map (LandScene) with backend systems to enable:
- **Persistent base placement** (saved to database)
- **Real-time updates** for bases, troops, and attacks
- **Troop deployment visualization** on the map
- **Alliance territory display**
- **Telegram + Web data sync**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (index.html - Phaser)                             │
│  ├─ WorldScene (God View - Sector Map)                      │
│  ├─ LandScene (Isometric - Base Placement & Troops)         │
│  └─ WebSocket Client (Real-time sync)                       │
└──────────────────┬──────────────────────────────────────────┘
                   │
      ┌────────────┼────────────┐
      │            │            │
      ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ map_api  │ │ api_web  │ │ NEW: ws  │
│  (REST)  │ │ (REST)   │ │(WebSocket)
└────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │            │
     └────────────┼────────────┘
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
   database.py      supabase_db.py
   (Local JSON)     (Backend DB)
   
   alliance_system.py
   attack_system.py
   (Business Logic)
```

---

## Phase 1: Database & API Extensions

### 1.1 Extend Data Model (`database.py`)

**New user fields to track map state:**
- `placed_bases`: List of bases placed in sectors
  ```
  {
    "s{sector_num}": {
      "id": "base_xxx",
      "name": "Base Name",
      "sector": 1,
      "level": 1,
      "defense": 80,
      "troops": {"Infantry": 50, "Archers": 30, ...},
      "resources": {"wood": 150, "iron": 80, ...},
      "owner_id": "user_123",
      "created_at": "2024-01-15T10:30:00Z",
      "last_updated": "2024-01-15T10:30:00Z"
    }
  }
  ```
- `active_marches`: List of troop movements in progress
  ```
  {
    "march_xxx": {
      "id": "march_xxx",
      "from_sector": 1,
      "to_sector": 5,
      "troops": {"Infantry": 100},
      "started_at": "2024-01-15T10:00:00Z",
      "eta": "2024-01-15T10:45:00Z",
      "status": "traveling"  // or "arrived", "canceled"
    }
  }
  ```

**New functions:**
- `save_placed_base(user_id, sector, base_data)`
- `get_placed_bases(user_id)`
- `get_bases_in_sector(sector_num)`
- `add_march(user_id, march_data)`
- `get_active_marches(user_id)`
- `complete_march(march_id)`

---

### 1.2 Extend Map API (`map_api.py`)

**New endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/bases/place` | Save a newly placed base |
| GET | `/api/bases/user/{user_id}` | Get all player's placed bases |
| GET | `/api/bases/sector/{sector}` | Get all bases in a sector (for display) |
| POST | `/api/marches` | Start a troop movement |
| GET | `/api/marches/active` | Get player's active marches |
| PUT | `/api/marches/{march_id}` | Update march status |
| GET | `/api/sector/{sector}/full` | Full sector data (bases + resources) |
| GET | `/api/world/live` | Real-time world state (all bases, marches) |

**Example POST `/api/bases/place` request/response:**
```json
// Request
{
  "user_id": "user_123",
  "sector": 5,
  "base_name": "Iron Fortress",
  "iso_x": 150,
  "iso_y": 200
}

// Response
{
  "success": true,
  "base": {
    "id": "base_xxx",
    "name": "Iron Fortress",
    "sector": 5,
    "level": 1,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## Phase 2: Frontend Integration (index.html Updates)

### 2.1 Player Badge Sync

**Update `updatePlayerBadge()` to fetch from backend:**
```javascript
async function updatePlayerBadge() {
  const res = await fetch(`/api/player/${G.userId}`);
  const p = await res.json();
  G.playerData = p;
  // Update DOM...
}
```

### 2.2 LandScene - Base Placement Integration

**Modify `LandScene.placeBaseAt()` to persist:**
1. Call `POST /api/bases/place` with base data
2. On success: save locally + update scene
3. On error: show toast, don't mark as placed

**Update `confirmDeploy()` to create march:**
1. Call `POST /api/marches` with troop counts
2. Return march ID and ETA
3. Add visual march animation to map

### 2.3 WorldScene - Display Remote Bases

**In `WorldScene.create()`, fetch bases before rendering:**
```javascript
async function _buildWorld() {
  const res = await fetch('/api/all_bases');
  const { bases } = await res.json();
  // Render base icons for each sector based on fetched data
}
```

### 2.4 LandScene - Display All Bases in Sector

**Before rendering terrain, load sector bases:**
```javascript
async create(data) {
  const sectorBases = await fetch(`/api/bases/sector/${data.sectorNum}`).then(r => r.json());
  // Render all bases from API (not mock data)
  this._spawnBases(sectorBases);
}
```

---

## Phase 3: Real-Time Sync (WebSocket)

### 3.1 New WebSocket Server (`ws_server.py`)

**Purpose:** Broadcast map updates to all connected clients

**Events:**
- `base_placed` → Notify all players of new base
- `march_started` → Show troop movement to attackers/defenders
- `march_arrived` → Trigger base attack visualization
- `base_destroyed` → Remove base from map
- `resources_updated` → Update base resource display
- `alliance_event` → Alliance members gain/lose territory

**Implementation:**
- Use `websockets` library
- Store connected clients by sector (optimize broadcasting)
- Sync with Telegram bot via API callbacks

### 3.2 Frontend WebSocket Client

**In `index.html`, add WS connection:**
```javascript
const ws = new WebSocket(`ws://localhost:8002?user_id=${G.userId}`);

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  if (msg.type === 'base_placed' && G.view === 'god') {
    // Add base to world scene
    worldScene._addRemoteBase(msg.base);
  }
  
  if (msg.type === 'march_arrived' && G.activeLandSector === msg.to_sector) {
    // Trigger attack animation in land scene
    landScene.showIncomingAttack(msg.march);
  }
  
  if (msg.type === 'resources_updated' && msg.sector === G.activeLandSector) {
    landScene._updateBaseResources(msg.base_id, msg.resources);
  }
};
```

---

## Phase 4: Integration with Existing Systems

### 4.1 Alliance System Integration

**In `alliance_system.py`, add map events:**
- When base is placed → Check if sector is allied territory
- Broadcast `alliance_base_placed` event to teammates
- Update alliance treasury when resources are shared

**New function: `get_alliance_territory(alliance_id)`**
- Returns all sectors with alliance member bases
- Used for alliance view mode on map

### 4.2 Attack System Integration

**In `attack_system.py`:**
- When `calculate_battle_outcome()` completes, trigger WS event
- Broadcast battle animation to attacker + defender
- Update defender's base defense/troops

**New function: `format_attack_for_map(attacker, defender, result)`**
- Returns animation data (source → target coordinates, damage, casualties)
- Frontend plays cinematic battle sequence

### 4.3 Telegram Bot Sync

**In `main.py`, add map callbacks:**
- `!place_base` → POST `/api/bases/place` (if web map used)
- Raid results → Emit `battle_complete` WS event
- Base upgrades → Emit `base_upgraded` WS event
- This ensures bot actions sync to web map in real-time

---

## Phase 5: Troop Visualization

### 5.1 WorldScene - Troop Count Display

**Extend `_buildWorld()` to show unit counts:**
- Fetch active marches: `GET /api/marches/active`
- For each march, draw animated unit group moving from sector → target
- Show ETA and troop count on hover

### 5.2 LandScene - Marching Troops Animation

**Extend `showMarch(count)` to be data-driven:**
```javascript
async showMarch(march_id) {
  const march = await fetch(`/api/marches/${march_id}`).then(r => r.json());
  
  const units = [];
  for (let i = 0; i < march.troops.Infantry; i++) {
    const unit = this.add.circle(sx, sy, 3, 0x44aaff);
    units.push(unit);
  }
  
  // Animate units from origin → destination
  this.tweens.add({
    targets: units,
    x: tx,
    y: ty,
    duration: march.eta_ms,
    onComplete: () => {
      // Army arrived – trigger defender notification
      fetch(`PUT /api/marches/${march_id}`, { status: 'arrived' });
    }
  });
}
```

### 5.3 Battle Visualization

**When attack lands, show cinematic sequence:**
1. Troops pour into base (unit animations)
2. Explosions/damage (visual effects)
3. Result overlay (victory/defeat banner)
4. Resources flow to winner

---

## Implementation Checklist

### Step 1: Database & API (3 tasks)
- [ ] Extend `database.py`: Add `placed_bases` and `active_marches` fields + helper functions
- [ ] Extend `map_api.py`: Add 8 new endpoints for base/march CRUD
- [ ] Test endpoints with Postman/curl

### Step 2: Frontend Integration (4 tasks)
- [ ] Update `updatePlayerBadge()` to fetch from `/api/player/{user_id}`
- [ ] Modify `LandScene.placeBaseAt()` to POST to `/api/bases/place`
- [ ] Modify `confirmDeploy()` to POST to `/api/marches`
- [ ] Update `_buildWorld()` to fetch and render real bases from `/api/all_bases`

### Step 3: Real-Time Sync (2 tasks)
- [ ] Create `ws_server.py` with WebSocket handler + event broadcaster
- [ ] Add WS client to `index.html` with message handlers

### Step 4: System Integration (3 tasks)
- [ ] Update `alliance_system.py`: Add `get_alliance_territory()` and emit WS events
- [ ] Update `attack_system.py`: Emit battle events to WS + update base state
- [ ] Update `main.py`: Telegram commands trigger map API calls

### Step 5: Visualization (2 tasks)
- [ ] Enhance `WorldScene` to show active marches
- [ ] Enhance `LandScene` with battle animations + troop visuals

---

## Verification & DoD

| Task | Verification |
|------|--------------|
| Base placement persists | Place base → Refresh page → Base still visible |
| Bases visible to others | Player A places base → Player B sees it (god view + sector view) |
| Troop deployment works | Deploy troops → March appears on map with ETA |
| Real-time updates | Player A raids Player B → Instant notification + damage display |
| Alliance integration | Bases in alliance sectors show alliance color/badge |
| Telegram sync | Raid via bot → Appears on web map (and vice versa) |
| No data loss | Server restart → All bases/marches persist in database |

---

## Dependencies & Constraints

- **Frontend delay:** Frontend must wait for API responses (add loading states)
- **Network resilience:** Use exponential backoff for failed API calls
- **Database consistency:** Ensure placed_bases + active_marches are atomic updates
- **WebSocket fallback:** If WS fails, frontend falls back to polling `/api/world/live` every 5s
- **Mobile friendly:** Tested on Telegram mini-app viewport (keep animations smooth)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Double-base placement race condition | Add server-side uniqueness check per sector per user |
| WebSocket connection drops | Auto-reconnect + local queue of pending actions |
| Stale data in god view | Periodic refresh via `/api/all_bases` (every 30s) |
| March ETA calculation conflicts | Use server timestamp as source of truth |
| Alliance base spam | Limit bases per alliance per sector (e.g., max 3) |