// static/script.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Get DOM Elements (Combined from both blocks) ---
    const submitButton = document.getElementById('submit-guess');
    const messageArea = document.getElementById('message-area');
    const scoreDisplay = document.getElementById('score');
    const rankDisplay = document.getElementById('rank');
    // Found Words Modal Elements (Original)
    const foundWordsList = document.getElementById('found-words-list'); // Still needed? Check usage
    const foundWordsCountSpan = document.getElementById('found-words-count');
    const showFoundWordsButton = document.getElementById('show-found-words-button');
    const foundWordsModal = document.getElementById('found-words-modal');
    const modalFoundWordsList = document.getElementById('modal-found-words-list'); // Inside found words modal
    const modalCloseButton = foundWordsModal?.querySelector('.modal-close-button'); // Found words modal close
    // Game Info Elements (Original)
    const totalWordsDisplay = document.getElementById('total-words');
    const wordsRemainingDisplay = document.getElementById('words-remaining');
    // Hive Elements (Original & New)
    const hiveCellGroups = document.querySelectorAll('.hive-cell-group'); // General selector, may need refinement
    const currentGuessDisplay = document.getElementById('current-guess-display');
    const deleteButton = document.getElementById('delete-char');
    const shuffleButton = document.getElementById('shuffle-letters');
    const hiveSvg = document.getElementById('hive-svg'); // Used by New
    const outerSegmentsGroup = hiveSvg?.querySelector('.outer-segments-group'); // Used by New
    const centerGroup = hiveSvg?.querySelector('.center-group'); // Used by Original & New
    // Ticker (Original)
    const recentWordsTicker = document.getElementById('recent-words-ticker');
    // Settings Modal Elements (Original)
    const settingsButton = document.getElementById('settings-button');
    const settingsModal = document.getElementById('settings-modal');
    const settingsCloseButton = settingsModal?.querySelector('.settings-close-button');
    // Dictionary Modal Elements (New)
    const newGameBtn = document.getElementById('new-game-button'); // Renamed for clarity, was newGameButton
    const dictionaryModal = document.getElementById('dictionary-modal'); // New modal element
    const dictionaryModalCloseBtn = document.getElementById('dictionary-modal-close-btn'); // New close button
    const dictionaryConfirmBtn = document.getElementById('confirm-start-game-btn'); // New confirm button
    const dictOptionsContainer = document.getElementById('dictionary-options-container'); // Checkbox container
    const dictLoadingDiv = document.getElementById('dictionary-options-loading'); // Loading indicator
    const dictErrorDiv = document.getElementById('dictionary-options-error'); // Error display

    // --- Constants & State (Combined) ---
    const MAX_TICKER_WORDS = 7;
    let currentGuess = '';

    // --- Initial Checks for Core Elements ---
    // Add checks for elements critical for basic function or the new flow
    if (!submitButton || !messageArea || !scoreDisplay || !rankDisplay || !currentGuessDisplay || !deleteButton || !shuffleButton || !hiveSvg || !newGameBtn) {
         console.error("Core game elements not found! Functionality may be limited.");
         // Maybe disable buttons?
         return;
    }
     if (!dictionaryModal || !dictionaryModalCloseBtn || !dictionaryConfirmBtn || !dictOptionsContainer || !dictLoadingDiv || !dictErrorDiv) {
        console.error("Dictionary modal elements are missing. New Game flow via modal disabled.");
        if (newGameBtn) newGameBtn.disabled = true; // Disable button if modal is broken
    }
    if (!outerSegmentsGroup || !centerGroup) {
        console.error("SVG group elements (.outer-segments-group, .center-group) not found. Display/Animation may fail.");
    }
    if (!foundWordsModal || !modalCloseButton) {
        console.warn("Found words modal elements not found.");
    }
     if (!settingsModal || !settingsCloseButton) {
        console.warn("Settings modal elements not found.");
    }


    // --- Helper Functions (Original - Updated Shuffle) ---

    const updateGuessDisplay = () => {
        if (currentGuess) {
            currentGuessDisplay.textContent = currentGuess.toUpperCase();
        } else {
            // Keep placeholder structure for height consistency
            currentGuessDisplay.innerHTML = '<span>&nbsp;</span>';
        }
    };

    // Click handler for letter segments/center
    const handleLetterClick = (event) => {
        // Use currentTarget to ensure we get the element the listener was attached to (the <g>)
        const letter = event.currentTarget.getAttribute('data-letter');
        if (letter) {
            currentGuess += letter;
            updateGuessDisplay();
            // Optional: Add visual feedback (like slight scale) on click via CSS :active state if desired
        }
    };

    const deleteLastChar = () => {
        if (currentGuess.length > 0) {
            currentGuess = currentGuess.slice(0, -1);
            updateGuessDisplay();
        }
    };

    // *** UPDATED Shuffle Logic ***
    const shuffleLetters = () => {
        if (!hiveSvg) return; // Guard against missing SVG

        // 1. Get all current outer letter text elements using their IDs
        const outerLetterElements = Array.from(hiveSvg.querySelectorAll('[id^="outer-letter-"]'));

        if (outerLetterElements.length === 0) {
            console.warn("Shuffle: No outer letter elements found with expected IDs.");
            return;
        }

        // 2. Extract the letters from their text content
        let letters = outerLetterElements.map(el => el.textContent.trim()).filter(Boolean); // Get current letters, ignore empty

        if (letters.length === 0) {
             console.warn("Shuffle: No letters found in outer elements.");
             return;
        }

        // 3. Shuffle the extracted letters array (Fisher-Yates)
        for (let i = letters.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [letters[i], letters[j]] = [letters[j], letters[i]];
        }

        // 4. Update the text content of each element with the shuffled letters
        // Also update the `data-letter` attribute on the PARENT `g` element for the click handler
        outerLetterElements.forEach((textElement, index) => {
            const parentGroup = textElement.closest('.outer-segment-group'); // Find parent group
            if (parentGroup && index < letters.length) {
                const newLetter = letters[index];
                textElement.textContent = newLetter.toUpperCase();
                parentGroup.setAttribute('data-letter', newLetter.toLowerCase()); // Update data-letter on group
            }
        });
         console.log("Letters shuffled.");
    };


    // Found Words Modal (Original)
    const openFoundWordsModal = () => {
        if(foundWordsModal) foundWordsModal.classList.add('modal-open');
    };
    const closeFoundWordsModal = () => {
        if(foundWordsModal) foundWordsModal.classList.remove('modal-open');
    };

    // Settings Modal (Original)
    const openSettingsModal = () => {
        if(settingsModal) settingsModal.classList.add('modal-open');
    };
    const closeSettingsModal = () => {
        if(settingsModal) settingsModal.classList.remove('modal-open');
    };

    // Submit Guess (Original - Minor adjustments possible)
    const submitGuess = async () => {
        const guess = currentGuess.trim().toLowerCase();
        if (!guess) return;

        // Disable button during submission?
        if(submitButton) submitButton.disabled = true;

        try {
            const response = await fetch('/guess', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ guess: guess }),
            });

            if (!response.ok) {
                 const errorData = await response.json().catch(() => ({})); // Try to get error message
                 throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log("Guess Backend response:", result);

            if(messageArea) {
                messageArea.textContent = result.message;
                messageArea.className = `message-${result.status}`; // Apply status class

                // Auto-clear message after a delay (except for final 'Queen Bee' message)
                if (result.status !== 'finished') {
                    setTimeout(() => {
                        // Only clear if the message hasn't changed in the meantime
                        if (messageArea.textContent === result.message) {
                           messageArea.textContent = '';
                           messageArea.className = '';
                        }
                    }, 3000);
                }
            }

            // Update score and rank displays safely
            if (scoreDisplay) scoreDisplay.textContent = result.score;
            if (rankDisplay) rankDisplay.textContent = result.rank;

            // Update remaining words count safely
            if (totalWordsDisplay && wordsRemainingDisplay && result.found_words_count !== undefined) {
                const totalWords = parseInt(totalWordsDisplay.textContent, 10); // Get current total
                 if (!isNaN(totalWords)) {
                     wordsRemainingDisplay.textContent = totalWords - result.found_words_count;
                 }
            }
             if (foundWordsCountSpan && result.found_words_count !== undefined) {
                 foundWordsCountSpan.textContent = result.found_words_count;
             }


            // Update Found Words List in Modal (Original logic seems okay)
            if (modalFoundWordsList && result.found_words) {
                modalFoundWordsList.innerHTML = ''; // Clear existing list
                result.found_words.forEach(word => {
                    const li = document.createElement('li');
                    li.textContent = word.toUpperCase();
                    li.setAttribute('data-word', word);
                    li.addEventListener('click', handleFoundWordClickForDefinition); // Attach definition handler
                    modalFoundWordsList.appendChild(li);
                });
            }

            // Update Ticker (Original logic seems okay)
            if (recentWordsTicker && result.status === 'valid') {
                const placeholder = recentWordsTicker.querySelector('.ticker-placeholder');
                if (placeholder) placeholder.remove();

                const wordSpan = document.createElement('span');
                wordSpan.textContent = guess.toUpperCase();
                recentWordsTicker.prepend(wordSpan);

                while (recentWordsTicker.children.length > MAX_TICKER_WORDS) {
                    recentWordsTicker.removeChild(recentWordsTicker.lastChild);
                }
            }

            // Clear guess input ONLY on success or specific known invalid states
             if (result.status === 'valid' ||
                 result.status === 'finished' ||
                 result.message === 'Already found!') // Add more conditions if needed
             {
                 currentGuess = '';
                 updateGuessDisplay();
            }

        } catch (error) {
            console.error('Error submitting guess:', error);
            if(messageArea) {
                messageArea.textContent = `Error: ${error.message}`;
                messageArea.className = 'message-error';
            }
        } finally {
             if(submitButton) submitButton.disabled = false; // Re-enable button
        }
    };

    // Helper for definition fetching (extracted from submitGuess)
    const handleFoundWordClickForDefinition = async (event) => {
        const targetLi = event.currentTarget;
        const existingDefinitionDiv = targetLi.querySelector('.definition-display');

        // Toggle off
        if (existingDefinitionDiv) {
            existingDefinitionDiv.remove();
            return;
        }

        // Remove others
        const allDefinitionDivs = modalFoundWordsList?.querySelectorAll('.definition-display');
        allDefinitionDivs?.forEach(div => div.remove());

        const wordToDefine = targetLi.getAttribute('data-word');
        if (!wordToDefine) return;

        // Create and append display div
        const definitionDiv = document.createElement('div');
        definitionDiv.className = 'definition-display';
        definitionDiv.textContent = 'Loading definition...';
        targetLi.appendChild(definitionDiv);

        try {
            const response = await fetch(`/definition/${wordToDefine}`);
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.message || 'Failed to fetch definition');
            }
            const data = await response.json();
            // Check if div still exists before updating
            const currentDefinitionDiv = targetLi.querySelector('.definition-display');
            if (currentDefinitionDiv) {
                 currentDefinitionDiv.textContent = data.definition || 'Definition not available.';
            }
        } catch (error) {
            console.error("Definition fetch error:", error);
             const currentDefinitionDiv = targetLi.querySelector('.definition-display');
             if (currentDefinitionDiv) {
                currentDefinitionDiv.textContent = `Error: ${error.message}`;
             }
        }
    };


    // --- Helper Functions (New Game Flow) ---

    async function populateDictionaryOptions() {
        if(!dictOptionsContainer || !dictLoadingDiv || !dictErrorDiv || !dictionaryConfirmBtn) return; // Guard

        dictLoadingDiv.style.display = 'block';
        dictErrorDiv.style.display = 'none';
        dictOptionsContainer.querySelectorAll('label').forEach(el => el.remove()); // Clear old options

        try {
            const response = await fetch('/get_dictionary_options');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();

            if (data.options && data.selected) {
                if (data.options.length === 0) {
                     dictErrorDiv.textContent = 'No word lists available.';
                     dictErrorDiv.style.display = 'block';
                     dictionaryConfirmBtn.disabled = true;
                     return;
                }
                data.options.forEach(option => {
                    const label = document.createElement('label');
                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.value = option;
                    checkbox.id = `dict-opt-${option}`;
                    checkbox.name = 'dictionary_selection';
                    if (data.selected.includes(option)) checkbox.checked = true;
                    label.appendChild(checkbox);
                    label.appendChild(document.createTextNode(` ${option.charAt(0).toUpperCase() + option.slice(1)}`));
                    dictOptionsContainer.appendChild(label);
                });
                 dictionaryConfirmBtn.disabled = false;
            } else {
                throw new Error('Invalid data format received from server.');
            }
        } catch (error) {
            console.error("Error fetching dictionary options:", error);
            dictErrorDiv.textContent = `Error loading word lists: ${error.message}.`;
            dictErrorDiv.style.display = 'block';
            dictionaryConfirmBtn.disabled = true;
        } finally {
            dictLoadingDiv.style.display = 'none';
        }
    }

    function prepareAndRunAnimation(outerLetters, centerLetter) {
        if (!outerSegmentsGroup || !centerGroup || !Array.isArray(outerLetters) || outerLetters.length !== 6 || !centerLetter) {
            console.error("Cannot run animation: Missing elements or invalid letter data.", { outerLetters, centerLetter });
            if (messageArea) messageArea.textContent = "Error updating display.";
            return;
        }
        console.log("Starting animation with:", outerLetters, centerLetter);

        // 1. Clear Letters & UI, Apply 'hidden'
        const allLetterTexts = hiveSvg.querySelectorAll('.hive-letter');
        allLetterTexts.forEach(el => {
            el.textContent = '';
            el.classList.add('hidden');
        });
        if (scoreDisplay) scoreDisplay.textContent = '0';
        if (rankDisplay) rankDisplay.textContent = 'Beginner';
        if (messageArea) messageArea.textContent = '';
        if (currentGuessDisplay) currentGuessDisplay.innerHTML = '<span>&nbsp;</span>'; // Reset guess display
        currentGuess = ''; // Reset internal guess state
        // Reset found words modal list and counts
        if (modalFoundWordsList) modalFoundWordsList.innerHTML = '';
        if (foundWordsCountSpan) foundWordsCountSpan.textContent = '0';
        // Reset remaining words (needs total words, maybe fetch that too?)
        // if (wordsRemainingDisplay && totalWordsDisplay) wordsRemainingDisplay.textContent = totalWordsDisplay.textContent;
        if (recentWordsTicker) recentWordsTicker.innerHTML = '<span class="ticker-placeholder">&nbsp;</span>'; // Reset ticker


        // 2. Trigger Spin
        outerSegmentsGroup.classList.add('spinning');

        // 3. Set timeout
        const spinDuration = 1500;
        setTimeout(() => {
            outerSegmentsGroup.classList.remove('spinning');

            // 4. Populate Outer Letters
            let revealDelay = 200;
            outerLetters.forEach((letter, index) => {
                setTimeout(() => {
                    const textElement = hiveSvg.querySelector(`#outer-letter-${index}`);
                    const parentGroup = textElement?.closest('.outer-segment-group');
                    if (textElement && parentGroup) {
                        textElement.textContent = letter.toUpperCase();
                        parentGroup.setAttribute('data-letter', letter.toLowerCase()); // Update data-letter for clicks
                        textElement.classList.remove('hidden');
                        console.log(`Revealed outer ${index}: ${letter}`);
                    } else {
                        console.warn(`Could not find text element/group for outer-letter-${index}`);
                    }
                }, index * revealDelay);
            });

            // 5. Populate Center Letter
            const centerTextElement = centerGroup.querySelector('.center-letter');
            const centerParentGroup = centerGroup; // Center group itself has data-letter
            const centerRevealDelay = outerLetters.length * revealDelay + 100;
            setTimeout(() => {
                 if (centerTextElement && centerParentGroup) {
                     centerTextElement.textContent = centerLetter.toUpperCase();
                     centerParentGroup.setAttribute('data-letter', centerLetter.toLowerCase()); // Update data-letter
                     centerTextElement.classList.remove('hidden');
                     console.log(`Revealed center: ${centerLetter}`);
                 } else {
                      console.warn(`Could not find center text element or group`);
                 }
            }, centerRevealDelay);

        }, spinDuration);
    }


    // --- Event Listeners (Original - Adapted where needed) ---

    // Keydown Listener (Original logic seems fine)
    document.addEventListener('keydown', (event) => {
        // Ignore if modifier keys are pressed or if inside an input/textarea
        if (event.metaKey || event.ctrlKey || event.altKey || event.target.matches('input, textarea')) {
            return;
        }
        // Also ignore if a modal is open
        if (dictionaryModal?.style.display !== 'none' || foundWordsModal?.classList.contains('modal-open') || settingsModal?.classList.contains('modal-open')) {
            return;
        }

        const key = event.key;

        if (key === 'Enter') {
            event.preventDefault();
            submitGuess();
        } else if (key === 'Backspace') {
            event.preventDefault();
            deleteLastChar();
        } else if (key.length === 1 && key.match(/[a-z]/i)) {
            event.preventDefault();
             // Check if the typed letter is actually in the puzzle (optional but good UX)
            const allPuzzleLetters = new Set();
             const centerLetterEl = centerGroup?.getAttribute('data-letter');
             if(centerLetterEl) allPuzzleLetters.add(centerLetterEl);
             hiveSvg?.querySelectorAll('.outer-segment-group')?.forEach(g => {
                 const letter = g.getAttribute('data-letter');
                 if(letter) allPuzzleLetters.add(letter);
             });

             if(allPuzzleLetters.size > 0 && allPuzzleLetters.has(key.toLowerCase())) {
                currentGuess += key.toLowerCase();
                updateGuessDisplay();
             } else if (allPuzzleLetters.size === 0) {
                 // Allow typing if letters aren't loaded yet? Or handle differently.
                 currentGuess += key.toLowerCase();
                 updateGuessDisplay();
             } else {
                 // Maybe flash an error or shake the input briefly? For now, just ignore.
                 console.log(`Ignoring key '${key}', not in puzzle letters.`);
             }
        }
    });

    // Button Listeners (Original)
    if(submitButton) submitButton.addEventListener('click', submitGuess);
    if(deleteButton) deleteButton.addEventListener('click', deleteLastChar);
    if(shuffleButton) shuffleButton.addEventListener('click', shuffleLetters);

    // Letter Click Listeners (Original - applied to groups)
    // Note: These need to be applied *after* letters are populated by animation too,
    // or applied dynamically. Applying once to hiveSvg and checking target might be better.

    // Re-attach click listeners to letter groups (center and outer)
    // Doing it once on the SVG container is more efficient if structure is stable
    if (hiveSvg) {
        hiveSvg.addEventListener('click', (event) => {
            // Find the closest ancestor group with data-letter
            const targetGroup = event.target.closest('.hive-cell-group[data-letter]');
            if (targetGroup) {
                handleLetterClick({ currentTarget: targetGroup }); // Simulate event object for handler
            }
        });
    } else { // Fallback: Attach individually if SVG listener fails
         if (centerGroup) centerGroup.addEventListener('click', handleLetterClick);
         // Add listeners to outer groups as they are created/updated if needed,
         // but the SVG delegation above is preferred.
    }


    // Found Words Modal Listeners (Original)
    if(showFoundWordsButton) showFoundWordsButton.addEventListener('click', openFoundWordsModal);
    if(modalCloseButton) modalCloseButton.addEventListener('click', closeFoundWordsModal);
    if(foundWordsModal) {
        foundWordsModal.addEventListener('click', (event) => {
            if (event.target === foundWordsModal) closeFoundWordsModal();
        });
    }

    // Settings Modal Listeners (Original)
    if(settingsButton) settingsButton.addEventListener('click', openSettingsModal);
    if(settingsCloseButton) settingsCloseButton.addEventListener('click', closeSettingsModal);
    if(settingsModal) {
        settingsModal.addEventListener('click', (event) => {
            if (event.target === settingsModal) closeSettingsModal();
        });
    }

    // --- Event Listeners (New Game Flow - Replaces old /new_game redirect) ---
    if (newGameBtn) {
        newGameBtn.addEventListener('click', (event) => {
            event.preventDefault(); // Prevent default button action
            if(dictionaryModal) { // Only proceed if modal exists
                populateDictionaryOptions(); // Fetch/show options
                dictionaryModal.style.display = 'flex'; // Show modal
            } else {
                 console.error("Cannot open dictionary modal - element not found.");
                 // Fallback? Simple reload?
                 // window.location.reload();
            }
        });
    } else {
        console.warn("New Game button not found, modal flow cannot be initiated.");
    }

    // Dictionary Modal Listeners (New)
    if(dictionaryModalCloseBtn) {
        dictionaryModalCloseBtn.addEventListener('click', () => {
            if(dictionaryModal) dictionaryModal.style.display = 'none';
        });
    }
    if(dictionaryConfirmBtn) {
        dictionaryConfirmBtn.addEventListener('click', async () => { // Already defined async, just ensure it exists
            const selectedDicts = [];
            dictOptionsContainer?.querySelectorAll('input[type="checkbox"][name="dictionary_selection"]:checked').forEach(cb => {
                selectedDicts.push(cb.value);
            });

            if (selectedDicts.length === 0) {
                 if(dictErrorDiv) {
                     dictErrorDiv.textContent = 'Please select at least one word list.';
                     dictErrorDiv.style.display = 'block';
                     setTimeout(() => { if(dictErrorDiv) dictErrorDiv.style.display = 'none';}, 3000);
                 }
                 return;
            }

            dictionaryConfirmBtn.disabled = true;
            dictionaryConfirmBtn.textContent = 'Starting...';
            if(dictErrorDiv) dictErrorDiv.style.display = 'none';

            try {
                const response = await fetch('/start_game', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ dictionaries: selectedDicts })
                });
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || `Failed to start game (Status: ${response.status})`);

                if (data.success && data.outer_letters && data.center_letter) {
                    if(dictionaryModal) dictionaryModal.style.display = 'none';
                    prepareAndRunAnimation(data.outer_letters, data.center_letter);
                    if(messageArea) {
                        messageArea.textContent = "New game started!";
                        setTimeout(() => { if (messageArea?.textContent === "New game started!") messageArea.textContent = ''; }, 2000);
                    }
                } else {
                    throw new Error(data.error || 'Invalid response data received.');
                }
            } catch (error) {
                console.error("Error starting game:", error);
                if(dictErrorDiv) {
                    dictErrorDiv.textContent = `Error: ${error.message}`;
                    dictErrorDiv.style.display = 'block';
                }
            } finally {
                 dictionaryConfirmBtn.disabled = false;
                 dictionaryConfirmBtn.textContent = 'Start New Game';
            }
        });
    }

    // --- Initial UI Setup ---
    if(currentGuessDisplay) currentGuessDisplay.focus(); // Focus guess display on load
    updateGuessDisplay(); // Ensure guess display is correct on load

    console.log("Spelling Bee script initialized.");

}); // End DOMContentLoaded