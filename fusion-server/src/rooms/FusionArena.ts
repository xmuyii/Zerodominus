import { WebSocket } from "ws";

// ─────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────

export interface Player {
    id: string;
    username: string;
    hp: number;
    shield: number;
    combo: number;
    heat: number;
    kills: number;
    isAlive: boolean;
    damageTaken: number;
    isBot: boolean;
    ws: WebSocket | null;
}

export interface KillEvent {
    time: number;
    attacker: string;
    victim: string;
    word: string;
    damage: number;
    isCrit: boolean;
}

// Bot word pool — varied lengths for different damage
const BOT_WORDS = [
    "CAT", "DOG", "RUN", "HIT",           // 3 letters - 5 dmg
    "FIRE", "DRAW", "STAB", "MOVE",        // 4 letters - 8 dmg
    "BLAST", "CRUSH", "SWORD", "ARROW",    // 5 letters - 10 dmg
    "ATTACK", "DEFEND", "CHARGE", "STRIKE",// 6 letters - 14 dmg
    "DESTROY", "SHATTER", "WARFARE",       // 7 letters - 16 dmg
];

// ─────────────────────────────────────────────────────
// ROOM
// ─────────────────────────────────────────────────────

export class FusionArena {
    readonly roomId: string;
    readonly maxClients = 8;

    private players = new Map<string, Player>();
    private letters: string[] = [];
    private gameStarted = false;
    private gameTime = 60;
    private timeLeft = 0;
    private killFeed: KillEvent[] = [];
    private gameLoopInterval: ReturnType<typeof setInterval> | null = null;
    private botIntervals: ReturnType<typeof setInterval>[] = [];

    private readonly DAMAGE_MULTIPLIERS: Record<number, number> = {
        3: 5, 4: 8, 5: 10, 6: 14, 7: 16,
        8: 18, 9: 20, 10: 22, 12: 30, 15: 40,
    };

    constructor(roomId: string) {
        this.roomId = roomId;
        this.generateLetters();
        console.log(`🎮 [${roomId}] FusionArena created`);
    }

    // ─ JOIN / LEAVE

    addPlayer(sessionId: string, username: string, ws: WebSocket): void {
        const player: Player = {
            id: sessionId,
            username,
            hp: 400,
            shield: 100,
            combo: 0,
            heat: 0,
            kills: 0,
            isAlive: true,
            damageTaken: 0,
            isBot: false,
            ws,
        };
        this.players.set(sessionId, player);
        console.log(`👤 [${this.roomId}] ${username} joined (${this.players.size} players)`);

        // Send room state to the joining player
        this.sendTo(ws, "room_joined", {
            roomId: this.roomId,
            yourId: sessionId,
            letters: this.letters,
            players: this.getPlayerList(),
        });

        // Notify everyone else
        this.broadcastExcept(sessionId, "player_joined", {
            id: sessionId,
            username,
            hp: 400,
            shield: 100,
        });

        this.tryStartGame();
    }

    addBot(botId: string, username: string): void {
        const bot: Player = {
            id: botId,
            username,
            hp: 400,
            shield: 100,
            combo: 0,
            heat: 0,
            kills: 0,
            isAlive: true,
            damageTaken: 0,
            isBot: true,
            ws: null,
        };
        this.players.set(botId, bot);
        console.log(`🤖 [${this.roomId}] Bot ${username} added`);

        // Notify real players about bot joining
        this.broadcast("player_joined", {
            id: botId,
            username,
            hp: 400,
            shield: 100,
            isBot: true,
        });

        this.tryStartGame();
    }

    removePlayer(sessionId: string): void {
        const player = this.players.get(sessionId);
        if (!player) return;

        console.log(`👋 [${this.roomId}] ${player.username} left`);

        if (this.gameStarted) {
            player.isAlive = false;
            if (this.getAlivePlayers().length <= 1) {
                this.endGame();
            }
        }

        this.players.delete(sessionId);
        this.broadcast("player_left", { id: sessionId, username: player.username });
    }

    get clientCount(): number {
        return this.players.size;
    }

