# app.py
# Inject pysqlite3 before any other imports that might load sqlite3
import _inject_pysqlite # Direct import

import os
import sqlite3 # Now this should refer to the injected pysqlite3
import subprocess # Added for init-db check
import sys # Added for init-db check, and runtime debugging
import time # Added for timing
from flask import Flask, render_template, request, session, jsonify, redirect, url_for, g, abort # Import abort
import requests
import click
from flask.cli import with_appcontext
import math # <-- ADDED IMPORT

# Import game logic from spelling_bee module
import spelling_bee # Direct import
# Import database setup function
import database_setup # Direct import
# Import the normalization function
# from spelling_bee import normalize_word # Can use spelling_bee.normalize_word

# --- Re-calculate paths needed by the app --- 
api_dir = os.path.abspath(os.path.dirname(__file__))
basedir = os.path.dirname(api_dir) # Project root
# DATABASE = os.path.join(basedir, 'word_database.db') # Original incorrect path used at runtime
# DATABASE_RUNTIME_PATH = "/var/task/word_database.db" # Absolute path in Vercel runtime
# Let's try constructing the path relative to the runtime script location first
DATABASE_PATH = os.path.join(basedir, 'word_database.db') # Use project root

# --- Flask App Definition (Should happen AFTER DB check/init) ---
print(f"--- [RUNTIME] api/index.py START (PID: {os.getpid()}) ---")
print(f"--- [RUNTIME] Python version: {sys.version}")
print(f"--- [RUNTIME] Expecting database relative to script at: {DATABASE_PATH}")

# --- Your Flask App Definition ---
# Explicitly set template and static folder paths relative to the project root
app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Read secret key from environment variable, with a fallback for local dev
# IMPORTANT: Set a strong SECRET_KEY environment variable in production (Vercel settings)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-replace-in-prod-or-use-env')

# --- Flask CLI Command for DB Initialization ---
@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    try:
        # Use the project root directory (calculated earlier as 'basedir')
        # Ensure 'basedir' is defined globally or recalculated if needed
        # If basedir is not accessible here, recalculate: 
        # api_dir_local = os.path.abspath(os.path.dirname(__file__))
        # basedir_local = os.path.dirname(api_dir_local)
        target_db_path = os.path.join(basedir, 'word_database.db') # Use project root

        # Ensure the *project root* directory exists (it definitely should)
        # os.makedirs(basedir, exist_ok=True) # Probably unnecessary
        
        print(f"--- [Flask init-db command] Target DB path: {target_db_path}") # Log the path being used

        # Pass the CORRECT path (project root) to the setup function
        database_setup.init_db(target_db_path)
        click.echo('Initialized the database.')
    except Exception as e:
        click.echo(f'Error initializing database: {e}')
        # It might be helpful to log the full exception here for debugging Vercel
        import traceback
        traceback.print_exc()

app.cli.add_command(init_db_command)

# --- Helper Function to Get Active List Types ---
def get_active_list_types_from_session():
    """Gets the list of active word list types based on session settings."""
    active_types = ['common'] # Common list is always active
    if session.get('use_nz', False):
        active_types.append('nz')
    if session.get('use_au', False):
        active_types.append('au')
    if session.get('use_tr', False):
        active_types.append('tr')
    print(f"Active list types from session: {active_types}") # Debug log
    return active_types

# --- Helper Function for New Game Setup ---
def setup_new_game(db_path, active_list_types):
    """Sets up a new game by choosing letters and finding solutions."""
    try:
        print(f"--- [setup_new_game] Starting setup with DB: {db_path}, Lists: {active_list_types}")
        # 1. Choose letters (pangram-first approach)
        letters_set, center_letter = spelling_bee.choose_letters(db_path, active_list_types)
        print(f"--- [setup_new_game] Letters chosen: {letters_set}, Center: {center_letter}")

        # 2. Find valid words and create normalization map
        solutions, normalized_solution_map = spelling_bee.find_valid_words(db_path, letters_set, center_letter, active_list_types)
        print(f"--- [setup_new_game] Solutions found: {len(solutions)}, Map size: {len(normalized_solution_map)}")

        # 3. Calculate total score
        total_score = spelling_bee.calculate_total_score(solutions, letters_set)
        print(f"--- [setup_new_game] Total score calculated: {total_score}")

        return letters_set, center_letter, solutions, normalized_solution_map, total_score

    except ConnectionError as e:
        print(f"!!! Database connection error during game setup using path: {db_path}. Error: {e}")
        # Re-raise or handle appropriately - perhaps raise a custom exception?
        raise RuntimeError(f"Could not connect to the word database: {e}") from e
    except RuntimeError as e:
        print(f"!!! Error generating puzzle: {e}")
        # Re-raise the specific error
        raise e
    except Exception as e:
        print(f"!!! Unexpected error during game setup: {e}")
        # Log the full traceback for unexpected errors
        import traceback
        traceback.print_exc()
        raise RuntimeError(f"An unexpected error occurred setting up the game: {e}") from e

