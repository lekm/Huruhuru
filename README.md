# Spelling Bee NZ Clone

A Python Flask application mimicking the New York Times Spelling Bee game, with a focus on NZ English, Australian English, and Te Reo Māori word lists.

## Features

*   Classic Spelling Bee gameplay (7 letters, 1 required center letter).
*   Scoring system (1 point for 4-letter words, length points for longer, +7 for pangrams).
*   Rank progression from Beginner to Queen Bee.
*   Modular word lists using SQLite:
    *   Common Core (Commonwealth English)
    *   NZ Specific (Optional)
    *   AUS Specific (Optional)
    *   Te Reo Māori (Optional, with macron normalization)
*   Word list selection via Settings dialog.
*   Definition lookup for found words (via DictionaryAPI).

## Local Setup & Running

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <repository-folder>
    ```

2.  **Create a virtual environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Prepare Word Lists:**
    *   Place your source word list files (UTF-8 encoded) into the `wordlists/source/` directory:
        *   `source_commonwealth.txt`
        *   `source_nz_raw.txt`
        *   `source_au_raw.txt`
        *   `source_maori_raw.txt`
    *   Ensure `source_commonwealth.txt` contains pangrams (7-letter words with 7 unique letters) for puzzle generation to work reliably.

5.  **Generate Processed Lists:**
    ```bash
    python3 generate_wordlists.py
    ```

6.  **Initialize Database:**
    *   This command reads the files generated in the previous step (`wordlists/processed/`) and creates `word_database.db`.
    ```bash
    python3 -m flask init-db
    ```

7.  **Run the Flask development server:**
    *   The `start.sh` script can also be used (ensure it uses `python3` if needed).
    ```bash
    python3 app.py
    ```
    *   The application should be available at `http://127.0.0.1:5001`.

## Deployment (Vercel)

*   Connect your GitHub repository to Vercel.
*   Vercel should automatically detect the `vercel.json` configuration.
*   **Crucially, set the `SECRET_KEY` environment variable** in your Vercel project settings to a strong, random string. The build process defined in `vercel.json` will handle installing dependencies, generating word lists, and initializing the database.

## Project Structure

```
├── wordlists/          # Word list files
│   ├── source/         # Raw input lists
│   └── processed/      # Cleaned lists for DB init
├── static/             # CSS, JavaScript
├── templates/          # HTML templates
├── .gitignore          # Files ignored by Git
├── app.py              # Main Flask application, routes
├── database_setup.py   # Script to initialize the database schema and data
├── generate_wordlists.py # Script to process source lists into final lists
├── requirements.txt    # Python dependencies
├── spelling_bee.py     # Core game logic
├── start.sh            # Helper script for local execution (not used by Vercel)
├── vercel.json         # Vercel deployment configuration
└── README.md           # This file
``` 