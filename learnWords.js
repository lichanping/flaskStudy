class LearnWords {
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

export function checkLoginStatus() {
    const currentDate = new Date();
    const storedLoginDate = new Date(localStorage.getItem('loginDate'));
    const loggedInWord = localStorage.getItem('loggedInWord') === 'true';

    // Calculate the difference in days
    const dayDifference = Math.floor((currentDate - storedLoginDate) / (1000 * 60 * 60 * 24));

    if (loggedInWord && dayDifference < 30) {
        // If logged in and the login date is within the last 30 days, allow the user to stay on the page
        // No action needed, user is allowed to stay on the page
    } else {
        // If not logged in or the login date is not within the last 30 days, redirect to login.html
        window.location.href = 'login.html';
    }
}

// Array of student names with associated subjects
const students = [
    {name: '英语', password: '0402'},
    {name: '法语', password: '0402'},
    {name: '妈妈', password: '0601'},
    {name: '硕硕', password: '8'},
];

export function validateLogin() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const currentDate = new Date();

    // Check if user is already logged in and if login is valid for the last 30 days
    const storedLoginDate = new Date(localStorage.getItem('loginDate'));
    const loggedInWord = localStorage.getItem('loggedInWord') === 'true';

    // Calculate the difference in days
    const dayDifference = Math.floor((currentDate - storedLoginDate) / (1000 * 60 * 60 * 24));

    // Validate credentials using the students array
    const student = students.find(student => student.name === username && student.password === password);

    if (loggedInWord && dayDifference < 30) {
        // If already logged in for the last 30 days, check if the new username is different
        const storedStudentName = sessionStorage.getItem('studentName');
        if (student && student.name !== storedStudentName) {
            // Update sessionStorage with the new student's name
            sessionStorage.setItem('studentName', student.name);
            window.location.href = 'index.html';
        } else {
            // If the same username is entered, skip login process
            window.location.href = 'index.html';
        }
        return;
    }

    if (student) {
        // Store login state, date, and student's name if credentials are correct
        localStorage.setItem('loggedInWord', 'true');
        localStorage.setItem('loginDate', currentDate.toString());
        sessionStorage.setItem('studentName', student.name);
        window.location.href = 'index.html';
    } else {
        document.getElementById('error-message').style.display = 'block';
    }
}


