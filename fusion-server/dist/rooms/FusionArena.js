"use strict";
var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.FusionArena = exports.RoomStateSchema = exports.KillEventSchema = exports.PlayerSchema = void 0;
const core_1 = require("@colyseus/core");
const schema_1 = require("@colyseus/schema");
// ─────────────────────────────────────────────────────
// SCHEMAS (What gets sent to clients)
// ─────────────────────────────────────────────────────
class PlayerSchema extends schema_1.Schema {
    constructor() {
        super();
        this.id = "";
        this.username = "";
        this.hp = 400;
        this.shield = 100;
        this.combo = 0;
        this.heat = 0;
        this.kills = 0;
        this.isAlive = true;
        this.damage_taken = 0;
    }
}
exports.PlayerSchema = PlayerSchema;
__decorate([
    (0, schema_1.type)("string"),
    __metadata("design:type", String)
], PlayerSchema.prototype, "id", void 0);
__decorate([
    (0, schema_1.type)("string"),
    __metadata("design:type", String)
], PlayerSchema.prototype, "username", void 0);
__decorate([
    (0, schema_1.type)("number"),
    __metadata("design:type", Number)
], PlayerSchema.prototype, "hp", void 0);
__decorate([
    (0, schema_1.type)("number"),
    __metadata("design:type", Number)
], PlayerSchema.prototype, "shield", void 0);
__decorate([
    (0, schema_1.type)("number"),
    __metadata("design:type", Number)
], PlayerSchema.prototype, "combo", void 0);
__decorate([
    (0, schema_1.type)("number"),
    __metadata("design:type", Number)
], PlayerSchema.prototype, "heat", void 0);
__decorate([
    (0, schema_1.type)("number"),
    __metadata("design:type", Number)
], PlayerSchema.prototype, "kills", void 0);
__decorate([
    (0, schema_1.type)("boolean"),
    __metadata("design:type", Boolean)
], PlayerSchema.prototype, "isAlive", void 0);
__decorate([
    (0, schema_1.type)("number"),
    __metadata("design:type", Number)
], PlayerSchema.prototype, "damage_taken", void 0);
class KillEventSchema extends schema_1.Schema {
    constructor() {
        super();
        this.time = 0;
        this.attacker = "";
        this.victim = "";
        this.word = "";
        this.damage = 0;
        this.isCrit = false;
    }
}
exports.KillEventSchema = KillEventSchema;
__decorate([
    (0, schema_1.type)("number"),
    __metadata("design:type", Number)
], KillEventSchema.prototype, "time", void 0);
__decorate([
    (0, schema_1.type)("string"),
    __metadata("design:type", String)
], KillEventSchema.prototype, "attacker", void 0);
__decorate([
    (0, schema_1.type)("string"),
    __metadata("design:type", String)
], KillEventSchema.prototype, "victim", void 0);
__decorate([
    (0, schema_1.type)("string"),
    __metadata("design:type", String)
], KillEventSchema.prototype, "word", void 0);
__decorate([
    (0, schema_1.type)("number"),
    __metadata("design:type", Number)
], KillEventSchema.prototype, "damage", void 0);
__decorate([
    (0, schema_1.type)("boolean"),
    __metadata("design:type", Boolean)
], KillEventSchema.prototype, "isCrit", void 0);
class RoomStateSchema extends schema_1.Schema {
    constructor() {
        super();
        this.players = new schema_1.MapSchema();
        this.letters = new schema_1.ArraySchema();
        this.killFeed = new schema_1.ArraySchema();
        this.timeLeft = 0;
        this.gameStarted = false;
    }
}
exports.RoomStateSchema = RoomStateSchema;
__decorate([
    (0, schema_1.type)({ map: PlayerSchema }),
    __metadata("design:type", Object)
], RoomStateSchema.prototype, "players", void 0);
__decorate([
    (0, schema_1.type)(["string"]),
    __metadata("design:type", Object)
], RoomStateSchema.prototype, "letters", void 0);
__decorate([
    (0, schema_1.type)("number"),
    __metadata("design:type", Number)
], RoomStateSchema.prototype, "timeLeft", void 0);
__decorate([
    (0, schema_1.type)("boolean"),
    __metadata("design:type", Boolean)
], RoomStateSchema.prototype, "gameStarted", void 0);
__decorate([
    (0, schema_1.type)({ array: KillEventSchema }),
    __metadata("design:type", Object)
], RoomStateSchema.prototype, "killFeed", void 0);
// ─────────────────────────────────────────────────────
// GAME LOGIC
// ─────────────────────────────────────────────────────
class FusionArena extends core_1.Room {
    constructor() {
        super(...arguments);
        this.maxClients = 8;
        this.gameTime = 60;
        this.gameLoopInterval = null;
        this.DAMAGE_MULTIPLIERS = {
            3: 5,
            4: 8,
            5: 10,
            6: 14,
            7: 16,
            8: 18,
            9: 20,
            10: 22,
            12: 30,
            15: 40
        };
    }
    // ─ INITIALIZATION
    onCreate(options) {
        console.log("🎮 New FusionArena room created");
        console.log("🎮 Room ID:", this.roomId);
        console.log("🎮 Room Name:", this.roomName); // Already set by matchmaker
        console.log("🎮 Options:", options);
        console.log("🎮 MaxClients:", this.maxClients);
        console.log("🎮 Current clients:", this.clients.length);
        // FIX: Don't auto-dispose when empty, wait for players
        this.autoDispose = false;
        this.seatReservationTimeout = 60;
        // FIX: Keep room alive for 60s waiting for players
        this.setState(new RoomStateSchema());
        this.generateLetters();
        this.onMessage("ready", (client) => this.handleReady(client));
        this.onMessage("submit_word", (client, message) => this.handleWordSubmission(client, message));
        // Log room state every 5 seconds for debugging
        setInterval(() => {
            console.log(`📊 [Room ${this.roomId}] Players: ${this.state.players.size} | Clients: ${this.clients.length} | GameStarted: ${this.state.gameStarted}`);
        }, 5000);
    }
    onAuth(client, options) {
        console.log(`🔐 [Auth] Client attempting join: ${options.username || 'Unknown'}`);
        return true; // Always allow joins if room isn't full
    }
    onJoin(client, options) {
        try {
            console.log(`👤 [JOIN] ${options.username || 'Unknown'} joining (current: ${this.state.players.size} players)`);
            console.log(`👤 [JOIN] Client ID: ${client.sessionId}`);
            console.log(`👤 [JOIN] Total clients in room: ${this.clients.length}`);
            const player = new PlayerSchema();
            player.id = client.sessionId;
            player.username = options.username || `Player_${client.sessionId.substring(0, 4)}`;
            this.state.players.set(client.sessionId, player);
            console.log(`👤 [JOIN] Player added to state. Total players: ${this.state.players.size}`);
            client.send("room_joined", {
                roomId: this.roomId,
                yourId: client.sessionId,
                letters: Array.from(this.state.letters)
            });
            this.tryStartGame();
        }
        catch (error) {
            console.error(`❌ [JOIN] Error: ${error.message}`);
            console.error(error.stack);
        }
    }
    onLeave(client, code) {
        const player = this.state.players.get(client.sessionId);
        if (player) {
            console.log(`👋 ${player.username} left (code: ${code})`);
            // Only mark dead if game is already running
            if (this.state.gameStarted) {
                player.isAlive = false;
                if (this.getAlivePlayers().length === 0) {
                    this.endGame();
                }
            }
            // Don't remove player from state — allows reconnection
        }
    }
    // ─ GAME FLOW
    tryStartGame() {
        if (this.state.gameStarted)
            return;
        if (this.state.players.size < 2)
            return;
        this.state.gameStarted = true;
        this.gameTime = 60;
        this.state.timeLeft = this.gameTime;
        console.log("⚔️ GAME STARTED!");
        this.broadcast("game_started", { timeLeft: this.gameTime });
        this.gameLoopInterval = setInterval(() => this.gameLoop(), 1000 / 30);
    }
    gameLoop() {
        if (!this.state.gameStarted)
            return;
        if (this.gameTime > 0) {
            this.gameTime -= 1 / 30;
            this.state.timeLeft = Math.ceil(this.gameTime);
        }
        const alive = this.getAlivePlayers();
        if (alive.length <= 1 || this.gameTime <= 0) {
            this.endGame();
        }
    }
    endGame() {
        if (!this.state.gameStarted)
            return;
        console.log("🏁 GAME ENDED");
        this.state.gameStarted = false;
        if (this.gameLoopInterval) {
            clearInterval(this.gameLoopInterval);
        }
        const alive = this.getAlivePlayers();
        const winner = alive.length > 0 ? alive[0] : null;
        const stats = Array.from(this.state.players.values()).map(p => ({
            username: p.username,
            kills: p.kills,
            hp: p.hp,
            damage_taken: p.damage_taken
        }));
        this.broadcast("match_ended", {
            winner: winner ? winner.username : "DRAW",
            stats
        });
        setTimeout(() => this.disconnect(), 5000);
    }
    // ─ MESSAGE HANDLERS
    handleReady(client) {
        const player = this.state.players.get(client.sessionId);
        if (player) {
            console.log(`✅ ${player.username} is ready`);
        }
    }
    handleWordSubmission(client, message) {
        const attacker = this.state.players.get(client.sessionId);
        if (!attacker || !attacker.isAlive) {
            client.send("error", { reason: "You're not alive" });
            return;
        }
        const word = (message.word || "").toUpperCase().trim();
        if (word.length < 3 || word.length > 20) {
            client.send("error", { reason: "Word must be 3-20 letters" });
            return;
        }
        if (!this.validateWord(word)) {
            client.send("error", { reason: "Not a valid English word" });
            return;
        }
        const baseDamage = this.calculateBaseDamage(word);
        const isCrit = Math.random() < 0.15;
        const damage = isCrit ? Math.ceil(baseDamage * 1.5) : baseDamage;
        const aliveOthers = this.getAlivePlayers().filter(p => p.id !== client.sessionId);
        if (aliveOthers.length === 0)
            return;
        const target = aliveOthers[Math.floor(Math.random() * aliveOthers.length)];
        if (target.shield > damage) {
            target.shield -= damage;
        }
        else {
            const hpDamage = damage - target.shield;
            target.shield = 0;
            target.hp -= hpDamage;
        }
        target.damage_taken += damage;
        attacker.combo++;
        attacker.heat = Math.min(100, attacker.heat + 10);
        const event = new KillEventSchema();
        event.time = this.state.timeLeft;
        event.attacker = attacker.username;
        event.victim = target.username;
        event.word = word;
        event.damage = damage;
        event.isCrit = isCrit;
        this.state.killFeed.push(event);
        if (this.state.killFeed.length > 15) {
            this.state.killFeed.shift();
        }
        this.broadcast("attack", {
            attacker: attacker.username,
            target: target.username,
            damage,
            word,
            isCrit,
            targetHp: Math.max(0, target.hp),
            targetShield: target.shield
        });
        if (target.hp <= 0) {
            target.hp = 0;
            target.isAlive = false;
            attacker.kills++;
            this.broadcast("kill", {
                attacker: attacker.username,
                victim: target.username,
                totalKills: attacker.kills
            });
            if (this.getAlivePlayers().length <= 1) {
                this.endGame();
            }
        }
    }
    // ─ UTILITY
    generateLetters() {
        const vowels = "AEIOU";
        const consonants = "BCDFGHJKLMNPQRSTVWXYZ";
        const letters = [];
        for (let i = 0; i < 3; i++) {
            letters.push(vowels[Math.floor(Math.random() * vowels.length)]);
        }
        for (let i = 0; i < 3; i++) {
            letters.push(consonants[Math.floor(Math.random() * consonants.length)]);
        }
        // FIX: Assign to ArraySchema properly
        const shuffled = letters.sort(() => 0.5 - Math.random());
        this.state.letters = new schema_1.ArraySchema(...shuffled);
    }
    validateWord(word) {
        return word.length >= 3 && /^[A-Z]+$/.test(word);
    }
    calculateBaseDamage(word) {
        const len = word.length;
        return this.DAMAGE_MULTIPLIERS[len] || 5;
    }
    getAlivePlayers() {
        return Array.from(this.state.players.values()).filter(p => p.isAlive);
    }
}
exports.FusionArena = FusionArena;
