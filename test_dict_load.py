#!/usr/bin/env python3
import sys
import os

# Add current dir to path
sys.path.insert(0, os.getcwd())

# Import and test dictionary loading
from main import load_dictionary, DICTIONARY, DICTIONARY_LOADED

print("Testing dictionary loading...")
print(f"Dictionary loaded flag: {DICTIONARY_LOADED}")
print(f"Words in DICTIONARY: {len(DICTIONARY)}")

if DICTIONARY:
    sample = list(DICTIONARY)[:10]
    print(f"Sample words: {sample}")
    
    # Test specific words
    test_words = ["aah", "players", "dangers", "save", "word"]
    for word in test_words:
        exists = word in DICTIONARY
        print(f"  '{word}' in DICTIONARY: {exists}")
else:
    print("❌ DICTIONARY IS EMPTY!")
