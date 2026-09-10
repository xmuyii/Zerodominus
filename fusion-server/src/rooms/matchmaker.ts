import { WebSocket } from "ws";
import { FusionArena } from "./rooms/FusionArena";
import { v4 as uuidv4 } from "uuid";

interface Reservation {
    sessionId: string;
    roomId: string;
    username: string;
    expiresAt: number;
}

export class Matchmaker {
    private rooms = new Map<string, FusionArena>();
    private reservations = new Map<string, Reservation>();
    private sessionToRoom = new Map<string, string>();

    constructor() {
        setInterval(() => this.cleanReservations(), 5000);
    }

    joinOrCreate(username: string): { sessionId: string; roomId: string } {
        let room = this.findAvailableRoom();

        if (!room) {
            const roomId = "room_" + uuidv4().substring(0, 8);
            room = new FusionArena(roomId);
            this.rooms.set(roomId, room);
            console.log(`🏠 Created new room: ${roomId}`);

            // Add 2 bots automatically so solo players can test immediately
            const bot1Id = "bot_" + uuidv4().substring(0, 6);
            const bot2Id = "bot_" + uuidv4().substring(0, 6);
            room.addBot(bot1Id, "BOT_Alpha");
            room.addBot(bot2Id, "BOT_Sigma");
        }

        const sessionId = uuidv4().substring(0, 12);
        const reservation: Reservation = {
            sessionId,
            roomId: room.roomId,
            username,
            expiresAt: Date.now() + 30_000,
        };

        this.reservations.set(sessionId, reservation);
        console.log(`🎫 Reserved: ${username} | session=${sessionId} room=${room.roomId}`);

        return { sessionId, roomId: room.roomId };
    }

    completeJoin(sessionId: string, ws: WebSocket): boolean {
        const reservation = this.reservations.get(sessionId);

        if (!reservation) {
            console.warn(`⚠️  No reservation: session=${sessionId}`);
            ws.send(JSON.stringify({ type: "error", data: { reason: "Invalid or expired session" } }));
            ws.close(4001, "Invalid session");
            return false;
        }

        if (Date.now() > reservation.expiresAt) {
            console.warn(`⚠️  Reservation expired: session=${sessionId}`);
            this.reservations.delete(sessionId);
            ws.send(JSON.stringify({ type: "error", data: { reason: "Seat reservation expired" } }));
            ws.close(4002, "Reservation expired");
            return false;
        }

        const room = this.rooms.get(reservation.roomId);
        if (!room) {
            console.warn(`⚠️  Room not found: ${reservation.roomId}`);
            ws.send(JSON.stringify({ type: "error", data: { reason: "Room no longer exists" } }));
            ws.close(4003, "Room not found");
            return false;
        }

        this.reservations.delete(sessionId);
        this.sessionToRoom.set(sessionId, reservation.roomId);
        room.addPlayer(sessionId, reservation.username, ws);

        ws.on("close", () => this.handleDisconnect(sessionId));
        return true;
    }

    handleMessage(sessionId: string, message: any): void {
        const roomId = this.sessionToRoom.get(sessionId);
        if (!roomId) return;
        const room = this.rooms.get(roomId);
        if (!room) return;
        room.handleMessage(sessionId, message);
    }

    private handleDisconnect(sessionId: string): void {
        const roomId = this.sessionToRoom.get(sessionId);
        if (!roomId) return;
        const room = this.rooms.get(roomId);
        if (room) {
            room.removePlayer(sessionId);
            if (room.isEmpty) {
                this.rooms.delete(roomId);
                console.log(`🗑  Room ${roomId} removed`);
            }
        }
        this.sessionToRoom.delete(sessionId);
    }

    getRoomList() {
        return Array.from(this.rooms.values()).map(room => ({
            roomId: room.roomId,
            clients: room.clientCount,
            maxClients: room.maxClients,
        }));
    }

    private findAvailableRoom(): FusionArena | null {
        for (const room of this.rooms.values()) {
            if (room.clientCount < room.maxClients) {
                return room;
            }
        }
        return null;
    }

    private cleanReservations(): void {
        const now = Date.now();
        for (const [id, res] of this.reservations.entries()) {
            if (now > res.expiresAt) {
                this.reservations.delete(id);
                console.log(`🧹 Expired reservation: session=${id}`);
            }
        }
    }
}