document.addEventListener('DOMContentLoaded', () => {
    // const guessInput = document.getElementById('guess-input'); // Removed
    const submitButton = document.getElementById('submit-guess');
    const messageArea = document.getElementById('message-area');
    const scoreDisplay = document.getElementById('score');
    const rankDisplay = document.getElementById('rank');
    const foundWordsList = document.getElementById('found-words-list');
    const foundWordsCountSpan = document.getElementById('found-words-count');
    const totalWordsDisplay = document.getElementById('total-words');
    const wordsRemainingDisplay = document.getElementById('words-remaining');
    const hiveCellGroups = document.querySelectorAll('.hive-cell-group');
    const currentGuessDisplay = document.getElementById('current-guess-display');
    const deleteButton = document.getElementById('delete-char');
    const shuffleButton = document.getElementById('shuffle-letters');
    const hiveSvg = document.getElementById('hive-svg');
    const newGameButton = document.getElementById('new-game-button');
    const showFoundWordsButton = document.getElementById('show-found-words-button');
    const foundWordsModal = document.getElementById('found-words-modal');
    const modalFoundWordsList = document.getElementById('modal-found-words-list');
    const modalCloseButton = foundWordsModal.querySelector('.modal-close-button');
    const recentWordsTicker = document.getElementById('recent-words-ticker');

    // Settings Modal Elements
    const settingsButton = document.getElementById('settings-button');
    const settingsModal = document.getElementById('settings-modal');
    const settingsCloseButton = settingsModal.querySelector('.settings-close-button');

    const MAX_TICKER_WORDS = 7;

    let currentGuess = '';

    const updateGuessDisplay = () => {
        if (currentGuess) {
            currentGuessDisplay.textContent = currentGuess.toUpperCase();
        } else {
            currentGuessDisplay.innerHTML = '<span>&nbsp;</span>';
        }
        // No longer need to update a hidden input
        // guessInput.value = currentGuess;
    };

    const handleLetterClick = (event) => {
        const letter = event.currentTarget.getAttribute('data-letter');
        if (letter) {
            currentGuess += letter;
            updateGuessDisplay();
        }
    };

    const deleteLastChar = () => {
        if (currentGuess.length > 0) {
            currentGuess = currentGuess.slice(0, -1);
            updateGuessDisplay();
        }
    };

    const shuffleLetters = () => {
        // Select the text elements directly
        const outerLetters = Array.from(document.querySelectorAll('.hive-letter.outer-letter-flat'));

        // Get the current letters from the data attribute
        let letters = outerLetters.map(el => el.getAttribute('data-letter'));

        // Shuffle the letters array (Fisher-Yates)
        for (let i = letters.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [letters[i], letters[j]] = [letters[j], letters[i]];
        }

        // Update the text content and data attribute of each element
        outerLetters.forEach((element, index) => {
            const newLetter = letters[index];
            element.textContent = newLetter.toUpperCase();
            element.setAttribute('data-letter', newLetter);
        });
    };

    const openModal = () => {
        foundWordsModal.classList.add('modal-open');
    };

    const closeModal = () => {
        foundWordsModal.classList.remove('modal-open');
    };

    // Settings Modal Functions
    const openSettingsModal = () => {
        settingsModal.classList.add('modal-open');
    };

    const closeSettingsModal = () => {
        settingsModal.classList.remove('modal-open');
    };

    const submitGuess = async () => {
        const guess = currentGuess.trim().toLowerCase();
        if (!guess) return;

        try {
            const response = await fetch('/guess', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ guess: guess }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            console.log("Backend response:", result);

            messageArea.textContent = result.message;
            messageArea.className = `message-${result.status}`;

            if (result.status !== 'finished') {
                setTimeout(() => {
                    if (messageArea.textContent === result.message) {
                       messageArea.textContent = '';
                       messageArea.className = '';
                    }
                }, 3000);
            }

            scoreDisplay.textContent = result.score;
            rankDisplay.textContent = result.rank;

            const totalWords = parseInt(totalWordsDisplay.textContent, 10);
            const foundCount = result.found_words_count;
            wordsRemainingDisplay.textContent = totalWords - foundCount;

            foundWordsCountSpan.textContent = result.found_words_count;

            modalFoundWordsList.innerHTML = '';
            result.found_words.forEach(word => {
                const li = document.createElement('li');
                li.textContent = word.toUpperCase();
                li.setAttribute('data-word', word);
                // li.setAttribute('title', 'Click to load definition...'); // Title no longer primary display

                li.addEventListener('click', async (event) => {
                    const targetLi = event.currentTarget;
                    const existingDefinitionDiv = targetLi.querySelector('.definition-display');

                    // If definition is already showing, remove it (toggle off)
                    if (existingDefinitionDiv) {
                        existingDefinitionDiv.remove();
                        return; // Stop here
                    }

                    // Remove definition from any other li before showing new one
                    const allDefinitionDivs = modalFoundWordsList.querySelectorAll('.definition-display');
                    allDefinitionDivs.forEach(div => div.remove());

                    const wordToDefine = targetLi.getAttribute('data-word');

                    // Create and append the definition display div
                    const definitionDiv = document.createElement('div');
                    definitionDiv.className = 'definition-display';
                    definitionDiv.textContent = 'Loading definition...';
                    targetLi.appendChild(definitionDiv); // Append below the word

                    try {
                        const response = await fetch(`/definition/${wordToDefine}`);
                        if (!response.ok) {
                            throw new Error('Failed to fetch definition');
                        }
                        const data = await response.json();
                        // Check if the div still exists (user might have clicked elsewhere quickly)
                        const currentDefinitionDiv = targetLi.querySelector('.definition-display');
                        if (currentDefinitionDiv) {
                             currentDefinitionDiv.textContent = data.definition;
                        }
                    } catch (error) {
                        console.error("Definition fetch error:", error);
                         const currentDefinitionDiv = targetLi.querySelector('.definition-display');
                         if (currentDefinitionDiv) {
                            currentDefinitionDiv.textContent = 'Could not load definition.';
                         }
                    }
                });

                modalFoundWordsList.appendChild(li);
            });

            // --- Update Ticker --- START
            if (result.status === 'valid') {
                const placeholder = recentWordsTicker.querySelector('.ticker-placeholder');
                if (placeholder) {
                    placeholder.remove();
                }

                const wordSpan = document.createElement('span');
                wordSpan.textContent = guess.toUpperCase();
                recentWordsTicker.prepend(wordSpan);

                // Limit the number of words in the ticker
                while (recentWordsTicker.children.length > MAX_TICKER_WORDS) {
                    recentWordsTicker.removeChild(recentWordsTicker.lastChild); // Remove the oldest (right-most)
                }
            }
            // --- Update Ticker --- END

            console.log("Before clear check - currentGuess:", currentGuess);
            if (result.status === 'valid' || 
                result.status === 'finished' || 
                result.message === 'Already found!' || 
                result.message.startsWith("Missing center letter") ||
                result.status === 'invalid' ) // Also clear on other invalid states
            {
                 console.log("Clearing currentGuess...");
                 currentGuess = '';
                 updateGuessDisplay();
            }
            console.log("After clear check - currentGuess:", currentGuess);

        } catch (error) {
            console.error('Error submitting guess:', error);
            messageArea.textContent = 'Error communicating with server.';
            messageArea.className = 'message-error';
        }
    };

    document.addEventListener('keydown', (event) => {
        if (event.metaKey || event.ctrlKey || event.altKey) {
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
            currentGuess += key.toLowerCase();
            updateGuessDisplay();
        }
    });

    submitButton.addEventListener('click', submitGuess);

    // Add click listener to the center group
    if (centerGroup) {
        centerGroup.addEventListener('click', handleLetterClick);
    }

    // Add click listeners to the outer letter text elements
    outerLetterElements.forEach(letterElement => {
        letterElement.addEventListener('click', handleLetterClick);
    });

    deleteButton.addEventListener('click', deleteLastChar);
    shuffleButton.addEventListener('click', shuffleLetters);

    showFoundWordsButton.addEventListener('click', openModal);

    modalCloseButton.addEventListener('click', closeModal);

    foundWordsModal.addEventListener('click', (event) => {
        if (event.target === foundWordsModal) {
            closeModal();
        }
    });

    // Settings Modal Listeners
    if (settingsButton) {
        settingsButton.addEventListener('click', openSettingsModal);
    }
    if (settingsCloseButton) {
        settingsCloseButton.addEventListener('click', closeSettingsModal);
    }
    if (settingsModal) {
        settingsModal.addEventListener('click', (event) => {
            // Close if clicking on the overlay itself, not the content inside
            if (event.target === settingsModal) {
                closeSettingsModal();
            }
        });
    }

    newGameButton.addEventListener('click', () => {
        window.location.href = '/new_game';
    });

    currentGuessDisplay.focus();
    updateGuessDisplay();
}); 