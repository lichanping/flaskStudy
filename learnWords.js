class LearnWords {
    static async readText(fileName) {
        const filePath = `data/review/${fileName}`;
        const cachedData = localStorage.getItem(filePath);

        if (cachedData) {
            console.log("If cached data exists, parse and return it, good optimization!");
            // If cached data exists, parse and return it
            return JSON.parse(cachedData);
        } else {
            const response = await fetch(filePath);
            const text = await response.text();
            const data = [];
            const pattern = /^([a-zA-Z'’\s-\/.]+)\s*(.*)$/;
            const encounteredWords = new Set();
            text.split('\n').forEach(line => {
                const match = line.trim().match(pattern);
                if (match) {
                    const [_, englishWord, translation] = match;
                    if (englishWord && translation) {
                        if (encounteredWords.has(englishWord)) {
                            console.error("Duplicate: ", englishWord);
                        } else {
                            encounteredWords.add(englishWord);
                            data.push({"单词": englishWord, "释意": translation});
                        }
                    } else {
                        console.error("Translation missing or empty for English word:", englishWord);
                    }
                }
            });

            // Cache the fetched data
            localStorage.setItem(filePath, JSON.stringify(data));
            console.log(JSON.stringify(data));
            return data;
        }
    }

    static shuffleArray(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
        return array;
    }

    static getRandomElement(array) {
        const shuffledArray = this.shuffleArray(array);
        return shuffledArray[0];
    }

    static generateOptions(globalWordsData, index = null) {
        const randomElement = index !== null ? globalWordsData[index] : this.getRandomElement(globalWordsData);
        const currentEnglishWord = randomElement["单词"].trim();
        const correctOption = randomElement["释意"];
        const otherWords = globalWordsData.filter(word => word !== randomElement);
        const wrongOptions = [];
        for (let i = 0; i < 3; i++) {
            let randomWrongWord;
            do {
                randomWrongWord = this.getRandomElement(otherWords)["释意"];
            } while (wrongOptions.includes(randomWrongWord));

            wrongOptions.push(randomWrongWord);
        }
        // 30% chance to exclude the correct option
        const noCorrectAnswer = Math.random() < 0.1;
        const options = noCorrectAnswer ? [...wrongOptions, this.getRandomElement(otherWords)["释意"]] : [correctOption, ...wrongOptions];

        // Shuffle the options
        const shuffledOptions = this.shuffleArray(options);
        // Always include "没有正确答案" as the last option
        shuffledOptions.push("没有正确答案");

        if (noCorrectAnswer) {
            const noCount = parseInt(document.getElementById('noCorrectAnswerCount').innerText);
            document.getElementById('noCorrectAnswerCount').innerText = noCount + 1;
            return {
                currentEnglishWord,
                options: shuffledOptions,
                correctIndex: shuffledOptions.indexOf("没有正确答案"),
                correctOption: correctOption
            };
        } else {
            return {
                currentEnglishWord,
                options: shuffledOptions,
                correctIndex: shuffledOptions.indexOf(correctOption),
                correctOption: ""
            };
        }
    }
}

export function play_audio() {
    const englishWordTextBox = document.getElementById('englishWordTextBox')
    const audioIcon = document.getElementById("playWord")
    englishWordTextBox.classList.add('playing-animation');
    // Remove the shake animation class after the animation ends
    setTimeout(function () {
        englishWordTextBox.classList.remove('playing-animation');
    }, 500);
    // Add playing animation class to the audio icon
    audioIcon.classList.add('playing-animation');
    // Remove playing animation class after a delay (adjust as needed)
    setTimeout(function () {
        audioIcon.classList.remove('playing-animation');
    }, 2000); // Remove the class after 2 seconds (adjust as needed)
    // Play corresponding sound if available
    const soundFileName = englishWordTextBox.value.trim().toLowerCase() + '.mp3';
    const soundFilePath = `static/sounds/${soundFileName}`;
    const audio = new Audio(soundFilePath);
    audio.onerror = () => {
        const msg = `Sound of '${englishWordTextBox.value.trim()}' failed to load!`;
        console.error(msg);
    };
    audio.play();
}

export async function renderQuestion() {
    const fileName = document.getElementById("file").value + ".txt";
    const key = fileName.replace('.txt', '');
    const optionsLine = document.getElementById("options-line");
    const renderQuestionButton = document.getElementById("renderQuestion");
    const buttonText = renderQuestionButton.innerText;
    const isPlayButton = buttonText == "播放";
    const isRandom = document.getElementById("random-toggle").checked;
    try {
        // Reset spelling input and its background color
        const spellingInput = document.getElementById('spellingInput');
        spellingInput.value = '';
        spellingInput.style.backgroundColor = '';
        const globalWordsData = await LearnWords.readText(fileName);
        // Update file count label
        const fileCountLabel = document.getElementById('fileCountLabel');
        fileCountLabel.textContent = `（${globalWordsData.length}个）`;

        let currentEnglishWord, options, correctIndex;
        let currentIndex = parseInt(sessionStorage.getItem(`${key}_currentIndex`)) || 0;
        if (isRandom) {
            const generatedOptions = LearnWords.generateOptions(globalWordsData);
            currentEnglishWord = generatedOptions.currentEnglishWord;
            options = generatedOptions.options;
            correctIndex = generatedOptions.correctIndex;
            document.getElementById("correctOptionValue").value = generatedOptions.correctOption;
        } else {
            const generatedOptions = LearnWords.generateOptions(globalWordsData, currentIndex);
            currentEnglishWord = generatedOptions.currentEnglishWord;
            options = generatedOptions.options;
            correctIndex = generatedOptions.correctIndex;
            document.getElementById("correctOptionValue").value = generatedOptions.correctOption;

            // Increment index for next question
            currentIndex = (currentIndex + 1) % globalWordsData.length;
            if (currentIndex === 0) {
                fileCountLabel.textContent = `（${globalWordsData.length}/${globalWordsData.length}个）`;
            } else {
                fileCountLabel.textContent = `（${currentIndex}/${globalWordsData.length}个）`;
            }
            sessionStorage.setItem(`${key}_currentIndex`, currentIndex);
        }

        let englishWordInput = document.getElementById("englishWordTextBox");
        englishWordInput.value = currentEnglishWord;
        if (isPlayButton) {
            englishWordInput.style.visibility = 'hidden';
        } else {
            englishWordInput.style.visibility = 'visible';
        }
        // Clear previous options
        optionsLine.innerHTML = '';

        for (let i = 0; i < options.length; i++) {
            const banner = document.createElement("button");
            banner.classList.add("banner");
            banner.id = `banner${i + 1}`;
            // Truncate the option text if it exceeds 30 characters
            // const truncatedOption = options[i].length > 30 ? options[i].substring(0, 28) + '..' : options[i];
            const truncatedOption = options[i];
            if (truncatedOption.length > 80) { // You can adjust this threshold as per your requirement
                banner.style.height = "auto";
            }
            banner.innerText = truncatedOption;
            optionsLine.appendChild(banner);
        }
        // Store correctIndex value in the hidden input
        document.getElementById("correctIndexValue").value = correctIndex;
        play_audio();
        return {currentEnglishWord, options, correctIndex};
    } catch (error) {
        console.error("Error:", error);
        return null;
    }
}

export function checkSpelling() {
    const englishWordTextBoxValue = document.getElementById('englishWordTextBox').value.trim().toLowerCase();
    const spellingInputValue = document.getElementById('spellingInput').value.trim().toLowerCase();
    const thumb = document.getElementById('thumb');
    const incorrectWordsSpan = document.getElementById('incorrectWords');
    const englishWordTextBox = document.getElementById('englishWordTextBox');
    if (spellingInputValue === '') {
        // Empty spelling input value, just show visibility
        englishWordTextBox.style.visibility = 'visible';
        return; // Exit the function
    }
    if (englishWordTextBoxValue === spellingInputValue) {
        // Correct spelling
        document.getElementById('spellingInput').style.backgroundColor = 'lightgreen';
        triggerAnimation(thumb);
    } else {
        // Incorrect spelling
        document.getElementById('spellingInput').style.backgroundColor = 'red';
        // Increment spelling errors count
        const spellingErrorsCountElement = document.getElementById('spellingErrors');
        let spellingErrorsCount = parseInt(spellingErrorsCountElement.innerText);
        spellingErrorsCountElement.innerText = spellingErrorsCount + 1;
        incorrectWordsSpan.innerText += `${document.getElementById('englishWordTextBox').value}\n`;
    }
    englishWordTextBox.style.visibility = 'visible';
}

export function compareOptionIndex(event) {
    // const passColor = "#AFEEEE";
    const passColor = "#87CEFA";

    const selectedOptionIndex = Array.from(event.target.parentNode.children).indexOf(event.target);
    const correctIndex = parseInt(document.getElementById('correctIndexValue').value);
    const correctOptionValue = document.getElementById("correctOptionValue").value;

    const englishWordTextBox = document.getElementById('englishWordTextBox');
    const english = englishWordTextBox.value;
    const scoreElement = document.getElementById('scoreNumber')
    const score = parseInt(scoreElement.innerText);
    const errorCount = parseInt(document.getElementById('errorCount').innerText);
    let correctOption = document.querySelectorAll('.banner')[correctIndex].innerText;
    if (correctOption === "没有正确答案") {
        correctOption = correctOptionValue;
    }
    document.querySelectorAll('.banner')[correctIndex].style.backgroundColor = passColor;
    const incorrectWordsSpan = document.getElementById('incorrectWords');
    const thumb = document.getElementById('thumb');
    const banners = document.querySelectorAll('.banner');
    banners.forEach(banner => {
        banner.disabled = true;
    });
    // Compare the selected option index with the correct index
    if (selectedOptionIndex === correctIndex) {
        englishWordTextBox.value = english + " " + event.target.innerText;
        englishWordTextBox.style.backgroundColor = passColor;
        if (correctOptionValue !== "") {
            displayToast(correctOptionValue);
        } else {
            displayToast(event.target.innerText);
        }
        scoreElement.innerText = score + 1;
        triggerAnimation(thumb);
    } else {
        event.target.style.backgroundColor = 'red';
        incorrectWordsSpan.innerText += `${english} ${correctOption}\n`;
        document.getElementById('errorCount').innerText = errorCount + 1;
        englishWordTextBox.style.backgroundColor = 'red';
    }

    // Automatically perform action of renderQuestion after 3 seconds
    englishWordTextBox.value = english + " " + correctOption;
    englishWordTextBox.style.visibility = 'visible';

    setTimeout(() => {
        renderQuestion();
        // Reset the background color of the English word text box after 3 seconds
        document.getElementById('englishWordTextBox').style.backgroundColor = '';
        document.querySelectorAll('.banner')[correctIndex].style.backgroundColor = '#f0f0f0';
        banners.forEach(banner => {
            banner.disabled = false;
        });
    }, 2000);
}

function triggerAnimation() {
    const thumb = document.createElement('i');
    thumb.classList.add('fas', 'fa-thumbs-up', 'thumb-up');
    document.body.appendChild(thumb);
    thumb.style.opacity = '0.2'; // Set opacity to make it visible
    thumb.style.transform = 'scale(1.2)'; // Adjust the scale for the desired effect
    setTimeout(() => {
        thumb.style.transform = 'scale(1)';
        setTimeout(() => {
            thumb.style.opacity = '0'; // Set opacity to make it invisible
            setTimeout(() => {
                thumb.remove(); // Remove the thumb-up icon after animation
            }, 300); // Adjust the timing of removal as needed (300 milliseconds in this case)
        }, 3000); // Adjust the timing of opacity change as needed (3000 milliseconds in this case)
    }, 300); // Adjust the timing of animation as needed (300 milliseconds in this case)
}


const spellingInput = document.getElementById('spellingInput');
// Add event listener for keydown event
spellingInput.addEventListener('keydown', function (event) {
    // Check if the pressed key is Enter
    if (event.key === 'Enter') {
        // Prevent the default action of the Enter key (form submission)
        event.preventDefault();
        // Perform the spelling check
        checkSpelling();
    }
});

function clearCachedData() {
    const fileName = document.getElementById("file").value + ".txt";
    const filePath = `data/review/${fileName}`; // Adjust the file name accordingly
    localStorage.removeItem(filePath); // Remove cached data
}

// Call the function to clear cached data when the page loads
window.onload = function () {
    populateList()
    clearCachedData();
    renderQuestion()
};

function populateList() {
    var today = new Date();
    var selectElement = document.getElementById("file");
    for (var i = 0; i < 10; i++) {
        var date = new Date(today);
        date.setDate(today.getDate() + i);
        var formattedDate = date.toISOString().split('T')[0];
        var option = document.createElement("option");
        option.value = formattedDate;
        option.text = formattedDate;
        selectElement.appendChild(option);
    }
}

function displayToast(message) {
    // Create a toast element
    const toast = document.createElement('div');
    toast.classList.add('toast');
    toast.textContent = message;

    // Append toast to the document body
    document.body.appendChild(toast);

    // Automatically remove toast after 3 seconds
    setTimeout(() => {
        toast.remove();
    }, 3000);
}