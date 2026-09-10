"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const core_1 = require("@colyseus/core");
const ws_transport_1 = require("@colyseus/ws-transport");
const http_1 = require("http");
const FusionArena_1 = require("./rooms/FusionArena");
const port = Number(process.env.PORT || 2567);
const app = (0, express_1.default)();
app.use(express_1.default.json());
const httpServer = (0, http_1.createServer)(app);
const gameServer = new core_1.Server({
    transport: new ws_transport_1.WebSocketTransport({
        server: httpServer,
        pingInterval: 3000,
    })
});
// Log WebSocket transport events
gameServer.transport?.simulateLatency(0);
console.log(`🔌 [WebSocket] Transport initialized`);
console.log(`🔌 [WebSocket] Listening for connections on ws://localhost:${port}`);
gameServer.define("fusion_arena", FusionArena_1.FusionArena, {
// FIX: Use joinOrCreate to match players by room name
// All joinOrCreate requests go to rooms named "fusion_arena"
});
// Manual matchmaker endpoint — replaces gameServer.attach
app.post("/matchmake/:method/:roomName", async (req, res) => {
    const { method, roomName } = req.params;
    console.log(`📋 [Matchmaker] ${method.toUpperCase()} on "${roomName}"`, req.body);
    try {
        let result;
        if (method === "joinOrCreate") {
            // Use built-in joinOrCreate which handles room matching automatically
            // It will find existing rooms with this name and join them if not full
            // Otherwise it creates a new room
            console.log(`🔍 [Matchmaker] Using built-in joinOrCreate logic...`);
            result = await core_1.matchMaker.joinOrCreate(roomName, req.body);
        }
        else {
            // Fallback for other methods
            result = await core_1.matchMaker[method](roomName, req.body);
        }
        console.log(`✅ [Matchmaker] Success! Room: ${result.roomId} | Session: ${result.sessionId}`);
        res.json(result);
    }
    catch (e) {
        console.error(`❌ [Matchmaker] Error on ${method}: ${e.message}`);
        console.error(`❌ [Stack] ${e.stack}`);
        res.status(400).json({ error: e.message });
    }
});
app.get("/health", async (req, res) => {
    try {
        const rooms = await core_1.matchMaker.query({ name: "fusion_arena" });
        res.json({ status: "ok", active_rooms: rooms.length });
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
app.get("/rooms", async (req, res) => {
    try {
        const rooms = await core_1.matchMaker.query({ name: "fusion_arena" });
        console.log(`📊 [Rooms] Active: ${rooms.length}`);
        rooms.forEach((room, i) => {
            console.log(`   [${i}] ${room.roomId} - ${room.clients} / ${room.maxClients} players`);
        });
        res.json(rooms.map((room) => ({
            roomId: room.roomId,
            name: "fusion_arena",
            clients: room.clients,
            maxClients: room.maxClients
        })));
    }
    catch (error) {
        console.error("❌ [Rooms] Query error:", error.message);
        res.status(500).json({ error: error.message });
    }
});
httpServer.listen(port, () => {
    console.log(`\n=================================================`);
    console.log(`⚔️ FUSION COMBAT BRAIN ENGINE ONLINE ON PORT ${port} ⚔️`);
    console.log(`=================================================\n`);
});
