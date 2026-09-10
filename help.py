from collections import defaultdict

# 1. Configuration
input_file = 'SupaDB1.txt'
output_file = 'full_anagram_patterns.txt'
anagram_groups = defaultdict(list)

# 2. Process the input file
try:
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            word = line.strip().lower()
            if not word: continue
            
            # Normalization: Sort letters to create a signature
            signature = "".join(sorted(word))
            anagram_groups[signature].append(word)
except FileNotFoundError:
    print(f"❌ Error: {input_file} not found.")
    exit()

# 3. Save ALL patterns to the text file
with open(output_file, 'w', encoding='utf-8') as out:
    # Sort groups by size (most words in a pattern first)
    # We remove [:10] to include the entire list
    all_patterns = sorted(anagram_groups.values(), key=len, reverse=True)
    
    out.write(f"--- COMPLETE ANAGRAM PATTERNS FOR {input_file} ---\n")
    out.write(f"Total Unique Patterns: {len(all_patterns)}\n\n")
    
    count = 0
    for group in all_patterns:
        # Filter: Only save if the pattern actually has anagrams (2 or more words)
        if len(group) > 1:
            out.write(f"{len(group)} words: {', '.join(group)}\n")
            count += 1

print(f"✅ Success! {count} patterns with anagrams saved to {output_file}")