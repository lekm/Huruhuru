import xml.sax
import bz2
import re
import argparse
import sys
from collections import defaultdict

# --- Configuration ---
MIN_WORD_LENGTH = 4

# Output filenames
OUTPUT_COMMONWEALTH = 'source_commonwealth_wikt.txt'
OUTPUT_NZ = 'source_nz_wikt.txt'
OUTPUT_AU = 'source_au_wikt.txt'
OUTPUT_MAORI = 'source_maori_wikt.txt'

# Target categories (lowercase) - These need careful selection and refinement!
# Add more as needed based on Wiktionary's actual category structure.
COMMONWEALTH_CATEGORIES = {
    'british english', 'commonwealth english', 'uk english',
    'english terms spelled with -our', 'english terms spelled with -re',
    'english terms spelled with -ise', # Be cautious, -ize is also used
    # Add other relevant categories... e.g., 'irish english', 'scottish english'?
}
NZ_CATEGORIES = {'new zealand english', 'new zealand slang', 'nz english'}
AU_CATEGORIES = {'australian english', 'australian slang', 'au english'}
# Include variations and common misspellings if observed in the dump
MAORI_CATEGORIES = {'māori language', 'māori lemmas', 'maori language', 'maori lemmas', 'te reo maori'}

# Regex for extracting categories from wikitext
# Looks for [[Category:Something]] or [[Category:Something|Sortkey]]
CATEGORY_RE = re.compile(r'\[\[Category:([^\]|]+)(?:\|[^\]]*)?\]\]', re.IGNORECASE)

# Regex for validating characters
# English: only a-z (lowercase is checked after conversion)
VALID_ENG_CHARS_RE = re.compile(r'^[a-z]+$')
# Maori: a-z plus macrons (handle UTF-8 correctly)
VALID_MAORI_CHARS_RE = re.compile(r'^[a-zāēīōū]+$')

# Title prefixes to ignore (common namespaces, converted to lowercase)
IGNORE_TITLE_PREFIXES = ('category:', 'template:', 'user:', 'file:', 'wikipedia:', 'help:', 'module:', 'media:', 'appendix:', 'wiktionary:', 'thesaurus:')

# --- SAX Content Handler ---

class WiktionaryHandler(xml.sax.ContentHandler):
    """
    SAX Handler to process Wiktionary XML dump, extracting words based on categories.
    """
    def __init__(self):
        super().__init__()
        self.current_tag = ""
        self.current_title = ""
        self.current_text = ""
        self.page_categories = set()

        # Output sets for collected words
        self.commonwealth_words = set()
        self.nz_words = set()
        self.au_words = set()
        self.maori_words = set()

        self.page_count = 0
        self.report_interval = 10000 # Print progress every N pages

    def startElement(self, name, attrs):
        self.current_tag = name
        if name == 'page':
            # Reset page-specific data
            self.current_title = ""
            self.current_text = ""
            self.page_categories = set()
            self.page_count += 1
            if self.page_count % self.report_interval == 0:
                print(f"Processed {self.page_count} pages...", file=sys.stderr)

    def characters(self, content):
        # Accumulate content for relevant tags
        if self.current_tag == 'title':
            self.current_title += content
        elif self.current_tag == 'text':
            # Limit text accumulation to prevent excessive memory use if needed,
            # but categories are usually near the end. For now, accumulate all.
            self.current_text += content

    def endElement(self, name):
        if name == 'text':
            # Extract categories from the page text once the text element ends
            try:
                found_categories = CATEGORY_RE.findall(self.current_text)
                # Store lowercase, stripped category names
                self.page_categories = {cat.lower().strip() for cat in found_categories}
            except Exception as e:
                # Handle potential regex errors on weird text content
                print(f"Warning: Error processing categories for page '{self.current_title}': {e}", file=sys.stderr)
                self.page_categories = set() # Ensure it's empty on error

        elif name == 'page':
            # Process the completed page data
            self._process_page()

        # Reset current tag regardless of which element ended
        self.current_tag = ""

    def _process_page(self):
        """Processes the data collected for a single <page> element."""
        title = self.current_title.strip().lower()

        # 1. Filter out titles that are not likely words
        if not title or len(title) < MIN_WORD_LENGTH:
            return
        if title.startswith(IGNORE_TITLE_PREFIXES):
            return
        if ':' in title: # Often indicates non-main namespace entries
             return

        # 2. Skip pages if no categories were found
        if not self.page_categories:
            return

        # 3. Check character validity for English and Māori
        is_maori_candidate = bool(VALID_MAORI_CHARS_RE.match(title))
        is_eng_candidate = bool(VALID_ENG_CHARS_RE.match(title))

        # Only proceed if the title matches one of the valid character sets
        if not is_maori_candidate and not is_eng_candidate:
            return

        # Use the already lowercased category set from endElement('text')
        page_cats_lower = self.page_categories
        added = False # Flag to potentially prevent adding to multiple lists if desired

        # 4. Check categories and add word to appropriate lists

        # Prioritize Māori if categories match and chars are valid Māori
        if is_maori_candidate and not page_cats_lower.isdisjoint(MAORI_CATEGORIES):
            self.maori_words.add(title)
            added = True # Decide if Māori words should *also* be in English lists
                         # Current logic: if identified as Māori, don't add elsewhere.

        # Check NZ/AU/Commonwealth only if it's a valid English format word
        # and wasn't already added as Māori (based on 'added' flag)
        if is_eng_candidate and not added:
            # Check NZ English
            if not page_cats_lower.isdisjoint(NZ_CATEGORIES):
                self.nz_words.add(title)
                # We allow overlap between NZ/AU/Commonwealth for now.
                # The generate_wordlists.py script can handle deduplication/prioritization later.

            # Check AU English
            if not page_cats_lower.isdisjoint(AU_CATEGORIES):
                self.au_words.add(title)

            # Check Commonwealth English (includes UK etc.)
            if not page_cats_lower.isdisjoint(COMMONWEALTH_CATEGORIES):
                self.commonwealth_words.add(title)


