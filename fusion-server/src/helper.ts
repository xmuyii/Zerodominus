import fs from 'fs';
import path from 'path';

export let DICTIONARY: Set<string> = new Set();
let isDictionaryLoaded = false;

export function loadDictionary(): boolean {
  if (isDictionaryLoaded) return true;
  const dictFiles = ['SupaDB1.txt', 'dictionary.txt', 'words.txt'];

  for (const file of dictFiles) {
    const fullPath = path.resolve(file);
    if (fs.existsSync(fullPath)) {
      console.log(`[DICT] Found ${file}, loading...`);
      const content = fs.readFileSync(fullPath, 'utf-8');
      let lines = content.split(/\r?\n/).map(w => w.trim().toLowerCase());
      
      if (lines.length > 0 && ['word', 'word_id', 'id'].includes(lines[0])) {
        lines = lines.slice(1);
      }
      
      DICTIONARY = new Set(lines.filter(Boolean));
      console.log(`✅ [OK] Dictionary loaded: ${DICTIONARY.size} words from ${file}`);
      isDictionaryLoaded = true;
      return true;
    }
  }
  console.log(`❌ [ERROR] No dictionary file found.`);
  return false;
}

export function detectWordPattern(word: string): 'palindrome' | 'double_letters' | 'vowel_rich' | 'anagram_set' | 'standard' {
  const upper = word.toUpperCase();
  if (upper === upper.split('').reverse().join('')) return 'palindrome';
  
  for (let i = 0; i < upper.length - 1; i++) {
    if (upper[i] === upper[i + 1]) return 'double_letters';
  }
  
  const vowelCount = (upper.match(/[AEIOU]/g) || []).length;
  if (vowelCount >= 3) return 'vowel_rich';
  if (new Set(upper).size === upper.length) return 'anagram_set';
  
  return 'standard';
}

export function getCharacterCounts(str: string): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const char of str) {
    counts[char] = (counts[char] || 0) + 1;
  }
  return counts;
}

export function canSpell(word: string, pool: string): boolean {
  const poolCounts = getCharacterCounts(pool);
  const wordCounts = getCharacterCounts(word);
  for (const [char, needed] of Object.entries(wordCounts)) {
    if ((poolCounts[char] || 0) < needed) return false;
  }
  return true;
}

export function computePossibleWords(letters: string): number {
  if (DICTIONARY.size === 0) loadDictionary();
  const poolCounts = getCharacterCounts(letters);
  let count = 0;

  for (const word of DICTIONARY) {
    if (word.length < 3) continue;
    const wordCounts = getCharacterCounts(word);
    let valid = true;
    for (const [char, needed] of Object.entries(wordCounts)) {
      if ((poolCounts[char] || 0) < needed) {
        valid = false;
        break;
      }
    }
    if (valid) count++;
  }
  return count;
}