// Function to handle button click and prompt interaction
export function handleSwitchStudentClick() {
    // Get the current value from sessionStorage
    const storedName = sessionStorage.getItem('studentName') || '';

    // Prompt the user to enter a student name and password
    var input = prompt('请输入学生姓名和密码以继续 (例如 法语xx):', storedName);

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

            if (student) {
                // Check if the current stored value is different from the new student's name
                const isDifferent = storedName !== student.name;
                if (isDifferent) {
                    // Record the boolean value (for demonstration purposes, we use console.log)
                    console.log('Entered student name is different:', isDifferent);
                    // Update sessionStorage with the new student's name
                    sessionStorage.setItem('studentName', student.name);
                    renderQuestion();
                } else {
                    console.log('Values are the same:', !isDifferent);
                }
                // Notify the user with the matching student's details
                alert(`您输入的学生姓名是: ${student.name}`);
            } else {
                // Handle the case where no matching student was found
                alert('未找到匹配的学生姓名。请确保姓名正确并用"-"分隔不同的名字。');
            }
        } else {
            // Handle the case where no input was entered
            alert('您没有输入学生姓名和密码，以"-"分割。');
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
        const spellingInput = document.getElementById('spellingInput');
        spellingInput.value = '';
        spellingInput.style.backgroundColor = '';
        const globalWordsData = await getWordData();
        const fileCountLabel = document.getElementById('fileCountLabel');
        fileCountLabel.textContent = `（${globalWordsData.length}个）`;

        // Store the length of globalWordsData in sessionStorage
        sessionStorage.setItem(`${key}_totalWords`, globalWordsData.length.toString());

        let currentWord, options, correctIndex;
        let currentIndex = parseInt(sessionStorage.getItem(`${key}_currentIndex`)) || 0;
        let generatedOptions;

        // Check if it's time to review a word from the review list
        if (wordsSinceLastReview >= 5 && reviewList.length > 0) {
            const reviewIndex = reviewList.shift();
            if (isRandom) {
                generatedOptions = LearnWords.generateWords(globalWordsData, reviewIndex);
            } else {
                generatedOptions = LearnWords.generateOptions(globalWordsData, reviewIndex);
            }
            currentWord = generatedOptions.currentEnglishWord;
            options = generatedOptions.options;
            correctIndex = generatedOptions.correctIndex;
            document.getElementById("correctOptionValue").value = generatedOptions.correctOption;
            wordsSinceLastReview = 0;
        } else {
            if (isRandom) {
                generatedOptions = LearnWords.generateWords(globalWordsData, currentIndex);
            } else {
                generatedOptions = LearnWords.generateOptions(globalWordsData, currentIndex);
            }
            currentWord = generatedOptions.currentEnglishWord;
            options = generatedOptions.options;
            correctIndex = generatedOptions.correctIndex;
            document.getElementById("correctOptionValue").value = generatedOptions.correctOption;
            currentIndex = (currentIndex + 1) % globalWordsData.length;
            if (currentIndex === 0) {
                fileCountLabel.textContent = `（${globalWordsData.length}/${globalWordsData.length}个）`;
            } else {
                fileCountLabel.textContent = `（${currentIndex}/${globalWordsData.length}个）`;
            }
            sessionStorage.setItem(`${key}_currentIndex`, currentIndex);
            wordsSinceLastReview++;
        }

        let wordInput = document.getElementById("englishWordTextBox");
        wordInput.value = currentWord;
        if (currentWord.length > 25) {
            // Append the currentWord value to the incorrectWordsSpan for visibility
            const incorrectWordsSpan = document.getElementById('incorrectWords');
            incorrectWordsSpan.innerText += `${currentWord}\n`;
        }
        wordInput.style.visibility = 'visible';
        optionsLine.innerHTML = '';

        for (let i = 0; i < options.length; i++) {
            const banner = document.createElement("button");
            banner.classList.add("banner");
            banner.id = `banner${i + 1}`;
            const truncatedOption = options[i];
            if (truncatedOption.length > 80) {
                banner.style.height = "auto";
            }
            banner.innerText = truncatedOption;
            optionsLine.appendChild(banner);
        }
        document.getElementById("correctIndexValue").value = correctIndex;
        if (!isRandom) {
            play_audio();
        }
        return {currentWord, options, correctIndex};
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
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e', 'É': 'e',
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

let hasSelectedWrong = false;
let reviewList = [];
let wordsSinceLastReview = 0;

export function compareOptionIndex(event) {
    const passColor = "#87CEFA";
    const isRandom = document.getElementById("random-toggle").checked;
    const baseDelay = 2000;
    let additionalDelay = 0;
    if (isRandom) {
        additionalDelay = 1000;
    }
    const totalDelay = baseDelay + additionalDelay;
    const selectedOptionIndex = Array.from(event.target.parentNode.children).indexOf(event.target);
    const correctIndex = parseInt(document.getElementById('correctIndexValue').value);
    const correctOptionValue = document.getElementById("correctOptionValue").value;

    const englishWordTextBox = document.getElementById('englishWordTextBox');
    const english = englishWordTextBox.value;
    const scoreElement = document.getElementById('scoreNumber');
    const score = parseInt(scoreElement.innerText);
    const errorCount = parseInt(document.getElementById('errorCount').innerText);
    let correctOption = document.querySelectorAll('.banner')[correctIndex].innerText;
    if (correctOption === "没有正确答案") {
        correctOption = correctOptionValue;
    }
    const incorrectWordsSpan = document.getElementById('incorrectWords');
    const thumb = document.getElementById('thumb');

    if (selectedOptionIndex === correctIndex) {
        if (isRandom) {
            play_audio();
        }
        let selectedText = (correctOption === "没有正确答案" ? correctOptionValue : event.target.innerText);
        let displayText = selectedText === "没有正确答案" ? correctOptionValue : selectedText;
        englishWordTextBox.value = english + " " + displayText;

        englishWordTextBox.style.backgroundColor = passColor;
        document.querySelectorAll('.banner')[correctIndex].style.backgroundColor = passColor;
        if (correctOptionValue !== "") {
            displayToast(correctOptionValue);
        } else {
            displayToast(event.target.innerText);
        }
        if (!hasSelectedWrong) {
            scoreElement.innerText = score + 1;
        }
        triggerAnimation(thumb);
        setTimeout(() => {
            renderQuestion();
            document.getElementById('englishWordTextBox').style.backgroundColor = '';
            document.querySelectorAll('.banner')[correctIndex].style.backgroundColor = '#f0f0f0';
            hasSelectedWrong = false;
        }, totalDelay);
    } else {
        event.target.style.backgroundColor = 'red';
        incorrectWordsSpan.innerText += `${english} ${correctOption}\n`;
        document.getElementById('errorCount').innerText = errorCount + 1;
        englishWordTextBox.style.backgroundColor = 'red';
        hasSelectedWrong = true;

        // Add incorrect word to review list based on isRandom flag
        const fileName = document.getElementById("file").value + ".txt";
        const key = fileName.replace('.txt', '');
        const currentIndex = parseInt(sessionStorage.getItem(`${key}_currentIndex`)) || 0;
        const totalWords = parseInt(sessionStorage.getItem(`${key}_totalWords`));
        let reviewIndex = currentIndex - 1;
        if (reviewIndex < 0) {
            reviewIndex += totalWords;
        }
        reviewList.push(reviewIndex);
    }
    englishWordTextBox.style.visibility = 'visible';
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


// 初始化IndexedDB
const DB_NAME = 'WordCacheDB';
const STORE_NAME = 'wordData';
const DB_VERSION = 1;

async function initDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME, { keyPath: 'filePath' });
            }
        };

        request.onsuccess = (event) => resolve(event.target.result);
        request.onerror = (event) => reject(event.target.error);
    });
}