# --- Helper Function ---

def write_output(filename, word_set):
    """Sorts and writes a set of words to a file, one word per line (UTF-8)."""
    print(f"Writing {len(word_set)} words to {filename}...")
    sorted_words = sorted(list(word_set))
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for word in sorted_words:
                f.write(word + '\\n')
    except IOError as e:
        print(f"Error writing to file {filename}: {e}", file=sys.stderr)

# --- Main Execution ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse English Wiktionary XML dump to extract words based on regional categories.')
    parser.add_argument('input_file', help='Path to the bz2 compressed Wiktionary XML dump (e.g., enwiktionary-latest-pages-articles.xml.bz2)')
    args = parser.parse_args()

    input_filepath = args.input_file

    print(f"Starting Wiktionary parse process on: {input_filepath}")
    print("This may take a very long time depending on the dump size and system performance.")
    print("Ensure you have sufficient disk space for the output files.")

    # Create the handler and parser
    handler = WiktionaryHandler()
    parser = xml.sax.make_parser()
    parser.setContentHandler(handler)

    # Open the compressed file and parse
    try:
        with bz2.open(input_filepath, 'rt', encoding='utf-8', errors='ignore') as infile:
            parser.parse(infile)
    except FileNotFoundError:
        print(f"Error: Input file not found at '{input_filepath}'", file=sys.stderr)
        sys.exit(1)
    except xml.sax.SAXParseException as e:
         print(f"XML Parsing Error: {e}. The dump might be corrupt or incomplete.", file=sys.stderr)
         # Continue to write whatever was collected before the error
    except Exception as e:
        print(f"An unexpected error occurred during parsing: {e}", file=sys.stderr)
        # Continue if possible
        
    print("\nParsing complete. Writing output files...")

    # Write the collected words to output files
    write_output(OUTPUT_COMMONWEALTH, handler.commonwealth_words)
    write_output(OUTPUT_NZ, handler.nz_words)
    write_output(OUTPUT_AU, handler.au_words)
    write_output(OUTPUT_MAORI, handler.maori_words)

    print("\n--- Summary ---")
    print(f"Total pages processed: {handler.page_count}")
    print(f"Commonwealth words found: {len(handler.commonwealth_words)}")
    print(f"New Zealand words found: {len(handler.nz_words)}")
    print(f"Australian words found: {len(handler.au_words)}")
    print(f"Māori words found: {len(handler.maori_words)}")
    print("----------------")
    print("Script finished.")
    print("\nReminder: You need to download the English Wiktionary dump ")
    print("(enwiktionary-latest-pages-articles.xml.bz2) separately.")
    print("The generated files are 'raw' lists and may need further cleaning ")
    print("by the generate_wordlists.py script.") 