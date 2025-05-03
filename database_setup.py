# database_setup.py
import os
import sys
import sqlite3 # Standard import should now work due to injection

WORD_LIST_FILES = {
    'common': 'words_common.txt',
    'nz': 'words_nz_only.txt',
    'au': 'words_au_only.txt',
    'tr': 'words_maori_only.txt'
}
MIN_WORD_LENGTH_SETUP = 4 # Use a distinct constant name during setup

# Define the directory where the processed word list files are expected
# PROCESSED_WORDLIST_DIR = os.path.join('wordlists', 'processed') # Old way

def init_db(db_path='word_database.db'): # Keep default for direct script running
    """Initializes the SQLite database and populates it with words."""
    print(f"Initializing database at: {db_path}")
    # Determine the directory containing the DB file (which is likely the project root)
    db_dir = os.path.dirname(db_path)
    # Assume wordlists directory is relative to the DB directory (project root)
    word_list_dir = os.path.join(db_dir, 'wordlists', 'processed') # <--- Construct path relative to db_path
    print(f"Looking for processed word lists in: {word_list_dir}") # Add log
    conn = None # Initialize conn to None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS words (
                word TEXT PRIMARY KEY,
                list_type TEXT NOT NULL CHECK(list_type IN ('common', 'nz', 'au', 'tr'))
            )
        ''')
        conn.commit()
        print("Table 'words' created or already exists.")

        # Populate table
        total_words_added = 0
        for list_type, filename in WORD_LIST_FILES.items():
            # Use the calculated absolute path to word lists
            filepath = os.path.join(word_list_dir, filename)
            words_in_file = 0
            words_added_from_file = 0
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip().lower()
                        if len(word) >= MIN_WORD_LENGTH_SETUP:
                            words_in_file += 1
                            try:
                                # INSERT OR IGNORE avoids errors if word already exists (PK constraint)
                                cursor.execute("INSERT OR IGNORE INTO words (word, list_type) VALUES (?, ?)", (word, list_type))
                                if cursor.rowcount > 0: # Check if a row was actually inserted
                                     words_added_from_file += 1
                            except sqlite3.Error as e:
                                print(f"Error inserting word '{word}' from {filename}: {e}")
                conn.commit() # Commit after each file
                print(f"Processed '{filename}' ({list_type}): Found {words_in_file} words (>= {MIN_WORD_LENGTH_SETUP} letters), Added {words_added_from_file} new words.")
                total_words_added += words_added_from_file
            except FileNotFoundError:
                print(f"Warning: Word list file not found at '{filepath}'. Skipping.")
            except Exception as e:
                print(f"Error reading file {filepath}: {e}")


        print(f"\nDatabase initialization complete. Total new words added: {total_words_added}")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    # Allows running this script directly, e.g., python database_setup.py
    # Assumes the script is run from the project root.
    # Define default DB path relative to *this* script if run directly
    script_dir = os.path.dirname(__file__)
    default_db_path = os.path.join(script_dir, 'word_database.db')
    init_db(default_db_path) 