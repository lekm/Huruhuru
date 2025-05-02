import random
import string
from collections.abc import Iterable
import sys
import sqlite3 # Standard import should now work due to injection

MIN_WORD_LENGTH = 4

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
    Choose 7 unique letters from the alphabet, ensuring at least one pangram
    exists in the database for the active word lists.
    """
    alphabet = list(string.ascii_lowercase)
    conn = _get_db_connection(db_path)
    if not conn:
        raise ConnectionError(f"Could not connect to database at {db_path}")

    cursor = conn.cursor()
    # Prepare placeholders for SQL IN clause
    placeholders = ','.join('?' * len(active_list_types))
    sql_query = f"SELECT word FROM words WHERE list_type IN ({placeholders}) AND LENGTH(word) >= 7"

    try:
        # Fetch potential pangram candidates (length >= 7) from active lists
        cursor.execute(sql_query, active_list_types)
        # Fetch all candidates into memory - necessary tradeoff for checking set equality easily
        candidate_words = {row[0] for row in cursor.fetchall()}
        if not candidate_words:
             print("Warning: No words of length 7 or more found in the active lists. Cannot guarantee a pangram.")
             # Fallback? Or raise error? For now, let's proceed but log warning.
             # We'll still pick letters, but find_valid_words might find 0 solutions.

    except sqlite3.Error as e:
        print(f"Database error during pangram candidate search: {e}")
        conn.close()
        raise # Re-raise the exception after closing connection

    conn.close() # Close connection after fetching candidates

    print(f"Checking potential pangrams from {len(candidate_words)} candidates...")
    attempts = 0
    max_attempts = 1000 # Prevent infinite loop if alphabet is small or lists restrictive

    while attempts < max_attempts:
        attempts += 1
        random.shuffle(alphabet)
        letters = set(alphabet[:7])
        center_letter = random.choice(list(letters))

        # Check if any candidate word forms a pangram with these letters
        found_pangram = False
        for word in candidate_words:
            # Check if the word uses *exactly* the 7 chosen letters
            if set(word) == letters:
                 # Double check it uses the center letter (pangrams must)
                 # Although set(word)==letters implies center_letter is in word if it's in letters
                if center_letter in word:
                    found_pangram = True
                    break # Found one, no need to check others

        if found_pangram:
            print(f"Found suitable letters after {attempts} attempts.")
            print(f"Chosen letters (Center *): {' '.join(sorted(list(letters))).replace(center_letter, f'{center_letter}*')}")
            return letters, center_letter
        # else:
            # print(f"Attempt {attempts}: No pangram found for {''.join(sorted(list(letters)))}, retrying...")


    # If loop finishes without finding letters
    raise RuntimeError(f"Could not find a set of 7 letters with a guaranteed pangram after {max_attempts} attempts. Check word lists and active types: {active_list_types}")


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
          AND INSTR(word, ?) > 0
          AND LENGTH(word) >= ?
    """
    query_params = active_list_types + [center_letter, MIN_WORD_LENGTH]

    try:
        cursor.execute(sql_query, query_params)
        candidate_words = cursor.fetchall() # Fetch all potential words

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