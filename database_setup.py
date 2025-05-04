# database_setup.py
import os
import sys
import sqlite3
import csv
import re

MIN_WORD_LENGTH_SETUP = 4 # Use a distinct constant name during setup
# Regex for validating letters, including common macrons
VALID_CHARS_RE_SETUP = re.compile(r'^[a-zāēīōū]+$')

# --- NEW: Define input sources by list type ---
CSV_WORD_COLUMN_INDEX = 0
# Map list_type keys to a list of source file paths
SOURCE_FILES_BY_TYPE = {
    'csw21': ['data_sources/csw21_filtered.txt'], # Use the filtered CSW21 list
    'te_reo': ['data_sources/tereo_cleaned.csv'], # Uses cleaned Te Reo data
    'nz_slang': ['data_sources/nzslang_cleaned.csv'] # Use the cleaned NZ Slang data
}
# < -----------------------------------------

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
        print("Dropping existing 'words' and 'definitions' tables (if they exist)...")
        cursor.execute("DROP TABLE IF EXISTS definitions;")
        cursor.execute("DROP TABLE IF EXISTS words;")
        conn.commit() # Commit the drop before recreating
        print("Tables dropped.")
        # --- END NEW ---

        # Create table words
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS words (
                word_id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                list_type TEXT NOT NULL CHECK(list_type IN ('csw21', 'te_reo', 'nz_slang')),
                UNIQUE(word, list_type) -- Prevent duplicate word/list combos
            )
        ''')
        conn.commit()
        print("Table 'words' created or already exists with new schema.")
        
        # Create table definitions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS definitions (
                definition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id INTEGER NOT NULL,
                definition_text TEXT NOT NULL,
                FOREIGN KEY(word_id) REFERENCES words(word_id) ON DELETE CASCADE
            )
        ''')
        conn.commit()
        print("Table 'definitions' created or already exists.")

        # Create indexes for faster lookups
        print("Creating indexes...")
        # Index on word_id is created automatically for PRIMARY KEY
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_word_text ON words (word);") # Index on the word text itself
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_list_type ON words (list_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_definition_word_id ON definitions (word_id);") # Index for FK lookups
        conn.commit()
        print("Indexes created or already exist.")

        # --- Clear existing data from both tables ---
        print("Clearing existing word data from 'words' and 'definitions' tables...")
        cursor.execute("DELETE FROM definitions;") # Clear child table first
        cursor.execute("DELETE FROM words;")
        conn.commit()
        print("Existing data cleared.")

        # --- Populate table from SOURCE_FILES_BY_TYPE ---
        total_words_processed = 0
        total_words_added = 0

        for list_type, filepaths in SOURCE_FILES_BY_TYPE.items():
            if not isinstance(filepaths, list):
                filepaths = [filepaths]

            for filepath in filepaths:
                print(f"Processing {filepath} for list type '{list_type}'...")
                words_in_file = 0
                words_added_from_file = 0
                try:
                    # Simple check for file extension - adjust logic if needed
                    is_csv = filepath.lower().endswith('.csv')

                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as infile:
                        rows_to_process = None # Initialize
                        if is_csv:
                            # Use csv reader with tab delimiter
                            reader = csv.reader(infile, delimiter='\t')
                            # Skip header row if necessary - assuming tereo_cleaned.csv has no header now
                            # next(reader, None) 
                            rows_to_process = enumerate(reader)
                        else: # Assume TXT file (one word per line)
                            lines = (line.strip() for line in infile)
                            valid_lines = filter(None, lines)
                            # Wrap each line in a list containing the word and None for definition
                            rows_to_process = enumerate([[line, None] for line in valid_lines])

                        # Process rows uniformly
                        rows_iterated_count = 0 # Add counter
                        for row_num, row in rows_to_process:
                            rows_iterated_count += 1 # Increment counter
                            if not row or len(row) < 1: continue # Skip empty/malformed rows
                            try:
                                word = row[0].strip().lower()
                                # Definition is already set to None for TXT or is row[1] for CSV
                                definition = row[1].strip() if is_csv and len(row) > 1 and row[1] else None
                                
                                # Basic quote handling for CSV definitions
                                if definition and definition.startswith('"') and definition.endswith('"'):
                                    definition = definition[1:-1].replace('""', '"')
                                    
                                # Validate word and insert/update definition
                                if len(word) >= MIN_WORD_LENGTH_SETUP and VALID_CHARS_RE_SETUP.match(word):
                                    words_in_file += 1
                                    current_word_id = None # Reset for each word
                                    
                                    # 1. Check if word/list_type combo already exists
                                    cursor.execute("SELECT word_id FROM words WHERE word = ? AND list_type = ?", (word, list_type))
                                    result = cursor.fetchone()
                                    
                                    if result:
                                        # Word exists, use its ID
                                        current_word_id = result[0]
                                    else:
                                        # Word doesn't exist for this list_type, insert it
                                        cursor.execute("INSERT INTO words (word, list_type) VALUES (?, ?)", 
                                                       (word, list_type))
                                        if cursor.rowcount > 0:
                                            words_added_from_file += 1
                                            current_word_id = cursor.lastrowid # Get ID of the newly inserted word
                                        else:
                                            # Should not happen if SELECT failed and INSERT failed, but handle defensively
                                            print(f"Error: Failed to insert new word AND could not find existing word: {word}", file=sys.stderr)
                                            continue # Skip this word
                                            
                                    # 2. Insert definition if it exists and we have a valid word_id
                                    if definition and current_word_id:
                                        cursor.execute("INSERT INTO definitions (word_id, definition_text) VALUES (?, ?)",
                                                       (current_word_id, definition))
                                        
                            except IndexError:
                                print(f"Warning: Row {row_num+1} in {filepath} seems empty or malformed. Skipping row: {row}", file=sys.stderr)
                            except Exception as e:
                                print(f"Warning: Error processing row {row_num+1} in {filepath}. Skipping row. Error: {e} Row: {row}", file=sys.stderr)

                    # --- Remove DEBUGGING PRINT for iterated count ---
                    # if list_type == 'te_reo':
                    #      print(f"  -> [DEBUG] Total rows iterated for {filepath}: {rows_iterated_count}")
                    # --- End print removal ---
                    conn.commit() # Commit after each file
                    print(f"  -> Processed {words_in_file} valid words, Added {words_added_from_file} new unique words as '{list_type}'.")
                    total_words_processed += words_in_file
                    total_words_added += words_added_from_file
                except FileNotFoundError:
                    print(f"Error: Input file not found at '{filepath}'. Skipping.", file=sys.stderr)
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