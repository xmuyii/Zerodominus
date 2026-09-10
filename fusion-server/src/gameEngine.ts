import { CONFIG } from './config';

export interface PlayerRoundSession {
  name: string;
  user_id: string;
  pts: number;
  leveled_up: boolean;
}

export class GameEngine {
  public running = false;
  public active = false;
  public forceStop = false;
  public word1 = "";
  public word2 = "";
  public letters = "";
  public extraLetters = "";
  public scores: Record<string, PlayerRoundSession> = {};
  public usedWords: string[] = [];
  public msgCount = 0;
  public gamesPlayed = 0;
  public emptyRounds = 0;
  public cratesDropping = 0;
  public crateClaimers: any[] = [];
  public decoyClaimers: any[] = [];
  public freezeUntil = 0;
  public activeTopic: number = CONFIG.FUSION_TOPIC_ID;

  constructor() {}
}

export const activeGames: Map<number, GameEngine> = new Map();

export function getEngine(chatId: number): GameEngine {
  if (!activeGames.has(chatId)) {
    activeGames.set(chatId, new GameEngine());
  }
  return activeGames.get(chatId)!;
}