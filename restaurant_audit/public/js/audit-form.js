// --- GLOBAL STATE ---
let currentRestaurant = null;
let auditData = { categories: [], answers: {} };
let totalQuestions = 0;

// --- CHAT MODAL STATE & LOGIC ---
const chatModal = document.getElementById('chat-modal');
const chatMessages = document.getElementById('chat-messages');
const answerOptions = document.getElementById('answer-options');
let currentCategory = null;
let questionQueue = [];
let followUpQueue = [];
let currentQuestion = null;

document.addEventListener('DOMContentLoaded', initializeAuditForm);

async function initializeAuditForm() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const restaurantId = urlParams.get('restaurant');
        if (!restaurantId) throw new Error('No restaurant selected.');
        const storedRestaurant = sessionStorage.getItem('selectedRestaurant');
        if (storedRestaurant) {
            currentRestaurant = JSON.parse(storedRestaurant);
            document.getElementById('restaurant-name').textContent = currentRestaurant.restaurant_name;
        }
        await checkUserLocation(restaurantId);
        await loadChecklistTemplate(restaurantId);
    } catch (error) {
        showError(error.message);
    }
}

async function loadChecklistTemplate(restaurantId) {
    const response = await fetch('/api/method/restaurant_audit.api.audit_api.get_checklist_template', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ restaurant_id: restaurantId })
    });
    if (!response.ok) throw new Error(`Server error: ${response.status}`);
    const result = await response.json();
    if (!result.message?.success) throw new Error(result.message?.message || 'Failed to load checklist.');
    const icons = ["🧼", "🍳", "😊", "🔥", "📋", "📦"];
    auditData.categories = result.message.templates.flatMap((template, tIndex) =>
        template.categories.map((cat, cIndex) => ({
            id: cat.id, name: cat.name, icon: icons[(tIndex + cIndex) % icons.length],
            questions: cat.questions.map(q => ({
                id: q.id, text: q.text, type: q.answer_type,
                options: q.options,
                is_mandatory: q.is_mandatory,
                allow_image_upload: q.allow_image_upload,
                comment: q.comment
            })),
            completed: false
        }))
    );
    totalQuestions = auditData.categories.reduce((acc, cat) => acc + cat.questions.length, 0);
    document.getElementById('loading').style.display = 'none';
    document.getElementById('audit-interface').style.display = 'block';
    renderCategoryGrid();
    updateDashboard();
}

function renderCategoryGrid() {
    const grid = document.getElementById('category-grid');
    grid.innerHTML = '';
    auditData.categories.forEach(cat => {
        const tag = document.createElement('div');
        tag.className = `category-tag ${cat.completed ? 'completed' : ''}`;
        tag.dataset.categoryId = cat.id;
        tag.innerHTML = `<div class="icon">${cat.icon}</div><h4>${cat.name}</h4><div class="status">${cat.completed ? 'Complete' : 'Pending'}</div>`;
        grid.appendChild(tag);
    });
}

function updateDashboard() {
    const answeredCount = Object.keys(auditData.answers).length;
    const completion = totalQuestions > 0 ? Math.round((answeredCount / totalQuestions) * 100) : 0;
    document.getElementById('completion-text').textContent = `${completion}%`;
    document.getElementById('completion-circle').style.strokeDashoffset = 100 - completion;
    let totalScore = 0;
    let maxScore = 0;
    Object.values(auditData.answers).forEach(ans => {
        maxScore += 5;
        totalScore += ans.score;
    });
    const scorePercentage = maxScore > 0 ? Math.round((totalScore / maxScore) * 100) : 0;
    const scoreCircle = document.getElementById('score-circle');
    document.getElementById('score-text').textContent = scorePercentage;
    scoreCircle.style.strokeDashoffset = 100 - scorePercentage;
    scoreCircle.style.stroke = scorePercentage < 50 ? 'var(--error-color)' : scorePercentage < 80 ? 'var(--star-color)' : 'var(--success-color)';
    document.getElementById('submit-btn').disabled = completion < 100;
}

function openChat(categoryId) {
    currentCategory = auditData.categories.find(c => c.id === categoryId);
    if (!currentCategory) return;
    questionQueue = [...currentCategory.questions];
    document.getElementById('chat-title').textContent = currentCategory.name + " Audit";
    chatMessages.innerHTML = '';
    chatModal.style.display = 'flex';
    setTimeout(() => chatModal.classList.add('active'), 10);
    processNextInQueue();
}

function closeChat() {
    const isCategoryComplete = currentCategory.questions.every(q => auditData.answers[q.id]);
    if (isCategoryComplete) currentCategory.completed = true;
    chatModal.classList.remove('active');
    setTimeout(() => chatModal.style.display = 'none', 300);
    updateDashboard();
    renderCategoryGrid();
}