# --- Helper Function to Calculate Rank ---
def calculate_rank(score, total_score):
    """Calculates the player's rank based on score.
    (Ensure this matches spelling_bee.get_rank if kept there)
    """
    if total_score == 0: # Avoid division by zero
        return "Beginner"
    percentage = (score / total_score) * 100
    # Rank thresholds (adjust as needed)
    if percentage >= 100: return "Queen Bee!"
    if percentage >= 80: return "Genius"
    if percentage >= 60: return "Amazing"
    if percentage >= 40: return "Great"
    if percentage >= 25: return "Nice"
    if percentage >= 15: return "Solid"
    if percentage >= 8: return "Good"
    if percentage >= 3: return "Moving Up"
    return "Beginner"

# --- Flask Routes ---

@app.before_request
def check_db():
    print(f"--- [RUNTIME] before_request: Entering check_db for {request.path}")
    # --- BEGIN DEBUG: List /var/task contents ---
    runtime_task_dir = '/var/task'
    print(f"--- [RUNTIME DEBUG] Listing contents of {runtime_task_dir}...")
    try:
        runtime_dir_listing = os.listdir(runtime_task_dir)
        print(f"--- [RUNTIME DEBUG] Contents of {runtime_task_dir}: {sorted(runtime_dir_listing)}")
    except Exception as e:
        print(f"--- [RUNTIME DEBUG] ERROR listing {runtime_task_dir}: {e}")
    # --- END DEBUG ---

    # Runtime check using the constructed absolute path
    print(f"--- [RUNTIME] Checking for DB at constructed path: {DATABASE_PATH}")
    if not os.path.exists(DATABASE_PATH):
         print(f"!!! RUNTIME CRITICAL ERROR: Database NOT FOUND at {DATABASE_PATH} !!!")
         # Abort the request cleanly
         abort(500, description=f"Internal Server Error: Database unavailable at {DATABASE_PATH}")
    else:
         print(f"--- [RUNTIME] Database FOUND at {DATABASE_PATH}")

