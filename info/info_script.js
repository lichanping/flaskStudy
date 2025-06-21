document.addEventListener('DOMContentLoaded', function () {
    // DOM元素
    const questionTitle = document.getElementById('question-title');
    const optionsContainer = document.getElementById('options-container');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const currentQuestionEl = document.getElementById('current-question');
    const totalQuestionsEl = document.getElementById('total-questions');
    const errorCountEl = document.getElementById('error-count');
    const feedbackContainer = document.getElementById('feedback');

    // 题目数据和状态
    let questionsData = [];
    let currentIndex = 0;
    let errorCount = 0;
    let userAnswers = {};

    // 加载JSON数据
    fetch('../data/questions.json')
        .then(response => response.json())
        .then(data => {
            questionsData = data;
            totalQuestionsEl.textContent = questionsData.length;
            renderQuestion(currentIndex);
        })
        .catch(error => {
            console.error('题目加载失败:', error);
            questionTitle.textContent = '题目加载失败，请刷新页面重试';
        });

    // 渲染题目
    function renderQuestion(index) {
        if (index < 0 || index >= questionsData.length) return;

        currentIndex = index;
        const question = questionsData[index];
        questionTitle.textContent = `${index + 1}. ${question.question}`;
        optionsContainer.innerHTML = '';

        // 重置所有选项状态
        feedbackContainer.className = 'feedback';
        feedbackContainer.innerHTML = '';

        // 生成选项
        question.options.forEach((option, optionIndex) => {
            const optionId = `option-${index}-${optionIndex}`;
            const optionElement = document.createElement('div');
            optionElement.className = 'option';
            optionElement.innerHTML = `
                <input 
                    type="radio" 
                    name="question-${question.id}" 
                    id="${optionId}"
                    value="${optionIndex}"
                >
                <label for="${optionId}">
                    ${String.fromCharCode(65 + optionIndex)}. ${option}
                </label>
            `;
            optionsContainer.appendChild(optionElement);

            // 添加事件监听
            const radioInput = optionElement.querySelector('input');
            radioInput.addEventListener('change', () => {
                handleOptionSelect(question, optionIndex);
            });

            // 如果用户之前已经选择了此选项
            if (userAnswers[question.id] === optionIndex) {
                radioInput.checked = true;
                updateOptionStatus(question, optionIndex);
            }
        });

        // 更新进度
        currentQuestionEl.textContent = index + 1;

        // 更新按钮状态
        prevBtn.disabled = index === 0;
        nextBtn.disabled = index === questionsData.length - 1;
    }

    // 处理选项选择
    function handleOptionSelect(question, selectedOptionIndex) {
        userAnswers[question.id] = selectedOptionIndex;

        const isCorrect = selectedOptionIndex === question.correctIndex;

        if (!isCorrect) {
            errorCount++;
            errorCountEl.textContent = errorCount;
        }

        // 更新所有选项状态
        updateAllOptionsStatus(question);

        // 显示反馈
        feedbackContainer.className = isCorrect ? 'feedback correct' : 'feedback incorrect';
        feedbackContainer.innerHTML = `
            <p>${isCorrect ? '✓ 回答正确！' : '✗ 回答错误！'}</p>
            <div class="explanation">${question.explanation}</div>
        `;
    }

    // 更新单个选项状态
    function updateOptionStatus(question, optionIndex) {
        const isCorrect = optionIndex === question.correctIndex;
        const isSelected = userAnswers[question.id] === optionIndex;

        const options = Array.from(optionsContainer.querySelectorAll('.option'));
        const optionElement = options[optionIndex];

        // 重置状态
        optionElement.classList.remove('correct', 'incorrect');

        if (isSelected) {
            if (isCorrect) {
                optionElement.classList.add('correct');
            } else {
                optionElement.classList.add('incorrect');
            }
        }
    }

    // 更新所有选项状态
    function updateAllOptionsStatus(question) {
        question.options.forEach((_, optionIndex) => {
            updateOptionStatus(question, optionIndex);
        });
    }

    // 上一题按钮事件
    prevBtn.addEventListener('click', function () {
        if (currentIndex > 0) {
            renderQuestion(currentIndex - 1);
        }
    });

    // 下一题按钮事件
    nextBtn.addEventListener('click', function () {
        if (currentIndex < questionsData.length - 1) {
            renderQuestion(currentIndex + 1);
        }
    });

    // 键盘导航支持
    document.addEventListener('keydown', function (event) {
        if (event.key === 'ArrowLeft') {
            prevBtn.click();
        } else if (event.key === 'ArrowRight') {
            nextBtn.click();
        }
    });
});