// 修改后的数据获取逻辑
async function getWordData() {
    const fileName = document.getElementById("file").value + ".txt";
    const studentName = sessionStorage.getItem('studentName') || '法语';
    const filePath = `data/review/${studentName}/${fileName}`;
    
    console.log('当前请求文件路径:', filePath); // 新增日志

    try {
        const db = await initDB();
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        
        // 打印所有存储的key
        const allKeys = await store.getAllKeys();
        console.log('IndexedDB现有缓存key列表:', allKeys); // 新增日志

        const request = store.get(filePath);
        const cachedData = await new Promise((resolve, reject) => {
            request.onsuccess = () => {
                console.log('缓存查询结果:', request.result); // 新增日志
                resolve(request.result?.data)
            };
            request.onerror = () => reject(request.error);
        });

        if (cachedData) {
            console.log(`使用缓存数据，路径: ${filePath}，数据量: ${cachedData.length}条`);
            return cachedData;
        }

        // 新增未命中缓存的日志
        console.warn(`未找到缓存，开始获取新数据: ${filePath}`);
        const response = await fetch(filePath);
        const text = await response.text();
        const data = processText(text);

        // 存储时添加日志
        const writeTx = db.transaction(STORE_NAME, 'readwrite');
        writeTx.oncomplete = () => console.log(`数据存储完成: ${filePath}`);
        const writeStore = writeTx.objectStore(STORE_NAME);
        writeStore.put({ filePath, data });
        
        return data;
    } catch (error) {
        console.error('IndexedDB操作失败:', error);
        throw error;
    }
}

// 清理缓存方法修改
async function clearCachedData() {
    const fileName = document.getElementById("file").value + ".txt";
    const studentName = sessionStorage.getItem('studentName') || '法语';
    const filePath = `data/review/${studentName}/${fileName}`;

    try {
        const db = await initDB();
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        store.delete(filePath);
    } catch (error) {
        console.error('缓存清理失败:', error);
    }
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

function processText(text) {
    const data = [];
    const pattern = /^([a-zA-ZéèêëîïùûüàâäôöçœÉÇÀ\'\s–\.\/\?\？，,0-9-]+)\s*(.*)$/;
    const encounteredWords = new Set();
    
    text.split('\n').forEach(line => {
        const match = line.trim().match(pattern);
        if (match) {
            let [_, englishWord, translation] = match;
            englishWord = englishWord.trim();
            if (englishWord && translation) {
                if (!encounteredWords.has(englishWord)) {
                    encounteredWords.add(englishWord);
                    data.push({ "单词": englishWord, "释意": translation });
                }
            }
        }
    });
    
    return data;
}

if (!('indexedDB' in window)) {
    alert("当前浏览器不支持IndexedDB，请使用Chrome 23+/Firefox 10+/Safari 8+");
}