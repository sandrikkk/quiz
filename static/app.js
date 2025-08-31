class QuizApp {
    constructor() {
        this.questions = [];
        this.currentQuestionIndex = 0;
        this.userAnswers = {};
        this.isQuizCompleted = false;
        
        this.initEventListeners();
        this.loadQuiz();
    }
    
    initEventListeners() {
        document.getElementById('next-btn').addEventListener('click', () => this.nextQuestion());
        document.getElementById('prev-btn').addEventListener('click', () => this.prevQuestion());
        document.getElementById('finish-btn').addEventListener('click', () => this.showResults());
        document.getElementById('show-results-btn').addEventListener('click', () => this.showResults());
        document.getElementById('show-details-btn').addEventListener('click', () => this.toggleDetailedResults());
        document.getElementById('restart-btn').addEventListener('click', () => this.restartQuiz());
    }
    
    async loadQuiz() {
        try {
            const response = await fetch('/api/quiz');
            if (!response.ok) {
                throw new Error('Failed to load quiz');
            }
            
            this.questions = await response.json();
            
            // Shuffle questions randomly
            this.shuffleArray(this.questions);
            
            this.initQuiz();
        } catch (error) {
            console.error('Error loading quiz:', error);
            this.showError('ქვიზის ჩატვირთვისას მოხდა შეცდომა');
        }
    }
    
    // Fisher-Yates shuffle algorithm
    shuffleArray(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
        return array;
    }

    initQuiz() {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('quiz-interface').style.display = 'block';
        
        document.getElementById('total-questions').textContent = this.questions.length;
        this.displayQuestion();
        this.updateProgress();
    }
    
    displayQuestion() {
        const question = this.questions[this.currentQuestionIndex];
        const container = document.getElementById('question-container');
        
        const optionLabels = ['A', 'B', 'C', 'D'];
        
        // Process question text to handle tables
        const processedQuestion = this.processQuestionWithTables(question.question);
        
        container.innerHTML = `
            <div class="question-card card fade-in">
                <div class="card-body">
                    <div class="card-title mb-4">${processedQuestion}</div>
                    <div class="options">
                        ${question.options.map((option, index) => `
                            <button class="btn btn-outline-secondary option-btn w-100 ${
                                this.userAnswers[question.id] === optionLabels[index] ? 'btn-primary' : ''
                            }" 
                            onclick="app.selectAnswer(${question.id}, '${optionLabels[index]}')">
                                <span style="font-weight: 900; color: #000;">${optionLabels[index]}.</span> ${option}
                            </button>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('current-question').textContent = this.currentQuestionIndex + 1;
        this.updateNavigationButtons();
    }
    
    processQuestionWithTables(questionText) {
        // Check if question contains table data (simple detection)
        if (questionText.includes('|') || questionText.includes('A\t') || questionText.includes('A B X')) {
            // Try to convert table-like text to HTML table
            return this.convertToHtmlTable(questionText);
        }
        return questionText;
    }
    
    convertToHtmlTable(text) {
        // Handle common table patterns
        let processedText = text;
        
        // Pattern 1: Pipe-separated tables
        if (text.includes('|')) {
            const lines = text.split('\n');
            let tableLines = [];
            let nonTableLines = [];
            let inTable = false;
            
            lines.forEach(line => {
                if (line.includes('|') && line.split('|').length >= 3) {
                    tableLines.push(line);
                    inTable = true;
                } else {
                    if (inTable && tableLines.length > 0) {
                        // Convert collected table lines
                        const tableHtml = this.createTableFromPipes(tableLines);
                        nonTableLines.push(tableHtml);
                        tableLines = [];
                        inTable = false;
                    }
                    nonTableLines.push(line);
                }
            });
            
            if (tableLines.length > 0) {
                const tableHtml = this.createTableFromPipes(tableLines);
                nonTableLines.push(tableHtml);
            }
            
            return nonTableLines.join('<br>');
        }
        
        // Pattern 2: Space/tab separated with headers like "A B X"
        if (text.match(/[A-Z]\s+[A-Z]\s+[X-Z]/)) {
            return this.createTableFromSpaces(text);
        }
        
        return text;
    }
    
    createTableFromPipes(lines) {
        const rows = lines.map(line => 
            line.split('|').map(cell => cell.trim()).filter(cell => cell)
        );
        
        if (rows.length === 0) return '';
        
        let html = '<table class="logic-table">';
        
        // First row as header
        html += '<thead><tr>';
        rows[0].forEach(cell => {
            html += `<th>${cell}</th>`;
        });
        html += '</tr></thead>';
        
        // Rest as body
        html += '<tbody>';
        for (let i = 1; i < rows.length; i++) {
            html += '<tr>';
            rows[i].forEach(cell => {
                html += `<td>${cell}</td>`;
            });
            html += '</tr>';
        }
        html += '</tbody></table>';
        
        return html;
    }
    
    createTableFromSpaces(text) {
        const lines = text.split('\n');
        let tableStart = -1;
        let tableEnd = -1;
        
        // Find table boundaries
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line.match(/^[A-Z]\s+[A-Z]\s+[X-Z]/) || line.match(/^[0-1]\s+[0-1]\s+[0-1]/)) {
                if (tableStart === -1) tableStart = i;
                tableEnd = i;
            }
        }
        
        if (tableStart === -1) return text;
        
        let result = '';
        
        // Before table
        for (let i = 0; i < tableStart; i++) {
            result += lines[i] + '<br>';
        }
        
        // Create table
        result += '<table class="logic-table"><thead>';
        const headerLine = lines[tableStart].trim().split(/\s+/);
        result += '<tr>';
        headerLine.forEach(cell => {
            result += `<th>${cell}</th>`;
        });
        result += '</tr></thead><tbody>';
        
        for (let i = tableStart + 1; i <= tableEnd; i++) {
            const cells = lines[i].trim().split(/\s+/);
            if (cells.length >= headerLine.length) {
                result += '<tr>';
                cells.forEach(cell => {
                    result += `<td>${cell}</td>`;
                });
                result += '</tr>';
            }
        }
        result += '</tbody></table>';
        
        // After table
        for (let i = tableEnd + 1; i < lines.length; i++) {
            result += '<br>' + lines[i];
        }
        
        return result;
    }
    
    selectAnswer(questionId, answer) {
        this.userAnswers[questionId] = answer;
        this.submitAnswer(questionId, answer);
        this.displayQuestion(); // Refresh to show selected state
        
        // Auto-advance if not on last question
        if (this.currentQuestionIndex < this.questions.length - 1) {
            setTimeout(() => this.nextQuestion(), 500);
        }
    }
    
    async submitAnswer(questionId, answer) {
        try {
            const response = await fetch(`/api/quiz/${questionId}/answer`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ answer: answer })
            });
            
            if (!response.ok) {
                throw new Error('Failed to submit answer');
            }
        } catch (error) {
            console.error('Error submitting answer:', error);
        }
    }
    
    nextQuestion() {
        if (this.currentQuestionIndex < this.questions.length - 1) {
            this.currentQuestionIndex++;
            this.displayQuestion();
            this.updateProgress();
        }
    }
    
    prevQuestion() {
        if (this.currentQuestionIndex > 0) {
            this.currentQuestionIndex--;
            this.displayQuestion();
            this.updateProgress();
        }
    }
    
    updateNavigationButtons() {
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        
        prevBtn.disabled = this.currentQuestionIndex === 0;
        
        // Next button is always "შემდეგი" except on last question
        if (this.currentQuestionIndex === this.questions.length - 1) {
            nextBtn.style.display = 'none'; // Hide next button on last question
        } else {
            nextBtn.style.display = 'inline-block';
            nextBtn.innerHTML = 'შემდეგი <i class="fas fa-arrow-right"></i>';
        }
    }
    
    updateProgress() {
        const progress = ((this.currentQuestionIndex + 1) / this.questions.length) * 100;
        document.getElementById('progress-bar').style.width = `${progress}%`;
    }
    
    async showResults() {
        try {
            const response = await fetch('/api/results');
            if (!response.ok) {
                throw new Error('Failed to get results');
            }
            
            const results = await response.json();
            
            // Reorder results to match the shuffled question order
            const reorderedResults = this.reorderResultsToMatchQuestions(results);
            this.displayResults(reorderedResults);
        } catch (error) {
            console.error('Error getting results:', error);
            this.showError('შედეგების მიღებისას მოხდა შეცდომა');
        }
    }
    
    reorderResultsToMatchQuestions(results) {
        // Create a map of question ID to result
        const resultMap = {};
        results.detailed_results.forEach(result => {
            resultMap[result.id] = result;
        });
        
        // Reorder results according to the current shuffled question order
        const reorderedDetailedResults = this.questions.map(question => {
            return resultMap[question.id] || null;
        }).filter(result => result !== null);
        
        return {
            ...results,
            detailed_results: reorderedDetailedResults
        };
    }
    
    displayResults(results) {
        document.getElementById('quiz-interface').style.display = 'none';
        document.getElementById('results-interface').style.display = 'block';
        
        document.getElementById('result-percentage').textContent = `${results.percentage}%`;
        document.getElementById('result-text').textContent = 
            `${results.correct_answers} / ${results.total_questions} სწორი პასუხი`;
        
        this.detailedResults = results.detailed_results;
    }
    
    toggleDetailedResults() {
        const detailsDiv = document.getElementById('detailed-results');
        const btn = document.getElementById('show-details-btn');
        
        if (detailsDiv.style.display === 'none') {
            this.renderDetailedResults();
            detailsDiv.style.display = 'block';
            btn.innerHTML = '<i class="fas fa-eye-slash"></i> დამალვა';
        } else {
            detailsDiv.style.display = 'none';
            btn.innerHTML = '<i class="fas fa-list"></i> დეტალები';
        }
    }
    
    renderDetailedResults() {
        const container = document.getElementById('detailed-results');
        const optionLabels = ['A', 'B', 'C', 'D'];
        
        container.innerHTML = this.detailedResults.map((result, index) => {
            const isCorrect = result.is_correct;
            const cardClass = isCorrect ? 'correct-answer' : 'wrong-answer';
            const questionNumber = index + 1; // Sequential number based on quiz order
            
            return `
                <div class="card ${cardClass} mb-3 fade-in">
                    <div class="card-body">
                        <h6 class="card-title">
                            <i class="fas ${isCorrect ? 'fa-check-circle text-success' : 'fa-times-circle text-danger'}"></i>
                            კითხვა ${questionNumber}
                            <span class="text-muted small">(ID: ${result.id})</span>
                        </h6>
                        <p class="card-text">${result.question}</p>
                        <div class="options">
                            ${result.options.map((option, index) => {
                                const optionLabel = optionLabels[index];
                                const isUserAnswer = result.user_answer === optionLabel;
                                const isCorrectAnswer = result.correct_answer === optionLabel;
                                
                                let optionClass = '';
                                if (isCorrectAnswer) {
                                    optionClass = 'text-success fw-bold';
                                } else if (isUserAnswer && !isCorrectAnswer) {
                                    optionClass = 'text-danger fw-bold';
                                }
                                
                                return `
                                    <div class="${optionClass}">
                                        <strong>${optionLabel}.</strong> ${option}
                                        ${isCorrectAnswer ? ' <i class="fas fa-check text-success"></i>' : ''}
                                        ${isUserAnswer && !isCorrectAnswer ? ' <i class="fas fa-times text-danger"></i>' : ''}
                                    </div>
                                `;
                            }).join('')}
                        </div>
                        <div class="mt-2">
                            <small class="text-muted">
                                თქვენი პასუხი: <strong>${result.user_answer || 'პასუხი არ არის მონიშნული (0 ქულა)'}</strong> | 
                                სწორი პასუხი: <strong>${result.correct_answer}</strong>
                            </small>
                        </div>
                        ${result.ai_explanation && !result.is_correct && result.user_answer ? `
                            <div class="mt-3 p-3 bg-light border-left border-info rounded">
                                <h6 class="text-info">
                                    <i class="fas fa-robot"></i> AI ახსნა:
                                </h6>
                                <div class="ai-explanation">
                                    ${this.renderMarkdown(result.ai_explanation)}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }
    
    async restartQuiz() {
        try {
            // Reset quiz data on server
            const response = await fetch('/api/reset', {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error('Failed to reset quiz');
            }
            
            // Reset local state
            this.currentQuestionIndex = 0;
            this.userAnswers = {};
            this.isQuizCompleted = false;
            
            // Shuffle questions again for new order
            this.shuffleArray(this.questions);
            
            // Reset UI
            document.getElementById('results-interface').style.display = 'none';
            document.getElementById('quiz-interface').style.display = 'block';
            document.getElementById('show-results-btn').style.display = 'none';
            document.getElementById('detailed-results').style.display = 'none';
            document.getElementById('show-details-btn').innerHTML = '<i class="fas fa-list"></i> დეტალები';
            
            this.displayQuestion();
            this.updateProgress();
            
        } catch (error) {
            console.error('Error restarting quiz:', error);
            this.showError('ქვიზის თავიდან დაწყებისას მოხდა შეცდომა');
        }
    }
    
    renderMarkdown(text) {
        if (!text) return '';
        
        return text
            // Headers
            .replace(/^### (.*$)/gm, '<h6 class="text-primary mb-2">$1</h6>')
            .replace(/^## (.*$)/gm, '<h5 class="text-primary mb-2">$1</h5>')
            .replace(/^# (.*$)/gm, '<h4 class="text-primary mb-2">$1</h4>')
            
            // Bold text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            
            // Code blocks (simple)
            .replace(/```([\s\S]*?)```/g, '<pre class="bg-light p-2 rounded"><code>$1</code></pre>')
            
            // Inline code
            .replace(/`([^`]+)`/g, '<code class="bg-light px-1 rounded">$1</code>')
            
            // Line breaks
            .replace(/\n/g, '<br>')
            
            // Horizontal rules
            .replace(/^---$/gm, '<hr class="my-2">')
            
            // Emojis and special characters
            .replace(/❌/g, '<span class="text-danger">❌</span>')
            .replace(/✅/g, '<span class="text-success">✅</span>')
            .replace(/💡/g, '<span class="text-warning">💡</span>');
    }

    showError(message) {
        const container = document.getElementById('question-container') || document.body;
        container.innerHTML = `
            <div class="alert alert-danger fade-in" role="alert">
                <i class="fas fa-exclamation-triangle"></i> ${message}
            </div>
        `;
    }
}

// Initialize the app when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.app = new QuizApp();
});

// Add keyboard navigation
document.addEventListener('keydown', (e) => {
    if (!window.app) return;
    
    switch(e.key) {
        case 'ArrowLeft':
            e.preventDefault();
            if (!document.getElementById('prev-btn').disabled) {
                window.app.prevQuestion();
            }
            break;
        case 'ArrowRight':
            e.preventDefault();
            window.app.nextQuestion();
            break;
        case '1':
        case '2':
        case '3':
        case '4':
            e.preventDefault();
            const optionIndex = parseInt(e.key) - 1;
            const optionLabel = ['A', 'B', 'C', 'D'][optionIndex];
            const currentQuestion = window.app.questions[window.app.currentQuestionIndex];
            if (currentQuestion && optionIndex < currentQuestion.options.length) {
                window.app.selectAnswer(currentQuestion.id, optionLabel);
            }
            break;
    }
}); 