from collections import defaultdict

def get_signature(word):
    return "".join(sorted(word.lower()))

def can_make(smaller_word, larger_word):
    """Checks if smaller_word is a subset of larger_word letters."""
    large_list = list(larger_word)
    for char in smaller_word:
        if char in large_list:
            large_list.remove(char)
        else:
            return False
    return True

# 1. Load your dictionary
file_path = 'SupaDB1.txt'
all_words = []
with open(file_path, 'r') as f:
    all_words = [line.strip().lower() for line in f if line.strip()]

# 2. Map by signature
anagram_map = defaultdict(list)
for w in all_words:
    anagram_map[get_signature(w)].append(w)

# 3. Create the Hierarchical Output
output_path = 'pattern_groups.txt'
with open(output_path, 'w', encoding='utf-8') as out:
    # We will track processed words so we don't repeat groups
    processed_sigs = set()

    for word in all_words:
        sig = get_signature(word)
        if sig in processed_sigs:
            continue
        
        # Get all words in this anagram group
        group = anagram_map[sig]
        
        # Sort so words starting with the current word's first letter come first
        start_char = word[0]
        primary_group = sorted(group, key=lambda x: x[0] != start_char)
        
        if len(primary_group) > 1:
            out.write(f"MAIN GROUP ({start_char.upper()}): {', '.join(primary_group)}\n")
            
            # Find Sub-patterns (words that are subsets of this group)
            subsets = []
            # Optimization: only check a sample of words to find subsets
            for other_word in all_words:
                if len(other_word) < len(word) and len(other_word) >= 3:
                    if can_make(other_word, word) and other_word not in primary_group:
                        subsets.append(other_word)
            
            if subsets:
                # Group subsets by their first letter to keep the 'p' trend
                subsets.sort(key=lambda x: x[0] != start_char)
                out.write(f"   ┗ SUBSETS: {', '.join(subsets[:15])}\n")
            
            out.write("-" * 20 + "\n")
            processed_sigs.add(sig)

print(f"✅ Pattern groups saved to {'cheats.txt'}")