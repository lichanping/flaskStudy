class LearnWords {
    static async readText(fileName) {
        // 从 sessionStorage 中获取 studentName
        let studentName = sessionStorage.getItem('studentName');
        // 判断 studentName 是否为 null 或空值
        const directoryName = studentName && studentName.trim() !== '' ? studentName : '英语';
        const filePath = `data/review/${directoryName}/${fileName}`;
        const cachedData = localStorage.getItem(filePath);

        if (cachedData) {
            console.log("If cached data exists, parse and return it, good optimization!");
            // If cached data exists, parse and return it
            return JSON.parse(cachedData);
        } else {
            const response = await fetch(filePath);
            const text = await response.text();
            const data = [];
            const pattern = /^([a-zA-Zéèêëîïùûüàâäôöçœ'’\s-\/\.\?\？]+)\s*(.*)$/;
            const encounteredWords = new Set();
            text.split('\n').forEach(line => {
                const match = line.trim().match(pattern);
                if (match) {
                    let [_, englishWord, translation] = match;
                    englishWord = englishWord.trim(); // Trim any whitespace or tabs
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
        const wrongOptionsSet = new Set();
        const otherWords = globalWordsData.filter(word => word["释意"] !== correctOption);
        while (wrongOptionsSet.size < 3) {
            const randomWrongWord = this.getRandomElement(otherWords)["释意"];
            wrongOptionsSet.add(randomWrongWord);
        }
        const wrongOptions = Array.from(wrongOptionsSet);
        // 10% chance to exclude the correct option
        const noCorrectAnswer = Math.random() < 0.1;
        // Add correct option or additional wrong option, ensuring no duplicates
        const finalOptionsSet = new Set(noCorrectAnswer
            ? [...wrongOptions, this.getRandomElement(otherWords)["释意"]]
            : [correctOption, ...wrongOptions]
        );
        // Convert finalOptionsSet to array and shuffle
        const shuffledOptions = this.shuffleArray(Array.from(finalOptionsSet));
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
                correctOption: currentEnglishWord
            };
        }
    }

    static generateWords(globalWordsData, index = null) {
        const randomElement = index !== null ? globalWordsData[index] : this.getRandomElement(globalWordsData);
        const currentEnglishWord = randomElement["释意"].trim();
        const correctOption = randomElement["单词"];
        document.getElementById("englishMeaningField").value = correctOption;
        // Create a Set to ensure unique wrong options
        const wrongOptionsSet = new Set();
        const otherWords = globalWordsData.filter(word => word["单词"] !== correctOption);
        while (wrongOptionsSet.size < 3) {
            const randomWrongWord = this.getRandomElement(otherWords)["单词"];
            wrongOptionsSet.add(randomWrongWord);
        }
        const wrongOptions = Array.from(wrongOptionsSet);
        // 10% chance to exclude the correct option
        const noCorrectAnswer = Math.random() < 0.1;
        // Add correct option or additional wrong option, ensuring no duplicates
        const finalOptionsSet = new Set(noCorrectAnswer
            ? [...wrongOptions, this.getRandomElement(otherWords)["单词"]]
            : [correctOption, ...wrongOptions]
        );
        // Convert finalOptionsSet to array and shuffle
        const shuffledOptions = this.shuffleArray(Array.from(finalOptionsSet));
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
                correctOption: correctOption
            };
        }
    }
}

// Array of student names with associated subjects
const students = [
    {name: '英语', password: '0402'},
    {name: '法语', password: '0402'},
    {name: '妈妈', password: '0601'},
];

// Function to handle button click and prompt interaction
export function handleSwitchStudentClick() {
    // Get the current value from sessionStorage
    const storedName = sessionStorage.getItem('studentName') || '';

    // Prompt the user to enter a student name and password
    var input = prompt('请输入学生姓名和密码以继续 (例如 英语xx):', storedName);

    // Check if the user entered input
    if (input !== null && input.trim() !== '') {
        // Use regex to capture the name and password (assuming name is all Chinese characters and password is numeric)
        const regex = /^([\u4e00-\u9fa5]+)(\d+)$/;
        const match = input.trim().match(regex);

        if (match) {
            const inputName = match[1];
            const inputPassword = match[2];

            // Find if the entered value matches any student in the list
            const student = students.find(student => student.name === inputName && student.password === inputPassword);
            // // Find if the entered value matches any student in the list
            // const student = students.find(student => `${student.name}-${student.password}` === input.trim());
            if (student) {
                // Check if the current stored value is different from the new student's name
                const isDifferent = storedName !== student.name;
                if (isDifferent) {
                    // Record the boolean value (for demonstration purposes, we use console.log)
                    console.log('Entered student name is different:', isDifferent);
                    // Update sessionStorage with the new student's name
                    sessionStorage.setItem('studentName', student.name);
                    renderQuestion()
                } else {
                    console.log('Values are the same:', !isDifferent);
                }
                // Notify the user with the matching student's details
                alert(`您输入的学生姓名是: ${student.name}`);
            } else {
                // Handle the case where no matching student was found
                alert('未找到匹配的学生姓名。请确保姓名正确并用“-”分隔不同的名字。');
            }
        } else {
            // Handle the case where no input was entered
            alert('您没有输入学生姓名和密码，以-分割。');
        }
    }
}


export function play_audio() {
    const englishWordTextBox = document.getElementById('englishWordTextBox')
    const audioIcon = document.getElementById("playWord")
    // Add playing animation class to the audio icon
    audioIcon.classList.add('playing-animation');
    // Remove playing animation class after a delay (adjust as needed)
    setTimeout(function () {
        audioIcon.classList.remove('playing-animation');
    }, 2000); // Remove the class after 2 seconds (adjust as needed)
    // Play corresponding sound if available
    const isRandom = document.getElementById("random-toggle").checked;
    let word;
    if (isRandom) {
        word = document.getElementById("englishMeaningField");
    } else {
        word = englishWordTextBox;
    }
    // word = word.value.trim().toLowerCase()
    word = word.value.trim()
    const soundFileName = encodeURIComponent(word) + '.mp3';
    const soundFilePath = `static/sounds/${soundFileName}`;
    console.log(`Attempting to play sound from path: ${soundFilePath}`);

    const audio = new Audio(soundFilePath);
    audio.onerror = () => {
        const msg = `Sound of '${englishWordTextBox.value.trim()}' failed to load! Path: ${soundFilePath}`;
        console.error(msg);
    };
    audio.play();
}

export async function clearCurrentIndex() {
    const fileName = document.getElementById("file").value + ".txt";
    const key = fileName.replace('.txt', '');
    sessionStorage.removeItem(`${key}_currentIndex`);
    renderQuestion();
    document.getElementById('englishWordTextBox').style.backgroundColor = '';
    document.getElementById('incorrectWords').innerHTML = '';
    document.getElementById("scoreNumber").textContent = "0";
    document.getElementById("errorCount").textContent = "0";
    document.getElementById("spellingErrors").textContent = "0";
    document.getElementById("noCorrectAnswerCount").textContent = "0";
}

export async function goToPreviousQuestion() {
    const fileName = document.getElementById("file").value + ".txt";
    const key = fileName.replace('.txt', '');
    let currentIndex = parseInt(sessionStorage.getItem(`${key}_currentIndex`), 10) || 0;

    // Decrement index if not at the first question
    if (currentIndex > 1) {
        currentIndex -= 2;
        sessionStorage.setItem(`${key}_currentIndex`, currentIndex);
    }

    // Render the previous question
    renderQuestion();

    // Optional: Clear or reset specific elements if needed
    document.getElementById('englishWordTextBox').style.backgroundColor = '';
//    document.getElementById('incorrectWords').innerHTML = '';
//    document.getElementById("scoreNumber").textContent = "0";
//    document.getElementById("errorCount").textContent = "0";
//    document.getElementById("spellingErrors").textContent = "0";
//    document.getElementById("noCorrectAnswerCount").textContent = "0";
}

export async function renderQuestion() {
    const fileName = document.getElementById("file").value + ".txt";
    const key = fileName.replace('.txt', '');
    const optionsLine = document.getElementById("options-line");
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
        let generatedOptions;
        if (isRandom) {
            generatedOptions = LearnWords.generateWords(globalWordsData, currentIndex);
        } else {
            generatedOptions = LearnWords.generateOptions(globalWordsData, currentIndex);

        }
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

        let englishWordInput = document.getElementById("englishWordTextBox");
        englishWordInput.value = currentEnglishWord;
        if (currentEnglishWord.length > 15) {
            displayToast(currentEnglishWord);
        }
        englishWordInput.style.visibility = 'visible';
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
        if (!isRandom) {
            play_audio();
        }
        return {currentEnglishWord, options, correctIndex};
    } catch (error) {
        console.error("Error:", error);
        return null;
    }
}

export function checkSpelling() {
    const isRandom = document.getElementById("random-toggle").checked;
    const correctOptionValue = document.getElementById("correctOptionValue").value.trim().toLowerCase();
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
    // 创建法语特殊字符到对应英语字母的映射关系
    const frenchCharMapping = {
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'î': 'i', 'ï': 'i',
        'ù': 'u', 'û': 'u', 'ü': 'u',
        'à': 'a', 'â': 'a', 'ä': 'a',
        'ô': 'o', 'ö': 'o',
        'ç': 'c',
        'œ': 'oe', '’': '\''
    };

    // 将字符串中的法语特殊字符替换为对应的英语字母
    function normalizeString(str) {
        return str.split('').map(char => frenchCharMapping[char] || char).join('');
    }

    // 获取需要比较的值
    const comparisonValue = isRandom ? correctOptionValue : englishWordTextBoxValue;
    // 将输入值和比较值标准化
    let normalizedComparisonValue = normalizeString(comparisonValue);
    let normalizedSpellingInputValue = normalizeString(spellingInputValue);
    if (normalizedComparisonValue === normalizedSpellingInputValue) {
        // Correct spelling
        document.getElementById('spellingInput').style.backgroundColor = '#20B2AA';
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
    play_audio();
}

export function compareOptionIndex(event) {
    // const passColor = "#AFEEEE";
    const passColor = "#87CEFA";
    const isRandom = document.getElementById("random-toggle").checked;
    const baseDelay = 2000; // 基础等待时间为 2 秒
    let additionalDelay = 0;
    if (isRandom) {
        play_audio();
        additionalDelay = 1000; // 额外的延迟
    }
    const totalDelay = baseDelay + additionalDelay;
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
    }, totalDelay);
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
    // 从 sessionStorage 获取学生姓名，如果为空则使用默认值
    const studentName = sessionStorage.getItem('studentName') || '英语';
    const filePath = `data/review/${studentName}/${fileName}`; // Adjust the file name accordingly
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

        // 指定年-月-日的格式
        var options = {timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit'};
        var formatter = new Intl.DateTimeFormat('en-US', options);
        var parts = formatter.formatToParts(date);
        var formattedDate = `${parts.find(part => part.type === 'year').value}-${parts.find(part => part.type === 'month').value}-${parts.find(part => part.type === 'day').value}`;

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
    }, 5000);
}