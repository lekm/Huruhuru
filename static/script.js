document.addEventListener('DOMContentLoaded', () => {
    // --- Get DOM Elements (Using IDs for robustness) ---
    const submitButton = document.getElementById('submit-guess');
    const messageArea = document.getElementById('message-area');
    const scoreDisplay = document.getElementById('score');
    const rankDisplay = document.getElementById('rank');
    const foundWordsList = document.getElementById('found-words-list');
    const foundWordsCountSpan = document.getElementById('found-words-count');
    const showFoundWordsButton = document.getElementById('show-found-words-button');
    const foundWordsModal = document.getElementById('found-words-modal');
    const modalFoundWordsList = document.getElementById('modal-found-words-list');
    const modalCloseButton = foundWordsModal?.querySelector('.modal-close-button');
    const totalWordsDisplay = document.getElementById('total-words');
    const wordsRemainingDisplay = document.getElementById('words-remaining');
    const currentGuessDisplay = document.getElementById('current-guess-display');
    const deleteButton = document.getElementById('delete-char');
    const shuffleButton = document.getElementById('shuffle-letters');
    const hiveSvg = document.getElementById('hive-svg'); // Main SVG container
    const centerGroup = document.getElementById('center-group'); // Use ID
    const outerSegmentsGroup = document.getElementById('outer-segments-group'); // Use ID
    const spinningPart = document.getElementById('spinning-part'); // Use ID
    const dictStatsListContainer = document.getElementById('dict-stats-list'); // Use ID
    const recentWordsTicker = document.getElementById('recent-words-ticker');
    const newGameBtn = document.getElementById('new-game-button');
    const dictionaryModal = document.getElementById('dictionary-modal');
    const dictionaryModalCloseBtn = document.getElementById('dictionary-modal-close-btn');
    const dictionaryConfirmBtn = document.getElementById('confirm-start-game-btn');
    const dictOptionsContainer = document.getElementById('dictionary-options-container');
    const dictLoadingDiv = document.getElementById('dictionary-options-loading');
    const dictErrorDiv = document.getElementById('dictionary-options-error');
    const rankClickableArea = document.getElementById('rank-clickable-area');
    const ranksModal = document.getElementById('ranks-modal');
    const ranksModalCloseBtn = ranksModal?.querySelector('.modal-close-button');
    const ranksList = document.getElementById('ranks-list');
    
    // --- Log selected elements for verification ---
    // Log only a few key ones to avoid overly verbose logs
    console.log("Selected container elements:", { hiveSvg, centerGroup, outerSegmentsGroup, spinningPart, dictStatsListContainer });

    // --- Constants & State (Combined) ---
    const MAX_TICKER_WORDS = 7;
    let currentGuess = '';
    let currentValidLettersSet = new Set(); // <<< ADDED: State for valid letters for input validation
    let currentGameTotalScore = 0; // <<< ADDED: State for total score for rank calculation
    // Define Kiwi Ranks in JS for modal display
    const KIWI_RANKS_JS = {
        0.00: "Egg",
        0.03: "Bit Useless, Eh",
        0.08: "Not Bad, Bro",
        0.15: "Sweet As",
        0.25: "On the Piss",
        0.40: "Full Noise",
        0.60: "Bloody Weapon",
        0.80: "Choice Cunt",
        1.00: "King Shit"
    };
    const SORTED_KIWI_THRESHOLDS_JS = Object.keys(KIWI_RANKS_JS).map(Number).sort((a, b) => a - b);

    // --- Initial Checks for Core Elements --- >
    console.log("Checking for core elements...");
    const coreElements = {
        submitButton,
        messageArea,
        scoreDisplay, // <<< Might be missing if no game started?
        rankDisplay, // <<< Might be missing if no game started?
        currentGuessDisplay,
        deleteButton,
        shuffleButton,
        hiveSvg,
        newGameBtn
    };
    let missingElement = false;
    for (const [key, element] of Object.entries(coreElements)) {
        if (!element) {
            console.error(`Core element MISSING: ${key}`);
            missingElement = true;
        }
    }

    if (missingElement) {
         console.error("Core game elements not found! Functionality may be limited.");
         // Decide if we should return or just disable certain buttons
         // return;
    }
    // < ----------------------------------
    
    // --- Check for dictionary modal elements --- > // Moved check later
     if (!dictionaryModal || !dictionaryModalCloseBtn || !dictionaryConfirmBtn || !dictOptionsContainer || !dictLoadingDiv || !dictErrorDiv) {
        console.error("Dictionary modal elements are missing. New Game flow via modal disabled.");
        if (newGameBtn) newGameBtn.disabled = true; // Disable button if modal is broken
    }
    // < ----------------------------------------
    
    // --- Check for SVG elements --- > // Moved check later
    // This check was around line 102 in previous versions
    /*
    if (!outerSegmentsGroup || !centerGroup || !spinningPart) { 
        // This check might be unnecessary now that containers always exist
        console.warn("Initial check: SVG container elements might not be fully ready, but proceeding.");
    }
    */
    // < ---------------------------
    
    // --- Check for Found Words modal elements --- > // Moved check later
    if (!foundWordsModal || !modalCloseButton) {
        console.warn("Found words modal elements not found.");
    }
    // < -------------------------------------------

    // Add checks for new elements
    if (!rankClickableArea || !ranksModal || !ranksModalCloseBtn || !ranksList) {
        console.warn("Rank modal elements missing, click functionality disabled.");
    }

    // Add a global variable or make metadata accessible if needed later for UI rebuilds
    let GLOBAL_DICT_METADATA = {}; // Store metadata fetched during game start

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
        const groupElement = event.currentTarget;
        console.log("handleLetterClick triggered for element:", groupElement);
        const letter = groupElement.getAttribute('data-letter');
        console.log(`Letter found in data-letter: '${letter}'`);

        if (letter) {
            currentGuess += letter;
            updateGuessDisplay();
            console.log(`Current guess updated: '${currentGuess}'`);
        } else {
            console.warn("No data-letter attribute found on clicked group:", groupElement);
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
    // REMOVED Settings modal helper functions
    // const openSettingsModal = () => {
    //    if(settingsModal) settingsModal.classList.add('modal-open');
    // };
    // const closeSettingsModal = () => {
    //    if(settingsModal) settingsModal.classList.remove('modal-open');
    // };

    // Submit Guess (Original - Minor adjustments possible)
    const submitGuess = async () => {
        const guessInput = document.getElementById('current-guess-display');
        const guess = guessInput.textContent.trim(); // Get text content
        const messageArea = document.getElementById('message-area');
        
        if (!guess) {
            // Maybe show a message or just ignore empty submission
            return;
        }

        try {
            const response = await fetch('/guess', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ guess: guess }),
            });
            const result = await response.json();

            // Update message area
            messageArea.textContent = result.message;
            messageArea.className = result.valid ? 'message-valid' : (result.message.includes('letter') || result.message.includes('short') ? 'message-invalid' : 'message-error'); // Use error for 'Not a word' etc.

            if (result.valid) {
                // Update Score and Rank (Top Panel)
                const scoreElement = document.getElementById('score');
                const rankElement = document.getElementById('rank');
                if (scoreElement) scoreElement.textContent = result.score;
                if (rankElement) rankElement.textContent = result.rank;

                // Update Per-Dictionary Stats (Bottom Panel)
                if (result.updated_list_type && result.new_found_count !== undefined) {
                    const listKey = result.updated_list_type;
                    const newFound = result.new_found_count;
                    
                    // Find the specific dictionary item container
                    const dictItemElement = document.querySelector(`.dict-stat-item[data-list-key="${listKey}"]`);
                    if (dictItemElement) {
                        const foundCountElement = dictItemElement.querySelector(`#found-count-${listKey}`);
                        const totalCountElement = dictItemElement.querySelector('.dict-total-count'); // Need total to calc remaining

                        if (foundCountElement) foundCountElement.textContent = newFound;
                    }
                }
                
                // Update Found Words Button Count
                updateFoundWordsButtonCount(); // Call reusable function

                // *** Add word to modal list dynamically ***
                const modalList = document.getElementById('modal-found-words-list');
                if (modalList) {
                    const listItem = document.createElement('li');
                    listItem.textContent = result.word.toUpperCase();
                    listItem.setAttribute('data-word', result.word);
                    // Add the click listener for definitions
                    listItem.addEventListener('click', handleFoundWordClickForDefinition);
                    // Append and potentially sort?
                    modalList.appendChild(listItem);
                    // Optional: Sort the list alphabetically after adding
                    const items = Array.from(modalList.children);
                    items.sort((a, b) => a.textContent.localeCompare(b.textContent));
                    items.forEach(item => modalList.appendChild(item)); // Re-append in sorted order
                }

                // Add word to recent words ticker
                addWordToTicker(result.word, result.is_pangram);

                // Clear input field
                clearGuessDisplay();
                
                // If game finished, maybe disable input?
                if (result.all_found) {
                    // Optional: Disable further input
                    messageArea.className = 'message-finished'; 
                }

            } else {
                // Invalid guess - still clear the display
                clearGuessDisplay(); 
                // Optionally shake the input or give other feedback (can keep this)
                // Example: Add a temporary class for shaking
                // const guessDisplayElement = document.getElementById('current-guess-display');
                // if (guessDisplayElement) {
                //     guessDisplayElement.classList.add('shake');
                //     setTimeout(() => guessDisplayElement.classList.remove('shake'), 500);
                // }
            }
        } catch (error) {
            console.error('Error submitting guess:', error);
            messageArea.textContent = 'Error submitting guess. Check connection.';
            messageArea.className = 'message-error';
            // Also clear display on fetch error
            clearGuessDisplay();
        }
    };

    // Helper for definition fetching (extracted from submitGuess)
    const handleFoundWordClickForDefinition = async (event) => {
        console.log("handleFoundWordClickForDefinition triggered"); // <<< LOG 1
        const targetLi = event.currentTarget;
        const definitionArea = document.getElementById('modal-definition-area');
        if (!definitionArea) {
            console.error("Definition display area (#modal-definition-area) not found!");
            return;
        }
        console.log("Definition area found:", definitionArea); // <<< LOG 2

        // --- Highlighting Logic --- >
        // Remove highlight from previously selected word
        const previouslySelected = modalFoundWordsList?.querySelector('.selected-word');
        if (previouslySelected) {
            previouslySelected.classList.remove('selected-word');
        }
        // Add highlight to clicked word
        targetLi.classList.add('selected-word');
        // < -----------------------

        const wordToDefine = targetLi.getAttribute('data-word');
        console.log(`Word to define (from data-word): ${wordToDefine}`); // <<< LOG 3
        if (!wordToDefine) {
            definitionArea.innerHTML = '<p class="placeholder error">Could not identify word to define.</p>';
            return;
        }

        // Update the dedicated definition area
        definitionArea.innerHTML = '<p class="placeholder loading">Loading definition...</p>'; // Use loading class
        console.log("Set definition area to loading..."); // <<< LOG 4

        try {
            const fetchUrl = `/definition/${wordToDefine}`;
            console.log(`Fetching definition from: ${fetchUrl}`); // <<< LOG 5
            const response = await fetch(fetchUrl);
            console.log(`Fetch response status: ${response.status}`); // <<< LOG 6
            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                const errorMsg = errData.error || `HTTP error ${response.status}`;
                console.error("Fetch error:", errorMsg); // <<< LOG 7
                throw new Error(errorMsg); // Use backend error if available
            }
            const data = await response.json();
            console.log("Received definition data:", data); // <<< LOG 8

            // Update definition area with actual definition
            definitionArea.innerHTML = ''; // Clear loading message
            const definitionP = document.createElement('p');
            definitionP.textContent = data.definition || 'Definition not available.';
            definitionArea.appendChild(definitionP);
            console.log("Updated definition area with content."); // <<< LOG 9

        } catch (error) {
            console.error("Definition fetch error (in catch block):", error); // <<< LOG 10
            // Update definition area with error message
            definitionArea.innerHTML = `<p class="placeholder error">Error: ${error.message}</p>`;
        }
    };


    // --- Helper Functions (New Game Flow) ---

    async function populateDictionaryOptions() {
        if(!dictOptionsContainer || !dictLoadingDiv || !dictErrorDiv || !dictionaryConfirmBtn) return; // Guard

        // *** Explicitly clear any previous error messages ***
        dictErrorDiv.textContent = '';
        dictErrorDiv.style.display = 'none';
        // *** ------------------------------------------ ***

        dictLoadingDiv.style.display = 'block';
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
                data.options.forEach(optionData => {
                    const label = document.createElement('label');
                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.value = optionData.id;
                    checkbox.id = `dict-opt-${optionData.id}`;
                    checkbox.name = 'dictionary_selection';
                    if (data.selected.includes(optionData.id)) checkbox.checked = true;
                    if (!optionData.optional) checkbox.disabled = true;

                    label.appendChild(checkbox);
                    
                    // Create icon element based on type
                    let iconElement = null;
                    if (optionData.icon_value) {
                        if (optionData.icon_type === 'image') {
                            iconElement = document.createElement('img');
                            iconElement.src = optionData.icon_value;
                            iconElement.alt = optionData.label; // Alt text
                            iconElement.classList.add('dict-icon-img'); // Class for styling
                            iconElement.setAttribute('loading', 'lazy'); // Improve performance
                        } else { // Default to emoji (treat as text)
                            iconElement = document.createElement('span');
                            iconElement.classList.add('dict-icon-emoji'); // Class for styling
                            iconElement.textContent = optionData.icon_value + ' '; // Add space after emoji
                        }
                    }

                    // Append icon if it was created
                    if (iconElement) {
                        label.appendChild(iconElement);
                    }

                    // Append label text
                    const textSpan = document.createElement('span');
                    textSpan.textContent = optionData.label; // Use the simplified label
                    label.appendChild(textSpan);
                    
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

    // --- REFACTORED Animation Logic --- 
    function prepareAndRunAnimation(outerLetters, centerLetter) {
        // Select target containers by ID
        const targetCenterGroup = document.getElementById('center-group');
        const targetSpinningPart = document.getElementById('spinning-part'); // Outer letters go inside here
        const targetHiveSvg = document.getElementById('hive-svg'); // Needed for geometry calc

        // Validate elements and data needed for dynamic creation
        if (!targetCenterGroup || !targetSpinningPart || !targetHiveSvg || !Array.isArray(outerLetters) || outerLetters.length !== 6 || !centerLetter) {
            console.error("Cannot run animation: Missing target elements or invalid letter data.", 
                          {targetCenterGroup, targetSpinningPart, targetHiveSvg, outerLetters, centerLetter});
            if (messageArea) {
                 messageArea.textContent = "Error updating display.";
                 messageArea.className = 'message-error';
            }
            return;
        }
        
        // --- Geometry Calculation (Needs to match backend logic) --- 
        function getSegmentGeometry(index, numSegments) {
            const viewBoxWidth = 150; // Assuming viewBox ~0 0 150 150 based on template
            const viewBoxHeight = 150;
            const viewBox_center_x = viewBoxWidth / 2;
            const viewBox_center_y = viewBoxHeight / 2;
            const center_radius = 25;
            const outer_ring_end_radius = 65;
            const letter_radius = center_radius + (outer_ring_end_radius - center_radius) / 2;
            const segment_angle_deg = 360 / numSegments;
            const segment_angle_rad = (Math.PI / 180) * segment_angle_deg;
            const start_angle_offset_rad = (Math.PI / 180) * (-90 - (segment_angle_deg / 2)); // Align first segment top
            
            const current_angle_rad = start_angle_offset_rad + index * segment_angle_rad;
            const next_angle_rad = current_angle_rad + segment_angle_rad;
            const letter_angle_rad = current_angle_rad + (segment_angle_rad / 2);

            const letter_x = letter_radius * Math.cos(letter_angle_rad);
            const letter_y = letter_radius * Math.sin(letter_angle_rad);
            
            const start_cx = center_radius * Math.cos(current_angle_rad);
            const start_cy = center_radius * Math.sin(current_angle_rad);
            const start_ox = outer_ring_end_radius * Math.cos(current_angle_rad);
            const start_oy = outer_ring_end_radius * Math.sin(current_angle_rad);
            const end_ox = outer_ring_end_radius * Math.cos(next_angle_rad);
            const end_oy = outer_ring_end_radius * Math.sin(next_angle_rad);
            const end_cx = center_radius * Math.cos(next_angle_rad);
            const end_cy = center_radius * Math.sin(next_angle_rad);
            const large_arc_flag = 0;
            const sweep_flag_outer = 1;
            const sweep_flag_inner = 0;
            const fmt = (num) => num.toFixed(2);
            
            const path_d = `M ${fmt(start_cx)} ${fmt(start_cy)} L ${fmt(start_ox)} ${fmt(start_oy)} A ${fmt(outer_ring_end_radius)} ${fmt(outer_ring_end_radius)} 0 ${large_arc_flag} ${sweep_flag_outer} ${fmt(end_ox)} ${fmt(end_oy)} L ${fmt(end_cx)} ${fmt(end_cy)} A ${fmt(center_radius)} ${fmt(center_radius)} 0 ${large_arc_flag} ${sweep_flag_inner} ${fmt(start_cx)} ${fmt(start_cy)} Z`;

            // --- ADD LOGGING --- >
            console.log(`[getSegmentGeometry ${index}] x: ${fmt(letter_x)}, y: ${fmt(letter_y)}, path d starts: ${path_d.substring(0, 20)}...`);
            // < -------------------
            
            return { x: fmt(letter_x), y: fmt(letter_y), segment_path: path_d };
        }
        // --- End Geometry Calculation ---

        console.log("Starting animation with:", outerLetters, centerLetter);

        // 1. Clear previous content from containers
        targetCenterGroup.innerHTML = ''; 
        targetSpinningPart.innerHTML = ''; 
        targetCenterGroup.removeAttribute("data-letter"); // Clear old data-letter
        
        // Reset other UI elements if needed (score/rank are handled by updateUIForNewGame)
        if (currentGuessDisplay) currentGuessDisplay.innerHTML = '<span>&nbsp;</span>';
        currentGuess = '';
        
        // --- Force Reflow (Attempt to fix animation timing) --- >
        void targetSpinningPart.offsetHeight; // Reading offsetHeight forces reflow
        // < ---------------------------------------------------

        // 2. Trigger Spin Animation
        console.log("Adding .spinning class to:", targetSpinningPart); // Log before adding
        targetSpinningPart.classList.add('spinning');
        console.log("Class list after add:", targetSpinningPart.classList); // Log after adding

        // 3. Set timeout for post-animation population
        const spinDuration = 3000; 
        setTimeout(() => {
            console.log("Removing .spinning class from:", targetSpinningPart); // Log before removing
            targetSpinningPart.classList.remove('spinning'); // Stop visual spin
            console.log("Class list after remove:", targetSpinningPart.classList); // Log after removing

            // 4. Populate Outer Letters Dynamically
            let revealDelay = 200;
            const numSegments = outerLetters.length;
            const white_color = '#ffffff'; // Define colors locally or get from CSS vars
            const pale_yellow = '#fffacd';
            
            outerLetters.forEach((letter, index) => {
                setTimeout(() => {
                    const geometry = getSegmentGeometry(index, numSegments);
                    const svgNS = "http://www.w3.org/2000/svg";
                    
                    const outerGroup = document.createElementNS(svgNS, "g");
                    outerGroup.classList.add("hive-cell-group", "outer-segment-group");
                    outerGroup.setAttribute("data-letter", letter.toLowerCase());

                    const path = document.createElementNS(svgNS, "path");
                    path.classList.add("hive-segment-path");
                    path.setAttribute("d", geometry.segment_path); 
                    // Apply fill using JS - CSS :nth-child won't work reliably on dynamic elements
                    path.setAttribute("fill", index % 2 === 0 ? white_color : pale_yellow); 

                    const textElement = document.createElementNS(svgNS, "text");
                    textElement.classList.add("hive-letter", "outer-letter");
                    textElement.setAttribute("id", `outer-letter-${index}`);
                    textElement.setAttribute("x", geometry.x);
                    textElement.setAttribute("y", geometry.y);
                    textElement.setAttribute("text-anchor", "middle");
                    textElement.setAttribute("dominant-baseline", "middle");
                    textElement.textContent = letter.toUpperCase();
                    textElement.classList.add('hidden'); // Add hidden initially

                    outerGroup.appendChild(path);
                    outerGroup.appendChild(textElement);
                    targetSpinningPart.appendChild(outerGroup);
                    
                    // Trigger reveal transition (force reflow)
                    requestAnimationFrame(() => { 
                        requestAnimationFrame(() => { textElement.classList.remove('hidden'); }); 
                    });

                }, index * revealDelay);
            });

            // 5. Populate Center Letter Dynamically
            const centerRevealDelay = outerLetters.length * revealDelay + 100;
            setTimeout(() => {
                 const centerRadius = 25; // Assuming fixed radius, or get from config/backend
                 const svgNS = "http://www.w3.org/2000/svg";
                 
                 const centerCircle = document.createElementNS(svgNS, "circle");
                 centerCircle.classList.add("hive-cell", "center");
                 centerCircle.setAttribute("r", centerRadius.toString()); 

                 const centerTextElement = document.createElementNS(svgNS, "text");
                 centerTextElement.classList.add("hive-letter", "center-letter");
                 centerTextElement.setAttribute("x", "0");
                 centerTextElement.setAttribute("y", "0");
                 centerTextElement.setAttribute("text-anchor", "middle");
                 centerTextElement.setAttribute("dominant-baseline", "middle");
                 centerTextElement.setAttribute("dy", "0.1em");
                 centerTextElement.textContent = centerLetter.toUpperCase();
                 centerTextElement.classList.add('hidden'); // Add hidden initially

                 targetCenterGroup.appendChild(centerCircle);
                 targetCenterGroup.appendChild(centerTextElement);
                 targetCenterGroup.setAttribute("data-letter", centerLetter.toLowerCase());
                 
                 // Trigger reveal transition (force reflow)
                 requestAnimationFrame(() => { 
                     requestAnimationFrame(() => { centerTextElement.classList.remove('hidden'); });
                 });

            }, centerRevealDelay);

        }, spinDuration);
    }
    // --- End Refactored Animation Logic ---

    // --- Event Listeners (Original - Adapted where needed) ---

    // Keydown Listener (Original logic seems fine)
    document.addEventListener('keydown', (event) => {
        // Ignore if modifier keys are pressed or if inside an input/textarea
        if (event.metaKey || event.ctrlKey || event.altKey || event.target.matches('input, textarea')) {
            return;
        }
        // Also ignore if a modal is open
        // --- Updated Modal Check --- 
        const isDictionaryModalOpen = dictionaryModal?.style.display !== 'none' && dictionaryModal?.style.display !== '';
        const isFoundWordsModalOpen = foundWordsModal?.classList.contains('modal-open');
        const isRanksModalOpen = ranksModal?.classList.contains('modal-open');
        if (isDictionaryModalOpen || isFoundWordsModalOpen || isRanksModalOpen) {
             console.log("Ignoring keydown event - a modal is open.");
            return;
        }
        // --- --------------------- ---

        const key = event.key;

        if (key === 'Enter') {
            event.preventDefault();
            submitGuess();
        } else if (key === 'Backspace') {
            event.preventDefault();
            deleteLastChar();
        } else if (key.length === 1 && key.match(/[a-z]/i)) {
            event.preventDefault();
             // --- USE UPDATED STATE FOR VALIDATION --- 
             const lowerKey = key.toLowerCase();
             if (currentValidLettersSet.size > 0 && currentValidLettersSet.has(lowerKey)) {
                currentGuess += lowerKey;
                updateGuessDisplay();
             } else if (currentValidLettersSet.size === 0) {
                 // Allow typing if letters aren't loaded yet (e.g., initial page load before game start)
                 console.warn("currentValidLettersSet is empty, allowing keypress anyway (initial load?)");
                 currentGuess += lowerKey;
                 updateGuessDisplay();
             } else {
                 // Letter is not in the valid set for the current game
                 console.log(`Ignoring key '${key}', not in currentValidLettersSet:`, currentValidLettersSet);
                 // Optionally provide feedback like a slight shake
                 currentGuessDisplay?.classList.add('shake-horizontal');
                 setTimeout(() => currentGuessDisplay?.classList.remove('shake-horizontal'), 300); 
             }
             // --- --------------------------------- ---
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

    // --- Event Listeners (New Game Flow) ---
    if (newGameBtn) {
        newGameBtn.addEventListener('click', (event) => {
            // Restore original behavior: Open the dictionary modal
            event.preventDefault(); // Prevent default if it's a form button
            console.log("New Game button clicked, opening dictionary modal."); 
            if(dictionaryModal) { // Only proceed if modal exists
                 // *** Fetch options when modal is opened ***
                populateDictionaryOptions(); 
                dictionaryModal.style.display = 'flex'; // Show modal
            } else {
                 console.error("Cannot open dictionary modal - element not found.");
                 // Optionally show an error to the user
                 if (messageArea) {
                     messageArea.textContent = "Error: Cannot load game options.";
                     messageArea.className = 'message-error';
                 }
            }
        });
    }

    // Dictionary Modal Listeners (New)
    if(dictionaryModalCloseBtn) {
        dictionaryModalCloseBtn.addEventListener('click', () => {
            if(dictionaryModal) dictionaryModal.style.display = 'none';
        });
    }
    if(dictionaryConfirmBtn) {
        dictionaryConfirmBtn.addEventListener('click', async () => {
            const selectedCheckboxes = dictOptionsContainer?.querySelectorAll('input[type="checkbox"][name="dictionary_selection"]:checked');
            const selectedLists = Array.from(selectedCheckboxes).map(cb => cb.value);

            console.log("Selected dictionary values for submission:", selectedLists);

            // Validate selection client-side
            if (selectedLists.length === 0) {
                 if(dictErrorDiv) {
                     dictErrorDiv.textContent = 'Please select at least one word list.';
                     dictErrorDiv.style.display = 'block';
                     // Optionally hide after a few seconds
                     // setTimeout(() => { if(dictErrorDiv) dictErrorDiv.style.display = 'none';}, 3000);
                 }
                 return;
            }

            // --- CORRECT PAYLOAD --- 
            const payload = { selected_lists: selectedLists }; // Use the correct key 'selected_lists'
            console.log("Sending JSON payload to /start_game:", JSON.stringify(payload));

            // Disable button and clear errors
            dictionaryConfirmBtn.disabled = true;
            dictionaryConfirmBtn.textContent = 'Starting...';
            if(dictErrorDiv) {
                dictErrorDiv.textContent = '';
                dictErrorDiv.style.display = 'none';
            }

            try {
                const response = await fetch('/start_game', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload) // Send the corrected payload
                });
                
                // Get the full response data regardless of status first
                const responseData = await response.json(); 

                // Check if the response status is OK *and* the backend reported success
                if (response.ok && responseData.success) {
                    // --- CORRECT SUCCESS HANDLING --- 
                    console.log("Received success from /start_game:", responseData);
                    if(dictionaryModal) dictionaryModal.style.display = 'none'; // Close modal
                    
                    // --- UPDATE VALIDATION STATE IMMEDIATELY --- <<<<<<<<<<<<<<<<<
                    if (responseData.all_letters && Array.isArray(responseData.all_letters)) {
                        currentValidLettersSet = new Set(responseData.all_letters.map(l => l.toLowerCase()));
                        console.log("Updated currentValidLettersSet for validation:", currentValidLettersSet); 
                    } else {
                         console.error("Missing/invalid all_letters in response, cannot update validation state!");
                         currentValidLettersSet = new Set(); // Clear it on error
                    }
                    // --- ------------------------------------- --- <<<<<<<<<<<<<<<<<
                    
                    // --- UPDATE TOTAL SCORE STATE --- <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
                    if (typeof responseData.total_score === 'number') {
                        currentGameTotalScore = responseData.total_score;
                        console.log("Updated currentGameTotalScore:", currentGameTotalScore);
                    } else {
                         console.error("Missing/invalid total_score in response!");
                         currentGameTotalScore = 0; // Default to 0 on error
                    }
                    // --- ------------------------- ---
                    
                    // 1. Update the UI with the new game state data (score, rank, counts)
                    updateUIForNewGame(responseData); 
                    
                    // 2. Prepare for and Run Animation using letter data from response
                    // --- FILTER LETTERS FOR ANIMATION --- 
                    const centerLetter = responseData.center_letter;
                    const outerLetters = responseData.all_letters.filter(l => l !== centerLetter);
                    if (outerLetters.length !== 6) {
                        // Safety check in case filtering fails or data is unexpected
                        console.error("Error: Could not determine correct outer letters for animation.", responseData);
                        if(messageArea) {
                            messageArea.textContent = 'Error preparing display animation.';
                            messageArea.className = 'message-error';
                        }
                    } else {
                         prepareAndRunAnimation(outerLetters, centerLetter); 
                    }
                    // --- ----------------------------- ---

                } else {
                    // Handle backend errors or non-ok responses
                    const errorMsg = responseData.message || responseData.error || `Failed to start game (Status: ${response.status})`;
                    console.error("Error starting game:", errorMsg);
                    throw new Error(errorMsg); // Throw error to be caught below
                }

            } catch (error) { // Catch fetch/backend errors/thrown errors
                console.error("Error in start game process:", error);
                if(dictErrorDiv) {
                    dictErrorDiv.textContent = `Error: ${error.message}`;
                    dictErrorDiv.style.display = 'block';
                }
                 // Also update message area maybe?
                 // if(messageArea) {
                 //    messageArea.textContent = `Error starting game: ${error.message}`;
                 //    messageArea.className = 'message-error';
                 // }
            } finally {
                 // Always re-enable button and reset text
                 dictionaryConfirmBtn.disabled = false;
                 dictionaryConfirmBtn.textContent = 'Start New Game';
            }
        });
    }

    // --- Helper Functions (New Ranks Modal) ---
    function populateAndOpenRanksModal() {
        if (!ranksList || !ranksModal) return;

        // --- UPDATE DESCRIPTION TEXT --- 
        const descriptionElement = ranksModal.querySelector('#ranks-list-container p');
        if (descriptionElement) {
            descriptionElement.textContent = 'Points needed for each rank:';
        }
        // --- ------------------------ ---

        // Clear previous list items
        ranksList.innerHTML = '';
        
        // Check if total score is valid
        if (currentGameTotalScore <= 0) {
             ranksList.innerHTML = '<li>Total score not available or invalid. Cannot calculate rank points.</li>';
             ranksModal.classList.add('modal-open');
             return;
        }

        // Populate list
        SORTED_KIWI_THRESHOLDS_JS.forEach(threshold => {
            const rankName = KIWI_RANKS_JS[threshold];
            // --- CALCULATE REQUIRED POINTS --- 
            const requiredPoints = Math.ceil(threshold * currentGameTotalScore);
            // --- -------------------------- ---

            const listItem = document.createElement('li');
            
            // --- DISPLAY POINTS --- 
            const pointsSpan = document.createElement('span');
            pointsSpan.classList.add('rank-points'); // Use a new class for points
            pointsSpan.textContent = `${requiredPoints} points`;
            // --- ----------------- ---
            
            const nameSpan = document.createElement('span');
            nameSpan.classList.add('rank-name');
            nameSpan.textContent = rankName;

            listItem.appendChild(pointsSpan); // Add points first
            listItem.appendChild(nameSpan);
            ranksList.appendChild(listItem);
        });

        // Show modal
        ranksModal.classList.add('modal-open');
    }

    function closeRanksModal() {
        if (ranksModal) ranksModal.classList.remove('modal-open');
    }

    // Ranks Modal Listeners (New)
    if (rankClickableArea) {
        rankClickableArea.addEventListener('click', populateAndOpenRanksModal);
    }
    if (ranksModalCloseBtn) {
        ranksModalCloseBtn.addEventListener('click', closeRanksModal);
    }
    if (ranksModal) {
        ranksModal.addEventListener('click', (event) => {
            // Close if clicked outside the modal content
            if (event.target === ranksModal) {
                closeRanksModal();
            }
        });
    }

    // --- Initial UI Setup ---
    if(currentGuessDisplay) currentGuessDisplay.focus(); // Focus guess display on load
    updateGuessDisplay(); // Ensure guess display is correct on load

    // Attach listeners to initially loaded found words
    if (modalFoundWordsList) {
        modalFoundWordsList.querySelectorAll('li[data-word]').forEach(li => {
            li.addEventListener('click', handleFoundWordClickForDefinition);
        });
        console.log(`Attached definition listeners to ${modalFoundWordsList.querySelectorAll('li[data-word]').length} initial words.`);
    }

    console.log("Spelling Bee script initialized.");

    // --- Move Helper Function Definitions Inside DOMContentLoaded Scope ---

    function updateFoundWordsButtonCount() {
        // Find all found count elements in the per-dictionary stats
        const foundCountElements = document.querySelectorAll('.dict-found-count');
        let totalFound = 0;
        foundCountElements.forEach(el => {
            totalFound += parseInt(el.textContent || '0', 10);
        });

        // Update the button text
        const foundWordsCountSpan = document.getElementById('found-words-count');
        if (foundWordsCountSpan) {
            foundWordsCountSpan.textContent = totalFound;
        }
        // Also update the modal header count if the modal is open/exists
        const modalCountSpan = document.getElementById('modal-found-words-count');
        if (modalCountSpan) {
            modalCountSpan.textContent = totalFound;
        }
    }

    function addWordToTicker(word, isPangram) {
        // Implementation of addWordToTicker function
        // (Assuming recentWordsTicker and MAX_TICKER_WORDS are accessible here)
        if (recentWordsTicker && word) { 
            const placeholder = recentWordsTicker.querySelector('.ticker-placeholder');
            if (placeholder) placeholder.remove();

            const wordSpan = document.createElement('span');
            wordSpan.textContent = word.toUpperCase(); 
            if (isPangram) {
                wordSpan.style.fontWeight = 'bold'; // Example: highlight pangrams
            }
            recentWordsTicker.prepend(wordSpan);

            // Limit the number of words shown
            while (recentWordsTicker.children.length > MAX_TICKER_WORDS) {
                recentWordsTicker.removeChild(recentWordsTicker.lastChild);
            }
        }    
    }

    function clearGuessDisplay() {
        // Implementation of clearGuessDisplay function
        const guessDisplay = document.getElementById('current-guess-display');
        if (guessDisplay) {
            guessDisplay.innerHTML = '<span>&nbsp;</span>'; // Reset to placeholder
        }
        // Also reset the internal state variable (now accessible)
        currentGuess = ''; 
    }

    // Function to update the UI after a successful game start (Method A)
    function updateUIForNewGame(data) {
        console.log("Updating UI for new game with data:", data);

        // --- Target Elements ---
        const scoreEl = document.getElementById('score'); // Use the ID from index.html
        const rankEl = document.getElementById('rank');   // Use the ID from index.html
        const foundWordsBtnCountEl = document.getElementById('found-words-count');
        const modalFoundWordsCountEl = document.getElementById('modal-found-words-count');
        const modalFoundWordsListEl = document.getElementById('modal-found-words-list');
        const dictStatsListContainer = document.querySelector('.dict-stats-list'); // Container from index.html
        const recentWordsTickerEl = document.getElementById('recent-words-ticker');

        // --- Update Score and Rank ---
        if (scoreEl) scoreEl.textContent = data.current_score;
        if (rankEl) rankEl.textContent = data.rank;

        // --- Reset Found Words Counts & Lists ---
        if (foundWordsBtnCountEl) foundWordsBtnCountEl.textContent = '0';
        if (modalFoundWordsCountEl) modalFoundWordsCountEl.textContent = '0';
        if (modalFoundWordsListEl) modalFoundWordsListEl.innerHTML = ''; // Clear the list

        // --- Rebuild Dictionary Stats Section ---
        if (dictStatsListContainer && data.word_counts_by_type && data.active_dict_metadata) {
            dictStatsListContainer.innerHTML = ''; // Clear existing stats
            GLOBAL_DICT_METADATA = data.active_dict_metadata; // Store metadata globally

            // Sort keys based on metadata order (optional, but good for consistency)
            // Assuming metadata keys are in desired order or sort them if needed.
            const sortedKeys = Object.keys(data.word_counts_by_type);
            // If you want a specific order based on AVAILABLE_DICTIONARIES_METADATA, you could sort here.

            sortedKeys.forEach(listKey => {
                const counts = data.word_counts_by_type[listKey];
                const metadata = data.active_dict_metadata[listKey];

                if (!counts || !metadata) {
                    console.warn(`Missing counts or metadata for listKey: ${listKey}`);
                    return; // Skip if data is incomplete for this key
                }

                // Create the main item container
                const dictItemDiv = document.createElement('div');
                dictItemDiv.className = 'dict-stat-item';
                dictItemDiv.setAttribute('data-list-key', listKey);

                // Create and add icon area
                const iconAreaSpan = document.createElement('span');
                iconAreaSpan.className = 'dict-icon-area';
                if (metadata.icon_type === 'emoji') {
                    const emojiSpan = document.createElement('span');
                    emojiSpan.className = 'dict-icon-emoji';
                    emojiSpan.textContent = metadata.icon_value;
                    iconAreaSpan.appendChild(emojiSpan);
                } else if (metadata.icon_type === 'image' && metadata.icon_value) {
                    const img = document.createElement('img');
                    img.src = metadata.icon_value;
                    img.alt = `${metadata.label} icon`;
                    img.className = 'dict-icon-img';
                    iconAreaSpan.appendChild(img);
                }
                dictItemDiv.appendChild(iconAreaSpan);

                // Create and add label
                const labelSpan = document.createElement('span');
                labelSpan.className = 'dict-label';
                labelSpan.textContent = `${metadata.label}:`;
                dictItemDiv.appendChild(labelSpan);

                // Create and add counts
                const countsSpan = document.createElement('span');
                countsSpan.className = 'dict-counts';
                countsSpan.innerHTML = `
                    <span class="dict-found-count" id="found-count-${listKey}">${counts.found}</span> / <span class="dict-total-count">${counts.total}</span> found
                `;
                dictItemDiv.appendChild(countsSpan);

                // Append the fully constructed item to the container
                dictStatsListContainer.appendChild(dictItemDiv);
            });
            
             // Make the container visible if it was hidden (check your CSS/template logic)
            const possibleRemainingPanel = dictStatsListContainer.closest('.possible-remaining-panel');
             if (possibleRemainingPanel) {
                 possibleRemainingPanel.style.display = ''; // Ensure it's visible
             }

        } else {
             console.warn("Could not update dictionary stats: Missing container, counts, or metadata.");
             // Optionally hide the container if data is missing
             const possibleRemainingPanel = document.querySelector('.possible-remaining-panel');
             if (possibleRemainingPanel) {
                 possibleRemainingPanel.style.display = 'none'; 
             }
        }
        
        // --- Reset Ticker ---
        if (recentWordsTickerEl) {
            recentWordsTickerEl.innerHTML = '<span class="ticker-placeholder">&nbsp;</span>'; // Reset to placeholder
        }

        // --- Clear Guess Display ---
        clearGuessDisplay(); // Use existing function
        
        // --- Message Area --- 
        // Optionally clear the message area or display the success message from backend
        if (messageArea && data.message) {
             messageArea.textContent = data.message;
             messageArea.className = 'message-valid'; // Assuming success
        } else if (messageArea) {
            messageArea.textContent = ''; // Clear it
            messageArea.className = '';
        }
    }

}); // End DOMContentLoaded