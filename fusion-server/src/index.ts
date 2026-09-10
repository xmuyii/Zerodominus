import express from "express";
import { createServer } from "http";
import { WebSocketServer, WebSocket } from "ws";
import { Matchmaker } from "./matchmaker";

const port = Number(process.env.PORT || 2567);
const app = express();
app.use(express.json());

const httpServer = createServer(app);
const wss = new WebSocketServer({ noServer: true });
const matchmaker = new Matchmaker();

// ─────────────────────────────────────────────────────
// HTTP ROUTES
// ─────────────────────────────────────────────────────

// Matchmaking — reserve a seat
app.post("/matchmake/joinOrCreate/fusion_arena", (req, res) => {
    const username = (req.body?.username || "").toString().trim();
    if (!username) {
        res.status(400).json({ error: "Username required" });
        return;
    }

    try {
        const result = matchmaker.joinOrCreate(username);
        console.log(`✅ Seat reserved: ${JSON.stringify(result)}`);
        res.json(result);
    } catch (err: any) {
        console.error("❌ Matchmaker error:", err.message);
        res.status(500).json({ error: err.message });
    }
});

// Room list
app.get("/rooms", (req, res) => {
    res.json(matchmaker.getRoomList());
});

// Health check
app.get("/health", (req, res) => {
    res.json({ status: "ok", rooms: matchmaker.getRoomList().length });
});

// ─────────────────────────────────────────────────────
// WEBSOCKET UPGRADE
// ─────────────────────────────────────────────────────

httpServer.on("upgrade", (req, socket, head) => {
    console.log(`🔌 WS upgrade: ${req.url}`);

    // Parse sessionId from URL: /SESSION_ID or /?sessionId=SESSION_ID
    const url = new URL(req.url || "/", `http://localhost:${port}`);
    const sessionId =
        url.searchParams.get("sessionId") ||
        url.pathname.replace(/^\//, "");

    if (!sessionId) {
        console.warn("⚠️  WS upgrade rejected: no sessionId");
        socket.destroy();
        return;
    }

    wss.handleUpgrade(req, socket, head, (ws) => {
        wss.emit("connection", ws, req, sessionId);
    });
});

// ─────────────────────────────────────────────────────
// WEBSOCKET CONNECTIONS
// ─────────────────────────────────────────────────────

wss.on("connection", (ws: WebSocket, req: any, sessionId: string) => {
    console.log(`🟢 WS connected: session=${sessionId}`);

    const joined = matchmaker.completeJoin(sessionId, ws);
    if (!joined) return;

    ws.on("message", (data) => {
        try {
            const message = JSON.parse(data.toString());
            matchmaker.handleMessage(sessionId, message);
        } catch (err) {
            console.warn("⚠️  Bad message format:", data.toString());
        }
    });

    ws.on("close", (code, reason) => {
        console.log(`🔴 WS closed: session=${sessionId} code=${code}`);
    });

    ws.on("error", (err) => {
        console.error(`❌ WS error: session=${sessionId}`, err.message);
    });
});

// ─────────────────────────────────────────────────────
// START
// ─────────────────────────────────────────────────────

httpServer.listen(port, () => {
    console.log(`\n=================================================`);
    console.log(`⚔️  FUSION COMBAT ENGINE ONLINE — PORT ${port}`);
    console.log(`=================================================\n`);
});