    get isEmpty(): boolean {
        // Room is empty if no real (non-bot) players remain
        return Array.from(this.players.values()).every(p => p.isBot);
    }

    // ─ MESSAGE HANDLER

    handleMessage(sessionId: string, message: any): void {
        const player = this.players.get(sessionId);
        if (!player) return;

        switch (message.type) {
            case "submit_word":
                this.handleWordSubmission(player, message.word || "");
                break;
            case "ready":
                console.log(`✅ [${this.roomId}] ${player.username} is ready`);
                break;
        }
    }

    // ─ GAME FLOW

    private tryStartGame(): void {
    if (this.gameStarted) return;
    
    // Count real players only
    const realPlayers = Array.from(this.players.values()).filter(p => !p.isBot);
    const bots = Array.from(this.players.values()).filter(p => p.isBot);
    
    // Start if at least 1 real player + at least 1 bot, OR 2+ real players
    if (realPlayers.length >= 1 && (bots.length >= 1 || realPlayers.length >= 2)) {
        // good to start
    } else {
        return;
    }

    this.gameStarted = true;
    this.gameTime = 60;
    this.timeLeft = 60;

    console.log(`⚔️  [${this.roomId}] GAME STARTED`);
    this.broadcast("game_started", { timeLeft: this.gameTime });
    this.gameLoopInterval = setInterval(() => this.gameLoop(), 1000);

    for (const player of this.players.values()) {
        if (player.isBot) this.startBotAI(player);
    }
}

    private startBotAI(bot: Player): void {
        // Bots submit a random word every 3-6 seconds
        const minDelay = 1000;
        const maxDelay = 2000;

        const scheduleNextWord = () => {
            if (!this.gameStarted || !bot.isAlive) return;
            const delay = minDelay + Math.random() * (maxDelay - minDelay);
            const interval = setTimeout(() => {
                if (!this.gameStarted || !bot.isAlive) return;
                const word = BOT_WORDS[Math.floor(Math.random() * BOT_WORDS.length)];
                console.log(`🤖 [Bot:${bot.username}] submitting: ${word}`);
                this.handleWordSubmission(bot, word);
                scheduleNextWord();
            }, delay);
            this.botIntervals.push(interval as any);
        };

        // Slight initial delay so game_started fires first
        setTimeout(() => scheduleNextWord(), 500);
    }

    private gameLoop(): void {
        if (!this.gameStarted) return;

        this.gameTime -= 1;
        this.timeLeft = this.gameTime;

        this.broadcast("timer_update", { timeLeft: this.timeLeft });

        if (this.getAlivePlayers().length <= 1 || this.gameTime <= 0) {
            this.endGame();
        }
    }

    private endGame(): void {
        if (!this.gameStarted) return;

        console.log(`🏁 [${this.roomId}] GAME ENDED`);
        this.gameStarted = false;

        if (this.gameLoopInterval) {
            clearInterval(this.gameLoopInterval);
            this.gameLoopInterval = null;
        }

        // Stop all bot timers
        for (const interval of this.botIntervals) {
            clearTimeout(interval);
        }
        this.botIntervals = [];

        const alive = this.getAlivePlayers();
        const winner = alive.length > 0 ? alive[0] : null;

        const stats = Array.from(this.players.values()).map(p => ({
            username: p.username,
            kills: p.kills,
            hp: p.hp,
            damageTaken: p.damageTaken,
            isBot: p.isBot,
        }));

        this.broadcast("match_ended", {
            winner: winner ? winner.username : "DRAW",
            stats,
        });

        setTimeout(() => this.dispose(), 5000);
    }

    private dispose(): void {
        if (this.gameLoopInterval) clearInterval(this.gameLoopInterval);
        for (const interval of this.botIntervals) clearTimeout(interval);
        for (const player of this.players.values()) {
            if (!player.isBot && player.ws) {
                try { player.ws.close(1000, "Match ended"); } catch (_) {}
            }
        }
        this.players.clear();
        console.log(`🗑  [${this.roomId}] Room disposed`);
    }

