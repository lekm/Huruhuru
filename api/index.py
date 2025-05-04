# app.py
# Inject pysqlite3 before any other imports that might load sqlite3
import _inject_pysqlite # Direct import -- Temporarily commented out for local init-db

import os
import sqlite3 # Now this should refer to the injected pysqlite3
import subprocess # Added for init-db check
import sys # Added for init-db check, and runtime debugging
import time # Added for timing
from flask import Flask, render_template, request, session, jsonify, redirect, url_for, g, abort, current_app # Added current_app and logging
import requests
import click
from flask.cli import with_appcontext
import math # <-- ADDED IMPORT
import logging # For better error logging

# Import game logic from spelling_bee module
import spelling_bee # Direct import
# Import database setup function
import database_setup # Direct import
# Import the normalization function
# from spelling_bee import normalize_word # Can use spelling_bee.normalize_word

# --- Add project root to sys.path --- START
api_dir_for_path = os.path.dirname(os.path.abspath(__file__))
project_root_for_path = os.path.dirname(api_dir_for_path)
if project_root_for_path not in sys.path:
    sys.path.insert(0, project_root_for_path)
# --- Add project root to sys.path --- END

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

# Configure logging
logging.basicConfig(level=logging.INFO) # Log info and above
# Adjust Flask logger level if needed
app.logger.setLevel(logging.INFO)

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

