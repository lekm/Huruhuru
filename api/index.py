# app.py
# Inject pysqlite3 before any other imports that might load sqlite3
import _inject_pysqlite

import os
import sqlite3 # Now this should refer to the injected pysqlite3
from flask import Flask, render_template, request, session, jsonify, redirect, url_for, g
import requests
import click
from flask.cli import with_appcontext

# Import game logic from spelling_bee module
import spelling_bee
# Import database setup function
import database_setup
# Import the normalization function
from spelling_bee import normalize_word

app = Flask(__name__)
# Read secret key from environment variable, with a fallback for local dev
# IMPORTANT: Set a strong SECRET_KEY environment variable in production (Vercel settings)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-replace-in-prod-or-use-env')
# --- Define Base Directory and Database Path ---
# Get the absolute path to the directory containing app.py
basedir = os.path.abspath(os.path.dirname(__file__))
# Define the database path relative to app.py
DATABASE = os.path.join(basedir, 'word_database.db') # <--- Use os.path.join

# --- Database Connection Handling (using Flask's g object) ---
# Not strictly necessary for this app as connections are short-lived in
# spelling_bee functions, but good practice if DB was used more directly here.
# Sticking to passing DB path for simplicity now.

# --- Flask CLI Command for DB Initialization ---
@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    try:
        # Pass the absolute DATABASE path to the setup function
        database_setup.init_db(DATABASE) # <--- Ensure init_db uses the path
        click.echo('Initialized the database.')
    except Exception as e:
        click.echo(f'Error initializing database: {e}')

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

# --- Flask Routes ---

@app.route('/')
def index():
    # Initialize default list preferences if not in session
    session.setdefault('use_nz', False)
    session.setdefault('use_au', False)
    session.setdefault('use_tr', False)

    # --- Game Setup ---
    # Start a new game if no letters in session (implies new visit or /new_game redirect)
    if 'letters' not in session:
        print("No letters found in session, starting new game setup...")
        # Check if DB exists before proceeding
        # Check if DB exists using the absolute path
        if not os.path.exists(DATABASE): # <--- Check uses the absolute path
             # Consider logging the path checked for easier debugging:
             print(f"Database file not found at expected path: {DATABASE}")
             return "Error: Word database file not found. Please check server logs.", 500 # More generic error

        active_list_types = get_active_list_types_from_session()
        if not active_list_types: # Should at least have 'common'
            return "Error: No active word lists selected or configured.", 500

        try:
            # Call refactored functions from spelling_bee module
            # Ensure functions called here use the absolute DATABASE path
            letters, center_letter = spelling_bee.choose_letters(DATABASE, active_list_types)
            # Ensure letters is a set for calculations, store as list in session
            letters_set = set(letters)
            # Get both solutions and the normalization map
            valid_solutions, normalized_solution_map = spelling_bee.find_valid_words(DATABASE, letters_set, center_letter, active_list_types)
            total_score = spelling_bee.calculate_total_score(valid_solutions, letters_set)

            # Store game state in session (convert sets to lists for JSON compatibility)
            session['letters'] = sorted(list(letters_set))
            session['center_letter'] = center_letter
            # Store canonical solutions as list for display/counting
            session['valid_solutions'] = sorted(list(valid_solutions))
            session['solution_map'] = normalized_solution_map # Store the map
            session['total_score'] = total_score
            session['found_words'] = []
            session['current_score'] = 0
            print(f"New game started. Letters: {session['letters']}, Center: {center_letter}, Solutions: {len(session['valid_solutions'])}, Map Size: {len(session['solution_map'])}, Total Score: {total_score}")

        except ConnectionError as e:
             # Log the path attempted for connection if possible
             print(f"Database connection error during game setup using path: {DATABASE}. Error: {e}")
             return f"Error: Could not connect to the word database.", 500 # More generic error
        except RuntimeError as e:
            print(f"Error generating puzzle: {e}")
            # Provide a user-friendly message
            return f"Error: Could not generate a suitable puzzle with the current word list selections. Details: {e}", 500
        except Exception as e:
            # Catch any other unexpected errors during setup
            print(f"Unexpected error during game setup: {e}")
            # Potentially log the full traceback here
            return "An unexpected error occurred while setting up the game.", 500


    # --- Prepare data for template (using session data) ---
    center_letter = session['center_letter']
    display_letters = sorted(session['letters'])
    outer_letters = [l for l in display_letters if l != center_letter]
    current_score = session['current_score']
    total_possible_score = session['total_score']
    found_words = sorted(session['found_words'])
    # Use refactored get_rank from spelling_bee
    rank = spelling_bee.get_rank(current_score, total_possible_score)
    total_words_count = len(session.get('valid_solutions', [])) # Get total word count

    return render_template('index.html',
                           letters=display_letters,
                           center_letter=center_letter,
                           outer_letters=outer_letters,
                           found_words=found_words,
                           score=current_score,
                           rank=rank,
                           total_words=total_words_count,
                           use_nz=session['use_nz'], # Pass list preferences
                           use_au=session['use_au'],
                           use_tr=session['use_tr'],
                           message=session.pop('message', None)) # Display flash messages if any


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
    normalized_guess = normalize_word(guess)

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
    if not os.path.exists(DATABASE):
        print(f"Warning: Database file '{DATABASE}' not found.")
        print("Please run 'flask init-db' in your terminal to create and populate it.")
        # Optionally exit or prevent app run? For development, allow running.
        # exit(1)
    app.run(debug=True, port=5001) # Use debug mode for development 