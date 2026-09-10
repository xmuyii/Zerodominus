"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const colyseus_1 = require("colyseus");
const ws_1 = require("@colyseus/transport/ws");
const FusionArena_1 = require("./rooms/FusionArena");
const app = (0, express_1.default)();
const gameServer = new colyseus_1.Server({
    transport: new ws_1.WebSocketTransport({
        server: app,
        pingInterval: 3000
    })
});
// Register room
gameServer.define("fusion_arena", FusionArena_1.FusionArena);
// Health check endpoint
app.get("/health", (req, res) => {
    res.json({ status: "ok", rooms: gameServer.rooms.length });
});
// List available rooms
app.get("/rooms", (req, res) => {
    const rooms = gameServer.rooms.map(room => ({
        roomId: room.roomId,
        name: room.name,
        clients: room.clients.length,
        maxClients: room.maxClients
    }));
    res.json(rooms);
});
const PORT = process.env.PORT || 3000;
gameServer.listen(PORT);
console.log(`🎮 Colyseus server running on ws://localhost:${PORT}`);