function processNextInQueue() {
    if (followUpQueue.length > 0) {
        const followUp = followUpQueue.shift();
        askFollowUpQuestion(followUp);
    } else if (questionQueue.length > 0) {
        const question = questionQueue.shift();
        currentQuestion = question;
        askMainQuestion(question);
    } else {
        addMessage("Section complete! Great job.", "bot");
        setTimeout(closeChat, 1500);
    }
}

function askMainQuestion(question) {
    const indicator = showTypingIndicator();
    setTimeout(() => {
        indicator.remove();
        let questionHTML = `<div>${question.text}</div>`;
        if (question.comment) {
            questionHTML += `<br><small><i>Hint: ${question.comment}</i></small>`;
        }
        
        if (question.options?.length > 0 && question.options[0]) {
            const secondaryGroup = document.createElement('div');
            secondaryGroup.className = 'secondary-options-group';
            secondaryGroup.innerHTML = '<h4>Additional Items:</h4>';
            const optionsContainer = document.createElement('div');
            optionsContainer.className = 'options-container';
            question.options.forEach(opt => {
                const label = document.createElement('label');
                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox'; checkbox.value = opt.trim();
                const customCheckbox = document.createElement('span');
                customCheckbox.className = 'custom-checkbox';
                label.appendChild(checkbox);
                label.appendChild(customCheckbox);
                label.append(opt.trim());
                optionsContainer.appendChild(label);
            });
            secondaryGroup.appendChild(optionsContainer);
            questionHTML += secondaryGroup.outerHTML;
        }

        addMessage(questionHTML, "bot", `bot-message-${question.id}`);
        renderAnswerOptions(question);
    }, 1000);
}

function renderAnswerOptions(question) {
    answerOptions.innerHTML = '';
    const primaryGroup = document.createElement('div');
    primaryGroup.className = 'primary-answer-group';
    let primaryOptions = [];

    if (question.type === 'Rating') {
        primaryGroup.classList.add('rating-group');
        primaryOptions = [...Array(5)].map((_, i) => ({ text: '⭐'.repeat(i + 1), score: i + 1, value: i + 1 }));
    } else if (question.type === 'Yes/No') {
        primaryOptions = [{ text: 'Yes', score: 5, value: 'Yes' }, { text: 'No', score: 1, value: 'No' }];
    }
    
    primaryOptions.forEach(opt => {
        const btn = document.createElement('button');
        btn.className = 'answer-btn star-btn';
        btn.innerHTML = opt.text;
        btn.onclick = () => {
             handleAnswer(question, opt);
        };
        primaryGroup.appendChild(btn);
    });
    
    answerOptions.appendChild(primaryGroup);
}

function handleAnswer(question, answer) {
    auditData.answers[question.id] = { 
        score: answer.score, 
        value: answer.value,
        text: answer.text,
        comment: "", 
        image_data: "", 
        selected_options: [] 
    };
    addMessage(answer.text, 'user');
    const botMessageWithCheckboxes = document.querySelector(`.bot-message-${question.id}`);
    if (botMessageWithCheckboxes) {
        const selectedOptions = Array.from(botMessageWithCheckboxes.querySelectorAll('.options-container input:checked')).map(cb => cb.value);
        if (selectedOptions.length > 0) {
            auditData.answers[question.id].selected_options = selectedOptions;
            addMessage(`Selected: ${selectedOptions.join(', ')}`, 'user');
        }
    }
    if (question.allow_image_upload) followUpQueue.push({ type: 'image', forQuestionId: question.id });
    followUpQueue.push({ type: 'comment', forQuestionId: question.id });
    answerOptions.innerHTML = '';
    processNextInQueue();
}

function askFollowUpQuestion(followUp) {
    let questionText = followUp.type === 'image' ? "Would you like to add a photo?" : "Any comments for this question?";
    addMessage(questionText, "bot");
    answerOptions.innerHTML = '';
    const container = document.createElement('div');
    container.className = 'follow-up-container';
    if (followUp.type === 'image') {
        const fileInput = document.createElement('input');
        fileInput.type = 'file'; fileInput.accept = 'image/*'; fileInput.className = 'chat-file-input';
        fileInput.onchange = e => handleImageFollowUp(followUp, e.target.files[0]);
        container.appendChild(fileInput);
    } else {
        const textInput = document.createElement('textarea');
        textInput.placeholder = "Type a comment...";
        textInput.className = "chat-textarea";
        container.appendChild(textInput);
        const enterBtn = document.createElement('button');
        enterBtn.className = 'answer-btn';
        enterBtn.textContent = "Enter";
        enterBtn.onclick = () => handleCommentFollowUp(followUp, textInput.value);
        container.appendChild(enterBtn);
    }
    const skipBtn = document.createElement('button');
    skipBtn.className = 'answer-btn skip-btn';
    skipBtn.textContent = "Skip";
    skipBtn.onclick = () => { answerOptions.innerHTML = ''; processNextInQueue(); };
    container.appendChild(skipBtn);
    answerOptions.appendChild(container);
}