# --- Helper Function for New Game Setup (MODIFIED) ---
def setup_new_game(db_path, active_list_types):
    """Sets up a new game, updates session, returns success status."""
    # Ensure active_list_types is valid
    if not active_list_types or not isinstance(active_list_types, list):
         app.logger.error(f"Invalid active_list_types provided to setup_new_game: {active_list_types}")
         return False # Indicate failure

    try:
        app.logger.info(f"--- [setup_new_game] Starting setup with DB: {db_path}, Lists: {active_list_types}")
        # 1. Choose letters (pangram-first approach) using selected lists
        letters_set, center_letter = spelling_bee.choose_letters(db_path, active_list_types)
        app.logger.info(f"--- [setup_new_game] Letters chosen: {letters_set}, Center: {center_letter}")

        # Sort letters for consistent display order
        all_letters_sorted = sorted(list(letters_set))
        outer_letters_alpha = [l for l in all_letters_sorted if l != center_letter]

        # 2. Find valid words and create normalization map
        solutions, normalized_solution_map = spelling_bee.find_valid_words(db_path, letters_set, center_letter, active_list_types)
        app.logger.info(f"--- [setup_new_game] Solutions found: {len(solutions)}, Map size: {len(normalized_solution_map)}")

        # 3. Calculate total score
        total_score = spelling_bee.calculate_total_score(solutions, letters_set)
        app.logger.info(f"--- [setup_new_game] Total score calculated: {total_score}")

        # --- Calculate Coordinates and Ordered Outer Letters ---        
        viewBox_center_x = 75
        viewBox_center_y = 75
        center_radius = 25
        outer_ring_end_radius = 65
        letter_radius = center_radius + (outer_ring_end_radius - center_radius) / 2
        num_segments = len(outer_letters_alpha) 

        outer_segments_data = []
        ordered_outer_letters_for_js = [] 

        if num_segments > 0:
            segment_angle_deg = 360 / num_segments
            segment_angle_rad = math.radians(segment_angle_deg)
            start_angle_offset_rad = math.radians(-90 - (segment_angle_deg / 2)) 

            letters_to_assign = list(outer_letters_alpha) 

            for i in range(num_segments):
                current_angle_rad = start_angle_offset_rad + i * segment_angle_rad
                next_angle_rad = current_angle_rad + segment_angle_rad
                letter_angle_rad = current_angle_rad + (segment_angle_rad / 2)

                letter_x = letter_radius * math.cos(letter_angle_rad)
                letter_y = letter_radius * math.sin(letter_angle_rad)

                assigned_letter = letters_to_assign[i]
                ordered_outer_letters_for_js.append(assigned_letter.upper())

                 # Calculate segment path 
                start_cx = center_radius * math.cos(current_angle_rad)
                start_cy = center_radius * math.sin(current_angle_rad)
                start_ox = outer_ring_end_radius * math.cos(current_angle_rad)
                start_oy = outer_ring_end_radius * math.sin(current_angle_rad)
                end_ox = outer_ring_end_radius * math.cos(next_angle_rad)
                end_oy = outer_ring_end_radius * math.sin(next_angle_rad)
                end_cx = center_radius * math.cos(next_angle_rad)
                end_cy = center_radius * math.sin(next_angle_rad)
                large_arc_flag = 0
                sweep_flag_outer = 1
                sweep_flag_inner = 0
                fmt = ".2f"
                path_d = (
                    f"M {start_cx:{fmt}} {start_cy:{fmt}} "
                    f"L {start_ox:{fmt}} {start_oy:{fmt}} "
                    f"A {outer_ring_end_radius:{fmt}} {outer_ring_end_radius:{fmt}} 0 {large_arc_flag} {sweep_flag_outer} {end_ox:{fmt}} {end_oy:{fmt}} "
                    f"L {end_cx:{fmt}} {end_cy:{fmt}} "
                    f"A {center_radius:{fmt}} {center_radius:{fmt}} 0 {large_arc_flag} {sweep_flag_inner} {start_cx:{fmt}} {start_cy:{fmt}} "
                    f"Z"
                )
                outer_segments_data.append({
                    'letter': assigned_letter.upper(),
                    'x': round(letter_x, 2),
                    'y': round(letter_y, 2),
                    'segment_path': path_d
                })
        # --- End Coordinate Calculation ---

        # 4. Update Session with all necessary game state
        session['letters'] = all_letters_sorted # Store sorted list
        session['center_letter'] = center_letter
        session['outer_letters_ordered'] = ordered_outer_letters_for_js # Store ordered outer letters specifically for JS animation
        session['outer_segments_data'] = outer_segments_data # Store data needed by template render
        session['solutions'] = list(solutions) # Store as list for JSON serialization
        session['normalized_solution_map'] = normalized_solution_map # Store the map
        session['found_words'] = []
        session['score'] = 0
        session['total_score'] = total_score
        # Ensure active_list_types is also in session, but it should be set before calling this function
        session.modified = True # Ensure session is saved

        app.logger.info(f"--- [setup_new_game] Success! State updated in session.")
        return True # Indicate success

    except (ConnectionError, RuntimeError, ValueError, Exception) as e: # Catch broader errors
        app.logger.error(f"!!! Error during game setup: {e}", exc_info=True) # Log full traceback
        return False # Indicate failure

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
    app.logger.info("--- Request received for / route ---")
    # DB Check happens via @app.before_request

    # Try to load existing game state from session
    center_letter = session.get('center_letter')
    outer_segments_data = session.get('outer_segments_data') # Get pre-calculated data if exists
    score = session.get('score', 0)
    total_score = session.get('total_score', 0) # Needed for rank calc
    # Calculate rank based on loaded score/total_score
    rank = calculate_rank(score, total_score)
    found_words = session.get('found_words', [])
    message = session.pop('message', '') # Get and clear flash message

    active_list_types = session.get('active_list_types', ['common'])
    use_nz = 'nz' in active_list_types
    use_au = 'au' in active_list_types
    use_tr = 'tr' in active_list_types

    # If there's no game in session, these will be None/empty
    app.logger.info(f"Rendering index page. Game in session: {bool(center_letter)}")
    app.logger.debug(f"Center: {center_letter}, Segments Data: {bool(outer_segments_data)}")

    # Need to ensure these parameters are always passed, even if None/empty
    viewBox_center_x = 75
    viewBox_center_y = 75
    center_radius = 25

    # Render the main game page
    return render_template('index.html',
                           center_letter=center_letter, # Can be None
                           outer_segments_data=outer_segments_data or [], # Pass empty list if None
                           score=score,
                           rank=rank,
                           total_words=len(session.get('solutions', [])), # Calculate from session solutions
                           found_words=sorted(list(set(found_words))),
                           message=message,
                           use_nz=use_nz,
                           use_au=use_au,
                           use_tr=use_tr,
                           viewBox_center_x=viewBox_center_x,
                           viewBox_center_y=viewBox_center_y,
                           center_radius=center_radius
                           )

@app.route('/guess', methods=['POST'])
def handle_guess():
    if 'letters' not in session:
        return jsonify({'status': 'error', 'message': 'Game not started. Please refresh.'}), 400

    guess = request.json.get('guess', '').strip().lower()
    # Retrieve game state from session
    letters_set = set(session['letters'])
    center_letter = session['center_letter']
    solution_map = session.get('normalized_solution_map', {}) # Get map from session
    found_words_set = set(session.get('found_words', [])) # Use get with default
    current_score = session.get('score', 0) # Use get with default
    total_possible_score = session.get('total_score', 0) # Use get with default

    # === Add Logging Start ===
    app.logger.info(f"[DEBUG /guess] Session state at START of guess handling:")
    app.logger.info(f"  - letters: {session.get('letters')}")
    app.logger.info(f"  - center_letter: {center_letter}") # Already retrieved
    app.logger.info(f"  - solutions length: {len(session.get('solutions', []))}") # Re-fetch for logging
    app.logger.info(f"  - norm_map length: {len(solution_map)}") # Use retrieved map
    app.logger.info(f"  - total_score: {total_possible_score}") # Use retrieved score
    app.logger.info(f"  - User guess: '{guess}', Normalized guess: '{spelling_bee.normalize_word(guess)}'")
    # === Add Logging End ===

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

