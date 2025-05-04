# database_setup.py
import os
import sys
import sqlite3
import csv
import re

MIN_WORD_LENGTH_SETUP = 4 # Use a distinct constant name during setup
# Regex for validating English letters only during setup
VALID_CHARS_RE_SETUP = re.compile(r'^[a-z]+$')

# --- NEW: Define input CSV files ---
# IMPORTANT: Adjust CSV_WORD_COLUMN_INDEX if the word is not in the first column (index 0)
CSV_WORD_COLUMN_INDEX = 0
CSV_FILES = [
    'data_sources/ngsl_sfi_adj.csv', # Relative path - RENAMED
    'data_sources/SUP_lemmatized.csv' # Relative path
]
# Note: This script now only populates the 'common' list type.
# To add 'nz', 'au', 'tr' words, you would need separate source files
# and potentially modify this script or create a separate one to assign
# the correct list_type during insertion.

def init_db(db_path='word_database.db'): # Keep default for direct script running
    """Initializes the SQLite database and populates it with words from CSV files."""
    # Determine the directory where this script *runs from* during build (project root)
    project_root = os.getcwd() 

    print(f"Initializing database at: {db_path}")
    print(f"Executing from CWD: {project_root}") # Log CWD for confirmation

    conn = None
    try:
        # Ensure the directory for the database exists (e.g., api/)
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir): # Create DB directory if db_path includes one and it doesn't exist
             os.makedirs(db_dir, exist_ok=True)
             print(f"Ensured directory exists: {db_dir}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # --- NEW: Drop table first to ensure schema changes apply ---
        print("Dropping existing 'words' table (if it exists)...")
        cursor.execute("DROP TABLE IF EXISTS words;")
        conn.commit() # Commit the drop before recreating
        print("Table dropped.")
        # --- END NEW ---

        # Create table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS words (
                word TEXT PRIMARY KEY,
                list_type TEXT NOT NULL CHECK(list_type IN ('common', 'nz', 'au', 'tr', 'csw21'))
            )
        ''')
        conn.commit()
        print("Table 'words' created or already exists.")

        # Create indexes for faster lookups
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_word ON words (word);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_list_type ON words (list_type);")
        conn.commit()
        print("Indexes created or already exist.")

        # --- NEW: Clear existing data ---
        print("Clearing existing word data from 'words' table...")
        cursor.execute("DELETE FROM words;")
        conn.commit()
        print("Existing data cleared.")

        # --- NEW: Populate table from CSV files ---
        total_words_processed = 0
        total_words_added = 0
        list_type = 'common' # Assign all words from these sources as 'common'

        for filepath in CSV_FILES:
            print(f"Processing {filepath}...")
            words_in_file = 0
            words_added_from_file = 0
            try:
                # Attempt to read with utf-8, ignoring errors initially
                # Consider adding 'errors='replace'' or more robust handling if needed
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as csvfile:
                    reader = csv.reader(csvfile)
                    # Optional: Skip header row if present (check your CSVs)
                    # next(reader, None) # Uncomment this line if CSVs have a header
                    for row_num, row in enumerate(reader):
                        if not row: continue # Skip empty rows
                        try:
                            # --- Get word from the specified column ---
                            # ASSUMPTION: Word is in column CSV_WORD_COLUMN_INDEX (default 0)
                            word = row[CSV_WORD_COLUMN_INDEX].strip().lower()

                            # --- Validation ---
                            if len(word) >= MIN_WORD_LENGTH_SETUP and VALID_CHARS_RE_SETUP.match(word):
                                words_in_file += 1
                                # --- Insertion ---
                                # INSERT OR IGNORE avoids errors if word already exists (PK constraint)
                                cursor.execute("INSERT OR IGNORE INTO words (word, list_type) VALUES (?, ?)", (word, list_type))
                                if cursor.rowcount > 0: # Check if a row was actually inserted
                                    words_added_from_file += 1
                        except IndexError:
                            print(f"Warning: Row {row_num+1} in {filepath} shorter than expected (column index {CSV_WORD_COLUMN_INDEX}). Skipping row: {row}", file=sys.stderr)
                        except Exception as e:
                             print(f"Warning: Error processing row {row_num+1} in {filepath}. Skipping row. Error: {e} Row: {row}", file=sys.stderr)

                conn.commit() # Commit after processing each file
                print(f"  -> Processed {words_in_file} valid words, Added {words_added_from_file} new unique words as '{list_type}'.")
                total_words_processed += words_in_file
                total_words_added += words_added_from_file
            except FileNotFoundError:
                print(f"Error: Input CSV file not found at '{filepath}'. Skipping.", file=sys.stderr)
            except Exception as e:
                print(f"Error reading or processing file {filepath}: {e}", file=sys.stderr)

        print(f"\nDatabase population complete.")
        print(f"Total valid words processed across all files: {total_words_processed:,}")
        print(f"Total unique words added to the database: {total_words_added:,}")

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