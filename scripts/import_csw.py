import sqlite3
import os
import time

# --- Configuration ---
# Assuming the script is run from the project root or 'scripts' directory
# Calculate paths relative to the script's location
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir) # Go up one level from 'scripts'

DB_PATH = os.path.join(project_root, 'word_database.db')
WORDLIST_PATH = os.path.join(project_root, 'data_sources', 'csw21_filtered.txt')
LIST_TYPE_TAG = 'csw21' # The tag to assign in the database

# --- Main Import Function ---
def import_wordlist(db_path, wordlist_path, list_type):
    """Imports words from a text file into the database."""
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return
    if not os.path.exists(wordlist_path):
        print(f"Error: Wordlist file not found at {wordlist_path}")
        return

    conn = None
    inserted_count = 0
    skipped_count = 0
    start_time = time.time()

    try:
        print(f"Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"Reading words from: {wordlist_path}")
        with open(wordlist_path, 'r', encoding='utf-8') as f:
            words_to_insert = []
            for line in f:
                word = line.strip().lower() # Normalize to lowercase
                if word: # Ensure it's not an empty line
                    # Check if the word already exists for this list_type to avoid duplicates
                    # This check adds overhead but ensures idempotency if run multiple times
                    cursor.execute("SELECT 1 FROM words WHERE word = ? AND list_type = ?", (word, list_type))
                    if cursor.fetchone():
                        skipped_count += 1
                    else:
                        words_to_insert.append((word, list_type))
                        inserted_count += 1
                
                # Optional: Insert in batches for very large files
                # if len(words_to_insert) >= 1000:
                #     cursor.executemany("INSERT INTO words (word, list_type) VALUES (?, ?)", words_to_insert)
                #     words_to_insert = []
                #     print(f"Inserted batch, total: {inserted_count}")

        # Insert any remaining words
        if words_to_insert:
            print(f"Inserting {len(words_to_insert)} words...")
            cursor.executemany("INSERT INTO words (word, list_type) VALUES (?, ?)", words_to_insert)

        conn.commit()
        print("Database commit successful.")

    except sqlite3.Error as e:
        print(f"Database error during import: {e}")
        if conn:
            conn.rollback() # Rollback changes on error
    except IOError as e:
        print(f"File reading error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

    end_time = time.time()
    print("--- Import Summary ---")
    print(f"Words processed: {inserted_count + skipped_count}")
    print(f"New words inserted: {inserted_count}")
    print(f"Words skipped (already existed for '{list_type}'): {skipped_count}")
    print(f"Duration: {end_time - start_time:.2f} seconds")

# --- Script Execution ---
if __name__ == "__main__":
    print(f"Starting import of '{LIST_TYPE_TAG}' words...")
    import_wordlist(DB_PATH, WORDLIST_PATH, LIST_TYPE_TAG)
    print("Import process finished.") 