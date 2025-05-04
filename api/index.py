# app.py
# Inject pysqlite3 before any other imports that might load sqlite3
# import _inject_pysqlite # <<< COMMENTED OUT for local init-db

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

# --- Database Connection Helpers --- >

# Dictionary containing the metadata for display (replaces definition in /get_dictionary_options)
# Moved here to be globally accessible
AVAILABLE_DICTIONARIES_METADATA = {
    'csw21': {'label': 'Standard', 'description': 'Official Scrabble list', 'optional': False, 'icon_type': 'emoji', 'icon_value': '🇬🇧'},
    'te_reo': {'label': 'Te Reo Māori', 'description': 'Words from Te Reo Māori', 'optional': True, 'icon_type': 'image', 'icon_value': '/static/images/maori_sticker.gif'},
    'nz_slang': {'label': 'NZ Slang', 'description': 'Common New Zealand slang', 'optional': True, 'icon_type': 'emoji', 'icon_value': '🇳🇿'}
}

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        try:
            # Ensure DATABASE_PATH is the correct, accessible path at runtime
            g.db = sqlite3.connect(DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
            g.db.row_factory = sqlite3.Row # Return rows that behave like dicts
            app.logger.info(f"Database connection opened successfully to {DATABASE_PATH}")
        except sqlite3.Error as e:
            app.logger.error(f"!!! Database connection error to {DATABASE_PATH}: {e}", exc_info=True)
            g.db = None # Ensure g.db is None if connection fails
            abort(500, description="Database connection failed.") # Abort on connection error
    elif g.db is None:
        # If g.db exists but is None (previous connection failed), abort
        app.logger.error("!!! Attempted to use failed database connection.")
        abort(500, description="Database connection previously failed.")
    return g.db

@app.teardown_appcontext
def close_db(error): # error argument is automatically passed by Flask
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()
        app.logger.info("Database connection closed.")
    if error:
        # Log the error that occurred during the request handling
        app.logger.error(f"App context teardown due to error: {error}", exc_info=True)

def get_word_list_type(db, word):
    """Queries the database for the list_type of a given word."""
    if not db:
        app.logger.error("get_word_list_type called with no DB connection.")
        return None # Or raise an error
    try:
        cursor = db.execute('SELECT list_type FROM words WHERE word = ?', (word,))
        result = cursor.fetchone()
        return result['list_type'] if result else None
    except sqlite3.Error as e:
        app.logger.error(f"DB error fetching list_type for '{word}': {e}", exc_info=True)
        return None
    except Exception as e:
        # Catch unexpected errors, e.g., if row_factory isn't working
        app.logger.error(f"Unexpected error fetching list_type for '{word}': {e}", exc_info=True)
        return None

# < -------------------------------

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
    active_types = ['csw21'] # Default is now CSW21
    if session.get('use_nz', False): # Assuming use_nz corresponds to nz_slang key
        active_types.append('nz_slang')
    # if session.get('use_au', False): # No corresponding AU key in AVAILABLE_DICTIONARIES
    #     active_types.append('au')
    if session.get('use_tr', False): # Assuming use_tr corresponds to te_reo key
        active_types.append('te_reo')
    print(f"Active list types from session: {active_types}") # Debug log
    return list(set(active_types)) # Ensure uniqueness

# --- Helper Function for New Game Setup (MODIFIED) ---
def setup_new_game(db_path, active_list_types):
    """Sets up a new game, updates session, returns success status."""
    if not active_list_types or not isinstance(active_list_types, list):
         app.logger.error(f"Invalid active_list_types provided: {active_list_types}")
         return False

    try:
        app.logger.info(f"Setting up new game with DB: {db_path}, Lists: {active_list_types}")
        
        # 1. Choose letters
        letters_set, center_letter = spelling_bee.choose_letters(db_path, active_list_types)
        app.logger.info(f"Letters chosen: {letters_set}, Center: {center_letter}")

        # 2. Find ALL valid words for chosen letters ACROSS selected lists
        solutions, normalized_solution_map = spelling_bee.find_valid_words(db_path, letters_set, center_letter, active_list_types)
        app.logger.info(f"Total solutions found: {len(solutions)}")
        if not solutions:
            app.logger.error("No solutions found for the chosen letters and lists!")
            return False # Cannot proceed without solutions

        # 3. Determine list_type for each solution and calculate counts
        solution_counts_by_list = {list_type: 0 for list_type in active_list_types}
        found_counts_by_list = {list_type: 0 for list_type in active_list_types} # Initialize found counts
        solutions_with_type = [] # Store word and its type if needed elsewhere
        db = get_db() # Get DB connection
        if not db:
             app.logger.error("Failed to get DB connection in setup_new_game")
             return False # Cannot proceed without DB

        for word in solutions:
            list_type = get_word_list_type(db, word)
            if list_type and list_type in active_list_types:
                solution_counts_by_list[list_type] += 1
                solutions_with_type.append((word, list_type))
            else:
                app.logger.warning(f"Solution '{word}' has unknown or inactive list_type: {list_type}. Ignoring for counts.")
        
        # Log the counts per list
        app.logger.info(f"Solution counts per list: {solution_counts_by_list}")

        # 4. Calculate total score (using original full solutions list)
        total_score = spelling_bee.calculate_total_score(solutions, letters_set)
        app.logger.info(f"Total score calculated: {total_score}")

        # --- Calculate Coordinates (Keep as is) ---
        viewBox_center_x = 75
        viewBox_center_y = 75
        center_radius = 25
        outer_ring_end_radius = 65
        letter_radius = center_radius + (outer_ring_end_radius - center_radius) / 2
        all_letters_sorted = sorted(list(letters_set))
        outer_letters_alpha = [l for l in all_letters_sorted if l != center_letter]
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

        # 5. Update Session
        session['center_letter'] = center_letter
        session['letters_set'] = "".join(sorted(list(letters_set)))
        session['solutions'] = list(solutions)
        session['normalized_solution_map'] = normalized_solution_map
        session['found_words'] = []
        session['score'] = 0
        session['total_score'] = total_score
        session['rank'] = calculate_rank(0, total_score)
        session['active_list_types'] = active_list_types # Store active types
        session['solution_counts'] = solution_counts_by_list # Store totals per list
        session['found_counts'] = found_counts_by_list # Store found counts per list (initially all 0)
        
        # Store calculated SVG data
        session['viewBox_center_x'] = viewBox_center_x
        session['viewBox_center_y'] = viewBox_center_y
        session['center_radius'] = center_radius
        session['outer_segments_data'] = outer_segments_data
        session['ordered_outer_letters'] = ordered_outer_letters_for_js # For shuffle animation

        app.logger.info("New game session initialized successfully.")
        return True

    except Exception as e:
        app.logger.error(f"Error setting up new game: {e}", exc_info=True)
        return False

# --- Helper Function to Calculate Rank --- >
# Define Kiwi Ranks with percentage thresholds
KIWI_RANKS = {
    0.00: "Egg",        # 0%
    0.03: "Bit Useless, Eh", # 3%
    0.08: "Not Bad, Bro",   # 8%
    0.15: "Sweet As",     # 15%
    0.25: "On the Piss",  # 25%
    0.40: "Full Noise",   # 40%
    0.60: "Bloody Weapon",# 60%
    0.80: "Choice Cunt",  # 80%
    1.00: "King Shit"     # 100%
}
# Sort thresholds for iteration
SORTED_KIWI_THRESHOLDS = sorted(KIWI_RANKS.keys())

def calculate_rank(score, total_score):
    """Calculates the player's rank based on score using Kiwi ranks."""
    
    if total_score <= 0:
        return KIWI_RANKS[0.00] # Return lowest rank (Egg) if no total score

    percentage = score / total_score

    # Handle exact 100% case
    if percentage >= 1.0:
        return KIWI_RANKS[1.00] # King Shit
    
    # Find the highest applicable rank based on percentage
    current_rank = KIWI_RANKS[0.00] # Default to lowest rank
    for threshold in SORTED_KIWI_THRESHOLDS:
        if percentage >= threshold:
            current_rank = KIWI_RANKS[threshold]
        else:
            # Since thresholds are sorted, we've found the highest applicable rank
            break 
            
    return current_rank

# < ------------------------------------

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
    """Main page route."""
    app.logger.info("--- Request received for / route ---")
    
    game_in_session = session.get('letters_set') is not None
    app.logger.info(f"Rendering index page. Game in session: {game_in_session}")
    
    # Initialize context with minimal non-game data
    context = {
        'message': session.get('message', ''),
        'game_in_session': game_in_session
    }

    if game_in_session:
        # --- If game exists, populate all game-related context ---
        current_score = session.get('score', 0)
        total_score = session.get('total_score', 0)
        calculated_rank = calculate_rank(current_score, total_score)

        context.update({
            'center_letter': session.get('center_letter'),
            'found_words': session.get('found_words', []),
            'score': current_score,
            'rank': calculated_rank,
            'viewBox_center_x': session.get('viewBox_center_x'),
            'viewBox_center_y': session.get('viewBox_center_y'),
            'center_radius': session.get('center_radius'),
            'outer_segments_data': session.get('outer_segments_data'),
            'ordered_outer_letters': session.get('ordered_outer_letters', [])
        })

        # Construct the display_stats list
        active_list_types = session.get('active_list_types', [])
        solution_counts = session.get('solution_counts', {})
        found_counts = session.get('found_counts', {})
        display_stats = []
        for list_type in active_list_types:
            meta = AVAILABLE_DICTIONARIES_METADATA.get(list_type)
            if meta:
                display_stats.append({
                    'key': list_type,
                    'label': meta['label'],
                    'icon_type': meta.get('icon_type'),
                    'icon_value': meta.get('icon_value'),
                    'total': solution_counts.get(list_type, 0),
                    'found': found_counts.get(list_type, 0)
                })
            else:
                 app.logger.warning(f"Metadata not found for active list type: {list_type}")
        
        context['display_stats'] = display_stats
        app.logger.info(f"Populated display_stats: {display_stats}")

    else:
        # --- No game in session, set defaults for display --- >
        context.update({
            'center_letter': None,
            'found_words': [],
            'score': 0,
            'rank': KIWI_RANKS[0.00], # Default rank ('Egg')
            'viewBox_center_x': None,
            'viewBox_center_y': None,
            'center_radius': None,
            'outer_segments_data': None,
            'ordered_outer_letters': [],
            'display_stats': []
        })
        app.logger.info("No active game session found, rendering with defaults.")
        # < ---------------------------------------------------

    session.pop('message', None)
    
    # --- Add Logging Before Render --- >
    app.logger.info("--- [DEBUG / route] Checking session before rendering --- ")
    app.logger.info(f"  - Session letters_set: {session.get('letters_set')}")
    app.logger.info(f"  - Session solution_counts: {session.get('solution_counts')}")
    # < -------------------------------
    
    return render_template('index.html', **context)

@app.route('/guess', methods=['POST'])
def handle_guess():
    """Handles a word guess submission."""
    if 'letters_set' not in session:
        app.logger.warning("Guess submitted without active game session.")
        return jsonify({'message': 'No active game. Start a new game?', 'valid': False, 'score': 0, 'rank': 'N/A'})

    guess = request.json.get('guess', '').lower()
    app.logger.info(f"[/guess] Received guess: {guess}")

    # --- ADD LOGGING TO CHECK SESSION STATE --- >
    center_letter_from_session = session.get('center_letter', 'MISSING')
    letters_set_str_from_session = session.get('letters_set', 'MISSING')
    app.logger.info(f"--- [/guess] Validating against session letters: '{letters_set_str_from_session}', center: '{center_letter_from_session}' ---") 
    # < ----------------------------------------
    
    # Use the retrieved session values for validation
    center_letter = center_letter_from_session
    letters_set_str = letters_set_str_from_session
    
    if center_letter == 'MISSING' or letters_set_str == 'MISSING':
        app.logger.error("[/guess] Critical error: Letters missing from session during guess.")
        return jsonify({'message': 'Error: Game state lost. Please start a new game.', 'valid': False})
        
    letters_set = set(letters_set_str) # Convert string to set for checking
    normalized_solution_map = session.get('normalized_solution_map', {})
    found_words = session.get('found_words', [])

    # Basic validation
    if not guess:
        return jsonify({'message': 'Please enter a word.', 'valid': False})
    if any(letter not in letters_set for letter in guess):
        invalid_letters = sorted(list(set(l for l in guess if l not in letters_set)))
        return jsonify({'message': f"Invalid letter(s): {', '.join(invalid_letters).upper()}", 'valid': False})
    if center_letter not in guess:
        return jsonify({'message': f'Missing center letter: {center_letter.upper()}', 'valid': False})
    if len(guess) < 4:
        return jsonify({'message': 'Too short (min 4 letters).', 'valid': False})

    # Normalize the guess
    normalized_guess = spelling_bee.normalize_word(guess)
    app.logger.info(f"Normalized guess: {normalized_guess}")

    # Check if the normalized guess is a valid solution
    if normalized_guess in normalized_solution_map:
        original_word = normalized_solution_map[normalized_guess] # Get the correctly cased/accented word
        
        if original_word in found_words:
            return jsonify({'message': 'Already found!', 'valid': False, 'word': original_word}) # Return original word
        else:
            # --- Word is valid and new ---
            points = spelling_bee.calculate_score(original_word, letters_set)
            is_pangram = spelling_bee.is_pangram(original_word, letters_set)
            message = f"+{points}"
            if is_pangram:
                message += " Pangram!"
            
            # Update session data
            session['found_words'].append(original_word)
            session['score'] += points
            
            # --- Update per-dictionary found counts ---
            db = get_db()
            list_type = get_word_list_type(db, original_word) # Use original word for DB lookup
            updated_list_type = None
            new_found_count_for_list = None
            if list_type and list_type in session.get('found_counts', {}):
                session['found_counts'][list_type] = session['found_counts'].get(list_type, 0) + 1
                updated_list_type = list_type
                new_found_count_for_list = session['found_counts'][list_type]
                app.logger.info(f"Incremented found count for list type '{list_type}' to {new_found_count_for_list}")
            else:
                 app.logger.warning(f"Could not find or update list type '{list_type}' for word '{original_word}' in session found_counts.")

            # --- Recalculate Rank ---
            total_score = session.get('total_score', 0)
            new_rank = calculate_rank(session['score'], total_score)
            session['rank'] = new_rank

            # --- Ensure session modifications are saved ---
            session.modified = True 
            
            app.logger.info(f"Word '{original_word}' is valid. Score +{points}. New total: {session['score']}. Rank: {new_rank}.")

            # Check if all words are found
            all_found = len(session['found_words']) == len(session.get('solutions', []))
            if all_found:
                message = "Congratulations! You found all the words!"

            # --- Add Logging Before Return ---
            app.logger.info(f"--- [DEBUG /guess] Returning Rank: {new_rank} ---")
            # --- End Logging Before Return ---

            return jsonify({
                'message': message, 
                'valid': True, 
                'word': original_word, # Send back original case
                'score': session['score'], 
                'rank': new_rank,
                'is_pangram': is_pangram,
                'all_found': all_found,
                'updated_list_type': updated_list_type, # Send the list type that was updated
                'new_found_count': new_found_count_for_list # Send the new count for that list
            })
    else:
        # Word is not in the solution list
        app.logger.info(f"Guess '{guess}' (normalized: '{normalized_guess}') not in solutions.")
        return jsonify({'message': 'Not a valid word.', 'valid': False})

@app.route('/update_settings', methods=['POST'])
def update_settings():
    """Updates word list preferences in the session and starts a new game."""
    print("Updating settings...")
    session['use_nz'] = 'use_nz' in request.form
    session['use_au'] = 'use_au' in request.form
    session['use_tr'] = 'use_tr' in request.form
    print(f"New settings: NZ={session['use_nz']}, AU={session['use_au']}, TR={session['use_tr']}")

    # Clear existing game state to force a new puzzle generation on redirect
    session.pop('letters_set', None)
    session.pop('center_letter', None)
    session.pop('solutions', None)
    session.pop('normalized_solution_map', None)
    session.pop('found_words', None)
    session.pop('score', None)
    session.pop('total_score', None)
    session.pop('rank', None)
    session.pop('active_list_types', None)
    session.pop('solution_counts', None)
    session.pop('found_counts', None)
    session.pop('viewBox_center_x', None)
    session.pop('viewBox_center_y', None)
    session.pop('center_radius', None)
    session.pop('outer_segments_data', None)
    session.pop('ordered_outer_letters', None)
    session['message'] = "Word list settings updated. New game started!" # Flash message
    session.modified = True

    return redirect(url_for('index')) # Redirect back to index to generate new game

@app.route('/get_dictionary_options')
def get_dictionary_options():
    # Use the globally defined metadata
    try:
        current_selections = session.get('active_list_types', ['csw21'])

        options_with_state = []
        for key, info in AVAILABLE_DICTIONARIES_METADATA.items():
            options_with_state.append({
                'id': key,
                'label': info['label'],
                'description': info['description'],
                'optional': info.get('optional', True),
                'checked': key in current_selections,
                'icon_type': info.get('icon_type', 'emoji'),
                'icon_value': info.get('icon_value', '')
            })

        return jsonify({
            'options': options_with_state,
            'selected': current_selections
        })
    except Exception as e:
        current_app.logger.error(f"Error in /get_dictionary_options: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to load dictionary options'}), 500

@app.route('/start_game', methods=['POST'])
def start_game():
    """Starts a new game based on selected dictionaries."""
    data = request.get_json()
    if not data or 'selected_lists' not in data:
        app.logger.error("'/start_game': Missing 'selected_lists' in request data.")
        return jsonify({'success': False, 'message': 'Missing dictionary selection.'}), 400

    selected_lists = data['selected_lists']
    
    # Basic validation - ensure it's a list and contains valid keys
    if not isinstance(selected_lists, list) or not all(key in AVAILABLE_DICTIONARIES_METADATA for key in selected_lists):
        app.logger.error(f"'/start_game': Invalid 'selected_lists' received: {selected_lists}")
        return jsonify({'success': False, 'message': 'Invalid dictionary selection.'}), 400
        
    # Ensure the mandatory 'csw21' list is always included if available
    if 'csw21' in AVAILABLE_DICTIONARIES_METADATA and 'csw21' not in selected_lists:
        selected_lists.append('csw21')
        app.logger.info("'/start_game': Force-included 'csw21' dictionary.")

    app.logger.info(f"'/start_game': Received request to start game with lists: {selected_lists}")

    # Use the correct database path
    db_path = DATABASE_PATH

    # Attempt to set up the new game and store details in session
    success = setup_new_game(db_path, selected_lists)

    if success:
        # Game setup was successful, retrieve necessary data from session
        app.logger.info("'/start_game': New game setup successful. Preparing response data.")
        
        # Retrieve data stored by setup_new_game
        all_letters = sorted(list(session.get('letters_set', set())))
        center_letter = session.get('center_letter', '')
        solution_counts = session.get('solution_counts', {}) # Totals per list
        total_score = session.get('total_score', 0) # <<< RETRIEVE TOTAL SCORE

        # Format word counts for frontend { key: { found: 0, total: X } }
        word_counts_for_js = {
            key: {'found': 0, 'total': count}
            for key, count in solution_counts.items()
        }
        
        # Filter metadata for active dictionaries
        active_dict_metadata = {
            key: AVAILABLE_DICTIONARIES_METADATA[key] 
            for key in selected_lists if key in AVAILABLE_DICTIONARIES_METADATA
        }

        # Prepare the full response payload
        response_data = {
            'success': True,
            'all_letters': all_letters,
            'center_letter': center_letter,
            'current_score': 0, # Initial score is always 0
            'rank': 'Egg',     # Initial rank is always 'Egg'
            'word_counts_by_type': word_counts_for_js,
            'active_dict_metadata': active_dict_metadata, # Pass metadata for UI building
            'total_score': total_score, # <<< ADD TOTAL SCORE TO RESPONSE
            'message': 'New game started successfully!' # Optional success message
        }
        app.logger.info(f"'/start_game': Sending success response: {response_data}") # Log response data
        return jsonify(response_data)
    else:
        # Game setup failed (e.g., no words found for letters/lists)
        app.logger.error("'/start_game': setup_new_game returned False. Failed to start new game.")
        return jsonify({'success': False, 'message': 'Failed to generate a suitable puzzle. Please try again.'}), 500

# --- Definition Route (Remains largely unchanged) ---
@app.route('/definition/<word>')
def get_definition(word):
    """Fetches definitions for a given word from the local database, with fallback to an external API."""
    definition_text = "Definition not found."
    definitions = [] # Store definition strings
    
    # 1. Try local database first
    db = get_db()
    if not db:
        app.logger.error(f"Could not get DB connection for definition lookup of '{word}'")
        return jsonify({'definition': 'Error: Database connection failed.'}), 500

    try:
        query = """
            SELECT d.definition_text 
            FROM definitions d
            JOIN words w ON d.word_id = w.word_id 
            WHERE w.word = ?
        """
        cursor = db.cursor()
        cursor.execute(query, (word.lower(),)) # Query using lowercase word
        results = cursor.fetchall()
        
        if results:
            app.logger.info(f"Found {len(results)} definitions for '{word}' in local DB.")
            # Format local definitions
            definitions = [row[0] for row in results]

    except sqlite3.Error as e:
        app.logger.error(f"Database error fetching definition for '{word}': {e}")
        # Don't return error yet, try API fallback
    except Exception as e:
        app.logger.error(f"Unexpected error fetching local definition for '{word}': {e}")
        # Don't return error yet, try API fallback

    # 2. If no local definitions found, try external API
    if not definitions:
        app.logger.info(f"No local definition for '{word}', trying external API...")
        api_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        try:
            response = requests.get(api_url, timeout=5) # Add timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            
            data = response.json()
            if data and isinstance(data, list):
                # Try to extract the first definition found
                first_entry = data[0]
                if 'meanings' in first_entry and first_entry['meanings']:
                    first_meaning = first_entry['meanings'][0]
                    if 'definitions' in first_meaning and first_meaning['definitions']:
                        first_def_obj = first_meaning['definitions'][0]
                        if 'definition' in first_def_obj:
                            definitions.append(first_def_obj['definition']) # Add the API definition
                            app.logger.info(f"Successfully fetched definition for '{word}' from API.")
                        else:
                            app.logger.warning(f"API response structure missing 'definition' field for '{word}'")
                    else:
                         app.logger.warning(f"API response structure missing 'definitions' list for '{word}'")
                else:
                     app.logger.warning(f"API response structure missing 'meanings' list for '{word}'")
            else:
                app.logger.warning(f"API returned no data or unexpected format for '{word}'")

        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error calling definition API for '{word}': {e}")
        except Exception as e:
            app.logger.error(f"Error parsing API response for '{word}': {e}")

    # 3. Format the final result (could be local, API, or default message)
    if definitions:
        # Join multiple definitions (if from local DB) with numbers
        if len(definitions) > 1:
             definition_text = "\n\n".join([f"{idx+1}. {d}" for idx, d in enumerate(definitions)])
        else:
            definition_text = definitions[0] # Single definition (local or API)
    # else: definition_text remains "Definition not found."
    
    return jsonify({'definition': definition_text})

# --- Main Execution ---
if __name__ == "__main__":
    # Check if DB exists on startup (optional, but helpful)
    # This check will likely use the path relative to where the script is run locally
    local_dev_db_path = os.path.join(os.path.dirname(__file__), 'word_database.db') # Path for local dev check
    if not os.path.exists(local_dev_db_path):
        print(f"Warning: Local database file '{local_dev_db_path}' not found.")
        print("Please run 'flask init-db' in your terminal to create and populate it.")
        
    app.run(debug=True, port=5001) 