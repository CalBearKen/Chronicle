document.addEventListener('DOMContentLoaded', function() {
    const datePicker = document.getElementById('date-picker');
    const dateSlider = document.getElementById('date-slider');
    const currentDateDisplay = document.getElementById('current-date');
    const articlesList = document.getElementById('articles-list');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    const notyf = new Notyf({
        duration: 3000,
        position: { x: 'right', y: 'top' }
    });
    
    let isTransitioning = false;
    const startDate = new Date(datePicker.min);
    const endDate = new Date(datePicker.max);
    const totalDays = (endDate - startDate) / (1000 * 60 * 60 * 24);
    
    function showLoading() {
        loadingIndicator.style.display = 'flex';
        articlesList.style.opacity = '0.3';
    }
    
    function hideLoading() {
        loadingIndicator.style.display = 'none';
        articlesList.style.opacity = '1';
    }
    
    async function fetchArticles(date) {
        try {
            showLoading();
            const response = await fetch(`/api/articles/${date}`);
            const data = await response.json();
            
            // Map the response data to article objects
            return data.map(article => ({
                id: article.id,
                title: article.title,
                publication: article.publication || article.name,  // Use feed name as fallback
                published: article.published,
                summary: article.summary,
                link: article.link,
                expanded: false
            }));
            
        } catch (error) {
            notyf.error('Error fetching articles');
            console.error('Error fetching articles:', error);
            return [];
        } finally {
            hideLoading();
        }
    }
    
    function formatDate(dateString) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        return new Date(dateString).toLocaleDateString(undefined, options);
    }
    
    function updateDisplay(articles) {
        articlesList.innerHTML = '';
        
        if (!articles || articles.length === 0) {
            articlesList.innerHTML = '<p class="no-data">No articles found for this date</p>';
            return;
        }
        
        articles.forEach((article, index) => {
            const articleEl = document.createElement('div');
            articleEl.className = 'article-item';
            articleEl.innerHTML = `
                <div class="article-header">
                    <div class="header-content">
                        <h3>${article.title}</h3>
                        <div class="article-meta">
                            <span class="publication">${article.publication}</span>
                            <span class="date">${new Date(article.published).toLocaleDateString()}</span>
                        </div>
                    </div>
                    <span class="toggle-icon">▼</span>
                </div>
                <div class="article-summary">
                    <p>${article.summary || 'No summary available'}</p>
                    <a href="${article.link}" target="_blank" class="read-more">Read full article →</a>
                </div>
            `;

            // Add click handler for expansion
            const header = articleEl.querySelector('.article-header');
            const summary = articleEl.querySelector('.article-summary');
            const toggleIcon = articleEl.querySelector('.toggle-icon');
            
            header.addEventListener('click', () => {
                const isExpanded = summary.classList.toggle('expanded');
                toggleIcon.style.transform = isExpanded ? 'rotate(180deg)' : 'rotate(0deg)';
                
                // Collapse other items if needed
                // document.querySelectorAll('.article-summary').forEach(el => {
                //     if (el !== summary) el.classList.remove('expanded');
                // });
            });

            articlesList.appendChild(articleEl);
        });
    }
    
    function dateToSliderValue(date) {
        const current = new Date(date);
        const days = (current - startDate) / (1000 * 60 * 60 * 24);
        return (days / totalDays) * 100;
    }
    
    function sliderValueToDate(value) {
        const days = (value / 100) * totalDays;
        const date = new Date(startDate);
        date.setDate(date.getDate() + Math.round(days));
        return date.toISOString().split('T')[0];
    }
    
    async function handleDateChange(date) {
        if (isTransitioning) return;
        isTransitioning = true;
        
        try {
            currentDateDisplay.textContent = formatDate(date);
            const articles = await fetchArticles(date);
            updateDisplay(articles);
        } finally {
            isTransitioning = false;
        }
    }
    
    async function findNearestNewsDate(date) {
        try {
            const response = await fetch(`/api/nearest-date/${date}`);
            const data = await response.json();
            return data.nearest_date;
        } catch (error) {
            console.error('Error finding nearest date:', error);
            return null;
        }
    }
    
    // Event Listeners
    datePicker.addEventListener('change', function() {
        const date = this.value;
        dateSlider.value = dateToSliderValue(date);
        handleDateChange(date);
    });
    
    dateSlider.addEventListener('input', function() {
        const date = sliderValueToDate(this.value);
        datePicker.value = date;
        currentDateDisplay.textContent = formatDate(date);
    });
    
    dateSlider.addEventListener('change', function() {
        const date = sliderValueToDate(this.value);
        handleDateChange(date);
    });
    
    // Initialize chat after DOM is loaded
    function initChat() {
        const chatInput = document.getElementById('chat-input');
        const sendButton = document.getElementById('send-button');
        const chatMessages = document.getElementById('chat-messages');
        
        if (!chatInput || !sendButton || !chatMessages) {
            console.error('Chat elements not found');
            return;
        }
        
        function addMessage(text, isUser = false) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
            
            const messageText = document.createElement('span');
            messageText.className = 'message-text';
            messageText.textContent = text;
            
            messageDiv.appendChild(messageText);
            chatMessages.appendChild(messageDiv);
            
            // Scroll to bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function addLoadingIndicator() {
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message bot-message loading';
            loadingDiv.innerHTML = `
                <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            `;
            chatMessages.appendChild(loadingDiv);
            return loadingDiv;
        }

        async function sendMessage() {
            const query = chatInput.value.trim();
            if (!query) return;

            // Add user message
            addMessage(query, true);
            chatInput.value = '';
            
            // Add loading indicator
            const loadingIndicator = addLoadingIndicator();
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ query })
                });

                const data = await response.json();
                
                // Remove loading indicator
                loadingIndicator.remove();
                
                // Add bot response
                if (data.error) {
                    notyf.error(data.error);
                    addMessage('Sorry, I encountered an error. Please try again.');
                } else {
                    addMessage(data.response);
                }
                
            } catch (error) {
                loadingIndicator.remove();
                notyf.error('Error sending message');
                addMessage('Sorry, I encountered an error. Please try again.');
            }
        }

        sendButton.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        // Add welcome message
        addMessage('Hi! I can help you find and understand news articles. What would you like to know?');
    }

    // Initialize both date handling and chat
    handleDateChange(datePicker.value);
    initChat();
}); 