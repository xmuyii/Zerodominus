# Multiplayer Connection Debug Guide

## What Was Fixed

1. **Matchmaker Logic**: Implemented custom room matching that explicitly queries for existing rooms and joins them before creating new ones
2. **Room Naming**: Set `this.roomName = "fusion_arena"` so the matchmaker can properly query and find rooms
3. **Enhanced Logging**: Added detailed logs to track room creation, player joins, and matchmaker decisions

## How to Test

### 1. Rebuild the Server
```bash
cd .worktrees/camera/fusion-server
npm run build
npm start
```

You should see:
```
⚔️ FUSION COMBAT BRAIN ENGINE ONLINE ON PORT 2567 ⚔️
```

### 2. Run First Godot Instance
In one terminal/window, run the first Godot export and join with username `Player1`.

Look for these logs in the server:
```
📋 [Matchmaker] JOINORCREATE on "fusion_arena"
📊 [Matchmaker] Found 0 existing rooms
🆕 [Matchmaker] Creating new room (no available slots)
✅ [Matchmaker] Success! Room: juyeE21C7 | Session: C1KYuRZhy
🎮 New FusionArena room created
👤 Player1 joined
```

### 3. Run Second Godot Instance  
In another terminal/window, run the second Godot export and join with username `Player2`.

Look for these logs in the server:
```
📋 [Matchmaker] JOINORCREATE on "fusion_arena"
📊 [Matchmaker] Found 1 existing rooms
   [0] juyeE21C7 - 1/8 players
✅ [Matchmaker] Joining existing room: juyeE21C7
✅ [Matchmaker] Success! Room: juyeE21C7 | Session: <different_session>
👤 Player2 joined (2 players)
⚔️ GAME STARTED!
```

### 4. Troubleshooting

If you still see multiple rooms created:
- Check that both instances are connecting to the same server (`localhost:2567`)
- Verify the room name is being set (look for `Room Name (after): fusion_arena`)
- Check the `/rooms` endpoint: `curl http://localhost:2567/rooms`

## Key Changes Made

### server/index.ts
- Custom `joinOrCreate` logic that queries existing rooms first
- Uses `matchMaker.reserveSeat()` to join existing rooms
- Falls back to `matchMaker.create()` only if no rooms available

### rooms/FusionArena.ts
- Set `this.roomName = "fusion_arena"` in onCreate
- Added detailed logging of room and player state
- Added 5-second interval logging for room status

### addons/colyseus/Client.gd
- Enhanced error reporting for HTTP and WebSocket failures
- Added null socket checks and reinitialization
- Better debug output for connection attempts