@app.route('/')
def index():
    print("--- [RUNTIME] Request received for / route ---")
    # Ensure DB exists before proceeding
    check_db()

    active_list_types = session.get('active_list_types', ['common'])
    print(f"Active list types from session: {active_list_types}")

    # Check if game state exists in session
    if 'letters' not in session or 'center_letter' not in session or 'solutions' not in session:
        print("No letters found in session, starting new game setup...")
        # Start new game if no state found
        letters, center_letter, solutions, normalized_solution_map, total_score = setup_new_game(DATABASE_PATH, active_list_types)
        session['letters'] = list(letters) # Store as list
        session['center_letter'] = center_letter
        session['solutions'] = list(solutions) # Store as list for JSON serialization
        session['normalized_solution_map'] = normalized_solution_map # Store the map
        session['found_words'] = []
        session['score'] = 0
        session['total_score'] = total_score
        print(f"New game started. Letters: {session['letters']}, Center: {center_letter}, Solutions: {len(solutions)}, Map Size: {len(normalized_solution_map)}, Total Score: {total_score}")

    # Retrieve game state from session
    center_letter = session['center_letter']
    all_letters = sorted(session['letters']) # Ensure consistent order for display
    outer_letters = [l for l in all_letters if l != center_letter]
    solutions = set(session['solutions']) # Convert back to set for efficient lookups later if needed
    found_words = session['found_words']
    score = session['score']
    total_score = session.get('total_score', 0) # Get total score

    # --- Calculate Outer Circle Positions --- RE-ENABLED for hexagonal layout
    circle_radius = 25 # Keep for reference/potential use
    center_pos_x = 75 # Must match template viewBox center
    center_pos_y = 75
    outer_ring_radius = 50 # Distance for positioning outer letters
    angles = [math.pi * -0.5, math.pi * -0.1667, math.pi * 0.1667, math.pi * 0.5, math.pi * 0.8333, math.pi * 1.1667] # Approx angles: -90, -30, 30, 90, 150, 210 degrees
    outer_positions = []
    for i in range(len(outer_letters)): # Max 6 outer letters
        if i < len(angles):
            angle = angles[i]
            pos_x = center_pos_x + outer_ring_radius * math.cos(angle)
            pos_y = center_pos_y + outer_ring_radius * math.sin(angle)
            outer_positions.append({'x': round(pos_x, 2), 'y': round(pos_y, 2)})
        else: # Should not happen with 7 letters, but handle defensively
            outer_positions.append({'x': center_pos_x, 'y': center_pos_y}) # Default to center
    print(f"--- [DEBUG index route] Calculated outer_positions: {outer_positions}")
    # --- Calculate Outer Circle Positions --- RE-ENABLED

    rank = calculate_rank(score, total_score)
    message = session.pop('message', '') # Get and clear flash message

    # Optional list usage flags
    use_nz = 'nz' in active_list_types
    use_au = 'au' in active_list_types
    use_tr = 'tr' in active_list_types

    print(f"--- [DEBUG index route] Center Letter: {center_letter}")
    print(f"--- [DEBUG index route] Display Letters (sorted from session): {all_letters}")
    print(f"--- [DEBUG index route] Outer Letters: {outer_letters}")

    # Render the main game page
    return render_template('index.html',
                           letters=all_letters, # Pass sorted letters
                           center_letter=center_letter,
                           outer_letters=outer_letters,
                           outer_positions=outer_positions,
                           score=score,
                           rank=rank,
                           total_words=len(solutions),
                           found_words=sorted(list(set(found_words))), # Pass unique sorted list
                           message=message,
                           use_nz=use_nz,
                           use_au=use_au,
                           use_tr=use_tr)

@app.route('/guess', methods=['POST'])
def handle_guess():
    if 'letters' not in session:
        return jsonify({'status': 'error', 'message': 'Game not started. Please refresh.'}), 400

    guess = request.json.get('guess', '').strip().lower()
    # Retrieve game state from session
    letters_set = set(session['letters'])
    center_letter = session['center_letter']
    # Retrieve the normalization map
    solution_map = session.get('solution_map', {}) # Get map from session
    # Get canonical found words (potentially with macrons)
    found_words_set = set(session['found_words'])
    current_score = session['current_score']
    total_possible_score = session['total_score']

    message = ""
    status = "invalid" # Default status
    score_increase = 0
    is_pangram_found = False

    # Normalize the user's guess
    normalized_guess = spelling_bee.normalize_word(guess)

    # --- Validation Logic using Normalization Map --- START
    if len(guess) < spelling_bee.MIN_WORD_LENGTH:
        message = f"Too short! Min {spelling_bee.MIN_WORD_LENGTH} letters."
    # Check original guess for center letter and allowed letters
    # This prevents accepting a normalized word if the original input was invalid
    elif center_letter not in guess:
        message = f"Missing center letter '{center_letter.upper()}'!"
    elif not all(char in letters_set for char in guess):
         # Need to check the original guess letters against the puzzle
         # However, what if the normalized guess matches but uses different letters?
         # E.g. letters = {a, b, c, d, e, f, ā}, center=a. Solution: 'abcā'. User types 'abca'. Normalizes ok.
         # Let's refine: Check the *normalized* guess chars against the *normalized* puzzle letters
         normalized_puzzle_letters = {normalize_word(l) for l in letters_set}
         # Check if all chars in the *original* guess belong to the *set* of letters (incl macrons)
         # This seems the most intuitive check from user perspective
         if not all(char in letters_set for char in guess):
            message = "Uses letters not in the puzzle!"
         else:
            # Now check if the normalized guess exists in our map
            canonical_word = solution_map.get(normalized_guess)

            if canonical_word:
                if canonical_word in found_words_set:
                    message = "Already found!"
                    status = "invalid" # Keep status as invalid even if found
                else:
                    # VALID GUESS - Use canonical word from now on
                    score_increase = spelling_bee.calculate_score(canonical_word, letters_set)
                    current_score += score_increase
                    found_words_set.add(canonical_word) # Add canonical word
                    is_pangram_found = spelling_bee.is_pangram(canonical_word, letters_set)

                    # Update session
                    session['current_score'] = current_score
                    session['found_words'] = sorted(list(found_words_set))
                    session.modified = True

                    message = f"Good! +{score_increase} points."
                    if is_pangram_found:
                        message += " Pangram!"
                    status = "valid"

                    if current_score == total_possible_score:
                        message = "Queen Bee! You found all the words!"
                        status = "finished"
            else:
                # Normalized guess not found in map
                message = "Not in word list."
                status = "invalid"
    else:
        # Passed initial checks, now check map
        canonical_word = solution_map.get(normalized_guess)
        if canonical_word:
            if canonical_word in found_words_set:
                message = "Already found!"
                status = "invalid"
            else:
                # VALID GUESS - Use canonical word
                score_increase = spelling_bee.calculate_score(canonical_word, letters_set)
                current_score += score_increase
                found_words_set.add(canonical_word)
                is_pangram_found = spelling_bee.is_pangram(canonical_word, letters_set)
                session['current_score'] = current_score
                session['found_words'] = sorted(list(found_words_set))
                session.modified = True
                message = f"Good! +{score_increase} points."
                if is_pangram_found:
                    message += " Pangram!"
                status = "valid"
                if current_score == total_possible_score:
                    message = "Queen Bee! You found all the words!"
                    status = "finished"
        else:
            message = "Not in word list."
            status = "invalid"

    # --- Validation Logic --- END

    # Use refactored get_rank
    rank = spelling_bee.get_rank(current_score, total_possible_score)

    return jsonify({
        'status': status,
        'message': message,
        'score': current_score,
        'rank': rank,
        'found_words': sorted(list(found_words_set)), # Return sorted list
        'found_words_count': len(found_words_set),
        'pangram': is_pangram_found
    })