@app.route('/get_dictionary_options')
def get_dictionary_options():
    # Define your available dictionaries (could be read from config/db)
    # Ensure 'common' is always available if it's non-optional
    AVAILABLE_DICTIONARIES = {
        'common': {'name': 'Common Words', 'description': 'Standard English words (Default)', 'optional': False},
        'te_reo': {'name': 'Te Reo Māori', 'description': 'Words from Te Reo Māori', 'optional': True},
        'nz_slang': {'name': 'NZ Slang', 'description': 'Common New Zealand slang terms', 'optional': True},
        # Add the new dictionary option
        'csw21': {'name': 'Collins Scrabble Words 2021', 'description': 'Official international Scrabble list (Aus/NZ/UK)', 'optional': True}
    }
    # Get current selections from session to pre-check boxes
    current_selections = session.get('active_list_types', ['common']) # Default to common if not set

    options_with_state = []
    for key, info in AVAILABLE_DICTIONARIES.items():
        options_with_state.append({
            'id': key,
            'name': info['name'],
            'description': info['description'],
            'optional': info.get('optional', True), # Assume optional if not specified
            'checked': key in current_selections
        })

    return jsonify(options_with_state)

@app.route('/start_game', methods=['POST'])
def start_game():
    start_time = time.time()
    app.logger.info("--- [START /start_game] ---")
    try:
        data = request.get_json()
        if not data:
             return jsonify({'success': False, 'error': 'Invalid request format'}), 400

        selected_list_types = data.get('dictionaries')

        # Validate input
        available_options = ['common', 'nz', 'au', 'tr'] # Replace with actual source if dynamic
        if (not selected_list_types or
                not isinstance(selected_list_types, list) or
                not all(item in available_options for item in selected_list_types)):
            app.logger.warning(f"Invalid dictionary selection received: {selected_list_types}")
            return jsonify({'success': False, 'error': 'Invalid dictionary selection provided'}), 400

        # Ensure 'common' is always included if it's mandatory
        if 'common' not in selected_list_types:
             app.logger.warning(f"'common' list missing from selection: {selected_list_types}. Adding it.")
             selected_list_types.insert(0, 'common') 
             selected_list_types = list(set(selected_list_types)) 

        # Update session *before* calling setup_new_game
        session['active_list_types'] = selected_list_types
        app.logger.info(f"Updated session active_list_types: {selected_list_types}")

        # Generate the new game using the selected lists
        success_flag = setup_new_game(DATABASE_PATH, selected_list_types) 

        if not success_flag:
             app.logger.error("setup_new_game failed to generate puzzle.")
             return jsonify({'success': False, 'error': 'Failed to generate game puzzle with selected lists.'}), 500

        # Retrieve the necessary letters from the session after successful setup
        center_letter = session.get('center_letter')
        ordered_outer_letters = session.get('outer_letters_ordered')

        # === Add Logging Start ===
        app.logger.info(f"[DEBUG /start_game] Session state AFTER setup:")
        app.logger.info(f"  - letters: {session.get('letters')}")
        app.logger.info(f"  - center_letter: {session.get('center_letter')}")
        app.logger.info(f"  - solutions length: {len(session.get('solutions', []))}")
        app.logger.info(f"  - norm_map length: {len(session.get('normalized_solution_map', {}))}")
        app.logger.info(f"  - total_score: {session.get('total_score')}")
        # === Add Logging End ===

        if not center_letter or not ordered_outer_letters:
             app.logger.error("Failed to retrieve letters from session after successful game setup.")
             return jsonify({'success': False, 'error': 'Internal server error retrieving game data.'}), 500

        end_time = time.time()
        app.logger.info(f"--- [END /start_game] Success! Time: {end_time - start_time:.2f}s ---")
        # Return success and the letters needed for frontend animation/display
        return jsonify({
            'success': True,
            'outer_letters': ordered_outer_letters, # Send the ordered outer letters
            'center_letter': center_letter.upper() # Ensure center is uppercase
         })

    except Exception as e:
        app.logger.error(f"!!! Unhandled error in /start_game: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error processing request.'}), 500

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