import fs from "fs";
import path from "path";

export let DICTIONARY: Set<string> = new Set();
let isDictionaryLoaded = false;

/**
 * Sweeps the root directory for common dictionary files and loads them into memory.
 */
export function loadDictionary(): boolean {
    if (isDictionaryLoaded) return true;
    const dictFiles = ["SupaDB1.txt", "dictionary.txt", "words.txt"];

    for (const file of dictFiles) {
        const fullPath = path.resolve(file);
        if (fs.existsSync(fullPath)) {
            console.log(`[DICT] Found ${file}, loading valid vocabulary...`);
            const content = fs.readFileSync(fullPath, "utf-8");
            let lines = content.split(/\r?\n/).map(w => w.trim().toLowerCase());
            
            // Skip headers if they exist
            if (lines.length > 0 && ["word", "word_id", "id"].includes(lines[0])) {
                lines = lines.slice(1);
            }
            
            DICTIONARY = new Set(lines.filter(Boolean));
            console.log(`✅ [DICT] Successfully loaded ${DICTIONARY.size} words.`);
            isDictionaryLoaded = true;
            return true;
        }
    }
    console.warn(`⚠️ [DICT] No dictionary files found. Word validation fallback active.`);
    return false;
}

/**
 * Returns a key-value counter map of characters in a string.
 */
export function getCharacterCounts(str: string): Record<string, number> {
    const counts: Record<string, number> = {};
    for (const char of str) {
        counts[char] = (counts[char] || 0) + 1;
    }
    return counts;
}

/**
 * Validates if a submitted word can be formed from an array/pool of letters.
 */
export function canSpell(word: string, pool: string[]): boolean {
    const poolString = pool.join("").toLowerCase();
    const poolCounts = getCharacterCounts(poolString);
    const wordCounts = getCharacterCounts(word.toLowerCase());

    for (const [char, needed] of Object.entries(wordCounts)) {
        if ((poolCounts[char] || 0) < needed) {
            return false;
        }
    }
    return true;
}

/**
 * Checks for specific word types based on your Python bot rules.
 */
export function detectWordPattern(word: string): "palindrome" | "double_letters" | "vowel_rich" | "anagram_set" | "standard" {
    const upper = word.toUpperCase();
    if (upper === upper.split("").reverse().join("")) return "palindrome";
    
    for (let i = 0; i < upper.length - 1; i++) {
        if (upper[i] === upper[i + 1]) return "double_letters";
    }
    
    const vowelCount = (upper.match(/[AEIOU]/g) || []).length;
    if (vowelCount >= 3) return "vowel_rich";
    if (new Set(upper).size === upper.length) return "anagram_set";
    
    return "standard";
}