    // ─ WORD SUBMISSION

    private handleWordSubmission(attacker: Player, rawWord: string): void {
        if (!this.gameStarted) {
            if (!attacker.isBot && attacker.ws)
                this.sendTo(attacker.ws, "error", { reason: "Game not started yet" });
            return;
        }
        if (!attacker.isAlive) {
            if (!attacker.isBot && attacker.ws)
                this.sendTo(attacker.ws, "error", { reason: "You are eliminated" });
            return;
        }

        const word = rawWord.toUpperCase().trim();

        if (word.length < 3 || word.length > 20) {
            if (!attacker.isBot && attacker.ws)
                this.sendTo(attacker.ws, "error", { reason: "Word must be 3–20 letters" });
            return;
        }
        if (!/^[A-Z]+$/.test(word)) {
            if (!attacker.isBot && attacker.ws)
                this.sendTo(attacker.ws, "error", { reason: "Letters only" });
            return;
        }

        const baseDamage = this.DAMAGE_MULTIPLIERS[word.length] ?? 5;
        const isCrit = Math.random() < 0.15;
        const damage = isCrit ? Math.ceil(baseDamage * 1.5) : baseDamage;

        const targets = this.getAlivePlayers().filter(p => p.id !== attacker.id);
        if (targets.length === 0) return;

        const target = targets[Math.floor(Math.random() * targets.length)];

        // Apply damage
        if (target.shield >= damage) {
            target.shield -= damage;
        } else {
            target.hp -= damage - target.shield;
            target.shield = 0;
        }
        target.damageTaken += damage;

        attacker.combo++;
        attacker.heat = Math.min(100, attacker.heat + 10);

        // Kill feed
        const event: KillEvent = {
            time: this.timeLeft,
            attacker: attacker.username,
            victim: target.username,
            word,
            damage,
            isCrit,
        };
        this.killFeed.push(event);
        if (this.killFeed.length > 15) this.killFeed.shift();

        this.broadcast("attack", {
            attacker: attacker.username,
            target: target.username,
            word,
            damage,
            isCrit,
            targetHp: Math.max(0, target.hp),
            targetShield: target.shield,
        });

        if (target.hp <= 0) {
            target.hp = 0;
            target.isAlive = false;
            attacker.kills++;

            this.broadcast("kill", {
                attacker: attacker.username,
                victim: target.username,
                totalKills: attacker.kills,
            });

            if (this.getAlivePlayers().length <= 1) {
                this.endGame();
            }
        }
    }

    // ─ UTILITIES

    private generateLetters(): void {
        const vowels = "AEIOU";
        const consonants = "BCDFGHJKLMNPQRSTVWXYZ";
        const letters: string[] = [];
        for (let i = 0; i < 3; i++)
            letters.push(vowels[Math.floor(Math.random() * vowels.length)]);
        for (let i = 0; i < 3; i++)
            letters.push(consonants[Math.floor(Math.random() * consonants.length)]);
        this.letters = letters.sort(() => Math.random() - 0.5);
    }

    private getAlivePlayers(): Player[] {
        return Array.from(this.players.values()).filter(p => p.isAlive);
    }

    private getPlayerList() {
        return Array.from(this.players.values()).map(p => ({
            id: p.id,
            username: p.username,
            hp: p.hp,
            shield: p.shield,
            isBot: p.isBot,
        }));
    }

    private broadcast(type: string, data: any): void {
        const msg = JSON.stringify({ type, data });
        for (const player of this.players.values()) {
            if (!player.isBot && player.ws && player.ws.readyState === WebSocket.OPEN) {
                player.ws.send(msg);
            }
        }
    }

    private broadcastExcept(excludeId: string, type: string, data: any): void {
        const msg = JSON.stringify({ type, data });
        for (const [id, player] of this.players.entries()) {
            if (id !== excludeId && !player.isBot && player.ws && player.ws.readyState === WebSocket.OPEN) {
                player.ws.send(msg);
            }
        }
    }

    private sendTo(ws: WebSocket, type: string, data: any): void {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type, data }));
        }
    }
}