async function handleImageFollowUp(followUp, file) { if (!file) { processNextInQueue(); return; } addMessage("Image attached.", 'user'); auditData.answers[followUp.forQuestionId].image_data = await toBase64(file); answerOptions.innerHTML = ''; processNextInQueue(); }
function handleCommentFollowUp(followUp, comment) { if (!comment) { processNextInQueue(); return; } addMessage(comment, 'user'); auditData.answers[followUp.forQuestionId].comment = comment; answerOptions.innerHTML = ''; processNextInQueue(); }
async function submitAudit() { const submitBtn = document.getElementById('submit-btn'); submitBtn.textContent = 'Submitting...'; submitBtn.disabled = true; try { const formattedAnswers = Object.entries(auditData.answers).map(([qid, ans]) => ({ question_id: qid, answer_value: ans.value, answer_comment: ans.comment, image_data: ans.image_data, selected_options: ans.selected_options, category: auditData.categories.find(cat => cat.questions.some(q => q.id === qid))?.id })); const response = await fetch('/api/method/restaurant_audit.api.audit_api.submit_audit', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ restaurant_id: currentRestaurant.name, answers: JSON.stringify(formattedAnswers), overall_comment: document.getElementById('overall-comment').value }) }); if (!response.ok) throw new Error(`Submit failed with status: ${response.status}`); const result = await response.json(); if (!result.message?.success) throw new Error(result.message?.message || 'Failed to submit audit.'); alert('Audit submitted successfully!'); window.location.href = '/audit-restaurants'; } catch (error) { alert(`Error: ${error.message}`); submitBtn.textContent = 'Submit Audit'; submitBtn.disabled = false; } }
function goBack() { window.location.href = '/audit-restaurants'; }
function showError(message) { document.getElementById('loading').style.display = 'none'; const errorDiv = document.getElementById('error'); errorDiv.textContent = message; errorDiv.style.display = 'block'; }
async function checkUserLocation(restaurantId) { const locationIcon = document.getElementById('location-icon'); const locationText = document.getElementById('location-text'); try { const position = await getCurrentPosition(); const { latitude, longitude } = position.coords; locationIcon.textContent = '📍'; locationText.textContent = 'Validating location...'; const response = await fetch('/api/method/restaurant_audit.api.audit_api.validate_location', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ restaurant_id: restaurantId, user_latitude: latitude, user_longitude: longitude }) }); if (!response.ok) throw new Error(`Server error: ${response.status}`); const result = await response.json(); if (result?.message?.success) { const validation = result.message; if (validation.is_within_range) { locationIcon.className = 'status-icon success'; locationIcon.textContent = '✓'; locationText.textContent = 'Location Verified'; } else { throw new Error(validation.message || 'You are not at the restaurant location.'); } } else { throw new Error(result?.message?.message || 'Location validation failed.'); } } catch (error) { console.error("Location check failed:", error); locationIcon.className = 'status-icon error'; locationIcon.textContent = '✗'; locationText.textContent = 'Location Check Failed'; } }
function getCurrentPosition() { return new Promise((resolve, reject) => { if (!navigator.geolocation) return reject(new Error('Geolocation is not supported.')); navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }); }); }
function toBase64(file) { return new Promise((resolve, reject) => { const reader = new FileReader(); reader.readAsDataURL(file); reader.onload = () => resolve(reader.result); reader.onerror = error => reject(error); }); }
function addMessage(text, sender, id = null) { const messageDiv = document.createElement('div'); if (id) messageDiv.classList.add(id); messageDiv.className += ` message ${sender}-message`; messageDiv.innerHTML = text; chatMessages.appendChild(messageDiv); chatMessages.scrollTop = chatMessages.scrollHeight; }
function showTypingIndicator() { const indicator = document.createElement('div'); indicator.className = 'typing-indicator'; indicator.innerHTML = '<span></span><span></span><span></span>'; chatMessages.appendChild(indicator); chatMessages.scrollTop = chatMessages.scrollHeight; return indicator; }
document.addEventListener('DOMContentLoaded', () => {
    initializeAuditForm();
    document.getElementById('category-grid').addEventListener('click', e => {
        const tag = e.target.closest('.category-tag');
        if (tag) openChat(tag.dataset.categoryId);
    });
    document.getElementById('close-chat').addEventListener('click', closeChat);
});