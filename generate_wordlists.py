# generate_wordlists.py
import os
import string
import sys # For potential error exit

# --- Configuration ---
MIN_WORD_LENGTH = 4

# Define base directory for wordlists
WORDLIST_DIR = 'wordlists'
SOURCE_DIR = os.path.join(WORDLIST_DIR, 'source')
PROCESSED_DIR = os.path.join(WORDLIST_DIR, 'processed')

SOURCE_COMMONWEALTH_FILE = os.path.join(SOURCE_DIR, 'source_commonwealth.txt')
SOURCE_NZ_FILE = os.path.join(SOURCE_DIR, 'source_nz_raw.txt')
SOURCE_AU_FILE = os.path.join(SOURCE_DIR, 'source_au_raw.txt')
SOURCE_MAORI_FILE = os.path.join(SOURCE_DIR, 'source_maori_raw.txt')

OUTPUT_COMMON_FILE = os.path.join(PROCESSED_DIR, 'words_common.txt')
OUTPUT_NZ_ONLY_FILE = os.path.join(PROCESSED_DIR, 'words_nz_only.txt')
OUTPUT_AU_ONLY_FILE = os.path.join(PROCESSED_DIR, 'words_au_only.txt')
OUTPUT_MAORI_ONLY_FILE = os.path.join(PROCESSED_DIR, 'words_maori_only.txt')

# Define allowed characters
ALLOWED_CHARS_ENGLISH = set(string.ascii_lowercase)
ALLOWED_CHARS_MAORI = set(string.ascii_lowercase + 'āēīōū')

# --- Helper Functions ---

def is_valid_word(word: str, allow_macrons: bool) -> bool:
    """Checks if a word contains only allowed characters."""
    if not word: # Skip empty strings
        return False
    allowed_set = ALLOWED_CHARS_MAORI if allow_macrons else ALLOWED_CHARS_ENGLISH
    return all(char in allowed_set for char in word)

def process_list(filepath: str, allow_macrons: bool = False) -> set:
    """
    Reads a word list file, cleans words, filters by length and valid characters.
    Returns a set of valid words.
    """
    print(f"Loading source file: {filepath} (Macrons allowed: {allow_macrons})...")
    valid_words = set()
    lines_read = 0
    words_processed = 0
    words_added = 0
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                lines_read += 1
                word = line.strip().lower()
                if not word: # Skip empty lines
                    continue

                words_processed += 1
                # Apply filters
                if len(word) >= MIN_WORD_LENGTH and is_valid_word(word, allow_macrons):
                    valid_words.add(word)
                    words_added += 1
                # Optional: Log invalid words if needed for debugging
                # else:
                #     if len(word) < MIN_WORD_LENGTH:
                #         print(f"  Skipping '{word}': Too short")
                #     elif not is_valid_word(word, allow_macrons):
                #          print(f"  Skipping '{word}': Invalid characters (allow_macrons={allow_macrons})")

        print(f"  Finished {filepath}: Read {lines_read} lines, processed {words_processed} potential words, added {words_added} valid words.")
        return valid_words
    except FileNotFoundError:
        print(f"Error: Source file not found at '{filepath}'. Please ensure it exists.")
        # sys.exit(1) # Optionally exit if a source file is critical
        return set() # Return empty set to allow continuation
    except Exception as e:
        print(f"Error processing file {filepath}: {e}")
        return set()

def write_list(filepath: str, word_set: set):
    """Writes a sorted set of words to a file, one word per line."""
    print(f"Writing output file: {filepath} ({len(word_set)} words)...")
    if not word_set and os.path.exists(filepath):
         print(f"  Warning: Word set is empty. Overwriting/creating empty file: {filepath}")
    elif not word_set:
        print(f"  Warning: Word set is empty. Creating empty file: {filepath}")


    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            sorted_words = sorted(list(word_set))
            for word in sorted_words:
                f.write(f"{word}\n")
        print(f"  Finished writing {filepath}.")
    except Exception as e:
        print(f"Error writing file {filepath}: {e}")

# --- Main Processing Logic ---

if __name__ == "__main__":
    print("Starting wordlist generation process...")

    # 1. Process Source Lists
    common_words = process_list(SOURCE_COMMONWEALTH_FILE, allow_macrons=False)
    nz_words_raw = process_list(SOURCE_NZ_FILE, allow_macrons=False)
    au_words_raw = process_list(SOURCE_AU_FILE, allow_macrons=False)
    maori_words_raw = process_list(SOURCE_MAORI_FILE, allow_macrons=True)

    # 2. Create Specific Lists (Deduplication)
    print("\nCalculating specific word lists (deduplicating)...")
    nz_only_words = nz_words_raw - common_words
    au_only_words = au_words_raw - common_words
    maori_only_words = maori_words_raw - common_words
    print(f"  Found {len(nz_only_words)} NZ-specific words.")
    print(f"  Found {len(au_only_words)} AU-specific words.")
    print(f"  Found {len(maori_only_words)} Māori-specific words (not in common).")


    # 3. Write Output Files
    print("\nWriting final word lists...")
    write_list(OUTPUT_COMMON_FILE, common_words)
    write_list(OUTPUT_NZ_ONLY_FILE, nz_only_words)
    write_list(OUTPUT_AU_ONLY_FILE, au_only_words)
    write_list(OUTPUT_MAORI_ONLY_FILE, maori_only_words)

    print("\nWordlist generation finished.") 