import random
import string
from collections.abc import Iterable
import sys
import sqlite3 # Standard import should now work due to injection
import os # Added os
import time # Added time
import unicodedata # Add unicodedata for normalization

# Constants
MIN_WORD_LENGTH = 4
# Define vowels (including macrons) at the module level
VOWELS = set("aeiouāēīōū") 

RANKS = {
    0: "Beginner", 0.02: "Good Start", 0.05: "Moving Up", 0.08: "Good",
    0.15: "Solid", 0.25: "Nice", 0.40: "Great", 0.50: "Amazing",
    0.70: "Genius", 1.00: "Queen Bee"
}

# --- Macron Normalization --- START
MACRON_MAP = str.maketrans("āēīōū", "aeiou")

def normalize_word(word: str) -> str:
    """Converts word to lowercase and replaces Māori macrons with non-macron vowels."""
    if not isinstance(word, str):
        return ""
    return word.lower().translate(MACRON_MAP)
# --- Macron Normalization --- END

# --- Database Helper ---
def _get_db_connection(db_path):
    """Helper to get a database connection."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row # Return rows that behave like dicts
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error to {db_path}: {e}")
        return None

# --- Core Game Logic using Database ---

def choose_letters(db_path: str, active_list_types: list[str]):
    """
    Chooses 7 unique letters by first finding a valid pangram from the database
    within the active word lists, ensuring the letter set includes a vowel.
    """
    if not active_list_types:
        raise ValueError("No active word list types provided.")

    print(f"--- [choose_letters PANGRAM-FIRST] Starting... DB: {db_path}, Lists: {active_list_types}")
    start_time = time.time()

    conn = None
    valid_pangram_candidates = []
    
    try:
        conn = _get_db_connection(db_path)
        if not conn:
            raise ConnectionError(f"Could not connect to database at {db_path}")

        cursor = conn.cursor()
        placeholders = ','.join('?' * len(active_list_types))
        # Query potential candidates (length >= 7)
        sql_query = f"""
            SELECT DISTINCT word 
            FROM words 
            WHERE list_type IN ({placeholders})
              AND LENGTH(word) >= 7
        """
        
        print("--- [choose_letters PANGRAM-FIRST] Querying candidate words...")
        cursor.execute(sql_query, active_list_types)
        candidate_words = cursor.fetchall()
        print(f"--- [choose_letters PANGRAM-FIRST] Found {len(candidate_words)} candidate words (len >= 7).")

        # Filter candidates in Python
        print("--- [choose_letters PANGRAM-FIRST] Filtering candidates for 7 unique letters and vowels...")
        for row in candidate_words:
            word = row[0]
            unique_letters = set(word)
            
            if len(unique_letters) == 7:
                # Check for vowels (including macrons)
                normalized_letters = {normalize_word(l) for l in unique_letters}
                if any(v in normalized_letters for v in VOWELS):
                    valid_pangram_candidates.append(word)

        print(f"--- [choose_letters PANGRAM-FIRST] Found {len(valid_pangram_candidates)} valid pangram candidates after filtering.")

    except sqlite3.Error as e:
        print(f"Database error during pangram candidate search: {e}")
        raise ConnectionError(f"Database error finding pangrams: {e}") # Re-raise as connection error or specific DB error
    finally:
        if conn:
            conn.close()

    if not valid_pangram_candidates:
        end_time = time.time()
        print(f"--- [choose_letters PANGRAM-FIRST] Failed. Time elapsed: {end_time - start_time:.2f} seconds.")
        raise RuntimeError(
            f"Could not find any words with exactly 7 unique letters (including a vowel) "
            f"in the active word lists: {active_list_types}. "
            f"Check database content and list selections."
        )

    # Select a random pangram from the valid candidates
    chosen_pangram = random.choice(valid_pangram_candidates)
    final_letters = set(chosen_pangram)
    center_letter = random.choice(list(final_letters)) # Choose center from the actual letters

    end_time = time.time()
    print(f"--- [choose_letters PANGRAM-FIRST] Success! Chosen Pangram: '{chosen_pangram}'. Time elapsed: {end_time - start_time:.2f} seconds.")
    print(f"--- [choose_letters PANGRAM-FIRST] Final letters: {''.join(sorted(list(final_letters)))}, Center: {center_letter}")

    return final_letters, center_letter


def find_valid_words(db_path: str, letters: set[str], center_letter: str, active_list_types: list[str]):
    """
    Find all valid words from the database using the given letters, center letter,
    and active word lists.
    Returns a tuple containing:
        - set: valid_solutions (canonical words with potential macrons)
        - dict: normalized_solution_map {normalized_word: canonical_word}
    """
    valid_solutions = set()
    normalized_solution_map = {} # Initialize the map
    if not letters or not center_letter or not active_list_types:
        return valid_solutions, normalized_solution_map # Return empty set and map

    conn = _get_db_connection(db_path)
    if not conn:
        return valid_solutions, normalized_solution_map # Cannot proceed without DB connection

    cursor = conn.cursor()
    placeholders = ','.join('?' * len(active_list_types))
    # Query words containing the center letter from the active lists
    # We will filter based on the full letter set in Python
    sql_query = f"""
        SELECT word
        FROM words
        WHERE list_type IN ({placeholders})
          AND INSTR(LOWER(word), LOWER(?)) > 0
          AND LENGTH(word) >= ?
    """
    query_params = active_list_types + [center_letter, MIN_WORD_LENGTH]

    try:
        cursor.execute(sql_query, query_params)
        candidate_words = cursor.fetchall() # Fetch all potential words
        print(f"--- [DEBUG find_valid_words] SQL Query Candidates (Center: {center_letter}): {[row[0] for row in candidate_words[:20]]}") # Print first 20 candidates

        # Filter candidates in Python
        allowed_chars = set(letters) # Use a set for efficient lookup
        for row in candidate_words:
            word = row[0]
            # Check if all characters in the word are within the allowed letters
            if all(char in allowed_chars for char in word):
                valid_solutions.add(word)
                # Add to the normalization map
                normalized_form = normalize_word(word)
                # If collision, last one wins (simple approach)
                normalized_solution_map[normalized_form] = word

        print(f"Found {len(valid_solutions)} valid words from DB query and filtering.")
        print(f"Created normalization map with {len(normalized_solution_map)} entries.") # Log map size
        print(f"--- [DEBUG find_valid_words] Final Valid Solutions (First 50): {sorted(list(valid_solutions))[:50]}")
        return valid_solutions, normalized_solution_map # Return set and map

    except sqlite3.Error as e:
        print(f"Database error during valid word search: {e}")
        return set(), {} # Return empty set and map on error
    finally:
        if conn:
            conn.close()


def is_pangram(word: str, letters: set[str]) -> bool:
    """Check if a word is a pangram (uses all 7 letters)."""
    # Ensure letters is a set for correct comparison
    if not isinstance(letters, set):
         letters = set(letters)
    return len(word) >= 7 and set(word) == letters

def calculate_score(word: str, letters: set[str]) -> int:
    """Calculate the score for a given word."""
    if len(word) < MIN_WORD_LENGTH: # Should not happen if guess validation is correct
        return 0
    if len(word) == MIN_WORD_LENGTH:
        return 1
    elif is_pangram(word, letters):
        return len(word) + 7
    else: # Word is longer than min length but not a pangram
        return len(word)

def calculate_total_score(valid_solutions: set[str], letters: set[str]) -> int:
    """Calculate the maximum possible score for the puzzle."""
    # This function no longer needs DB access, just the results
    total_score = 0
    if not isinstance(valid_solutions, Iterable): # Basic check
        print("Warning: valid_solutions is not iterable in calculate_total_score")
        return 0
    for word in valid_solutions:
        total_score += calculate_score(word, letters)
    return total_score

def get_rank(score: int, total_possible_score: int) -> str:
    """Get the player's rank based on their score."""
    # Ensure total_possible_score is not zero to avoid division error
    if total_possible_score <= 0:
        # If score is also 0 or less, Beginner. If somehow score is positive, Genius?
        # Let's assume if total is 0, rank is Beginner unless score matches (impossible?)
         return RANKS[0] # Beginner

    # Handle the Queen Bee case explicitly if score matches total
    if score == total_possible_score:
        return RANKS[1.00] # Queen Bee

    percentage = score / total_possible_score
    current_rank = RANKS[0] # Default to Beginner
    # Iterate through sorted rank thresholds
    for threshold, rank_name in sorted(RANKS.items()):
        # Skip the Queen Bee threshold (1.00) here as it's handled above
        if threshold == 1.00:
            continue
        if percentage >= threshold:
            current_rank = rank_name
        else:
            # Since thresholds are sorted, we can stop once percentage is lower
            break
    return current_rank

# Removed the if __name__ == "__main__": block for terminal game 