@app.route('/update_settings', methods=['POST'])
def update_settings():
    """Updates word list preferences in the session and starts a new game."""
    print("Updating settings...")
    session['use_nz'] = 'use_nz' in request.form
    session['use_au'] = 'use_au' in request.form
    session['use_tr'] = 'use_tr' in request.form
    print(f"New settings: NZ={session['use_nz']}, AU={session['use_au']}, TR={session['use_tr']}")

    # Clear existing game state to force a new puzzle generation on redirect
    session.pop('letters', None)
    session.pop('center_letter', None)
    session.pop('valid_solutions', None)
    session.pop('total_score', None)
    session.pop('found_words', None)
    session.pop('current_score', None)
    session['message'] = "Word list settings updated. New game started!" # Flash message
    session.modified = True

    return redirect(url_for('index')) # Redirect back to index to generate new game


@app.route('/new_game')
def new_game():
    """Clears the session to start a new game with current list settings."""
    # Clear only game-specific keys, keep list preferences
    session.pop('letters', None)
    session.pop('center_letter', None)
    session.pop('valid_solutions', None)
    session.pop('total_score', None)
    session.pop('found_words', None)
    session.pop('current_score', None)
    session['message'] = "New game started!" # Flash message
    session.modified = True
    print("Starting new game (keeping list settings), session cleared.") # Server log
    return redirect(url_for('index'))

# --- Definition Route (Remains largely unchanged) ---
@app.route('/definition/<word>')
def get_definition(word):
    """Fetches a definition from an external API."""
    api_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    definition = "Definition not found."
    try:
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list):
            meanings = data[0].get('meanings', [])
            if meanings:
                definitions = meanings[0].get('definitions', [])
                if definitions:
                    definition = definitions[0].get('definition', definition)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching definition for '{word}': {e}")
    except Exception as e:
        print(f"Error processing definition response for '{word}': {e}")

    return jsonify({'definition': definition})


# --- Main Execution ---
if __name__ == "__main__":
    # Check if DB exists on startup (optional, but helpful)
    # This check will likely use the path relative to where the script is run locally
    local_dev_db_path = os.path.join(os.path.dirname(__file__), 'word_database.db') # Path for local dev check
    if not os.path.exists(local_dev_db_path):
        print(f"Warning: Local database file '{local_dev_db_path}' not found.")
        print("Please run 'flask init-db' in your terminal to create and populate it.")
        
    app.run(debug=True, port=5001) 