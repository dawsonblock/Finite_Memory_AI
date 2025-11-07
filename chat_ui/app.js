// Modern Chat UI - JavaScript
class ChatApp {
    constructor() {
        this.messages = [];
        this.currentChatId = null;
        this.settings = {
            policy: 'sliding',
            maxTokens: 512,
            model: 'gpt2',
            telemetry: true,
            darkMode: false
        };
        
        this.init();
    }

    init() {
        this.loadSettings();
        this.bindEvents();
        this.updateStats();
        this.applyTheme();
    }

    bindEvents() {
        // Input events
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const charCount = document.getElementById('charCount');

        messageInput.addEventListener('input', (e) => {
            this.autoResize(e.target);
            charCount.textContent = `${e.target.value.length} characters`;
        });

        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        sendBtn.addEventListener('click', () => this.sendMessage());

        // Example prompts
        document.querySelectorAll('.example-prompt').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const prompt = e.target.dataset.prompt;
                messageInput.value = prompt;
                this.sendMessage();
            });
        });

        // Header actions
        document.getElementById('newChatBtn').addEventListener('click', () => this.newChat());
        document.getElementById('clearBtn').addEventListener('click', () => this.clearChat());
        document.getElementById('exportBtn').addEventListener('click', () => this.exportChat());

        // Settings modal
        document.getElementById('settingsBtn').addEventListener('click', () => this.openSettings());
        document.getElementById('closeSettingsBtn').addEventListener('click', () => this.closeSettings());
        document.getElementById('saveSettingsBtn').addEventListener('click', () => this.saveSettings());
        document.getElementById('resetSettingsBtn').addEventListener('click', () => this.resetSettings());

        // Settings controls
        document.getElementById('maxTokensRange').addEventListener('input', (e) => {
            document.getElementById('maxTokensValue').textContent = e.target.value;
        });

        document.getElementById('darkModeToggle').addEventListener('change', (e) => {
            this.settings.darkMode = e.target.checked;
            this.applyTheme();
        });

        // Close modal on outside click
        document.getElementById('settingsModal').addEventListener('click', (e) => {
            if (e.target.id === 'settingsModal') {
                this.closeSettings();
            }
        });
    }

    autoResize(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }

    async sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();

        if (!message) return;

        // Clear input
        input.value = '';
        input.style.height = 'auto';
        document.getElementById('charCount').textContent = '0 characters';

        // Hide welcome screen
        const welcomeScreen = document.querySelector('.welcome-screen');
        if (welcomeScreen) {
            welcomeScreen.remove();
        }

        // Add user message
        this.addMessage('user', message);

        // Show typing indicator
        this.showTypingIndicator();

        // Update status
        this.updateStatus('thinking', 'Thinking...');

        // Simulate API call (replace with actual backend call)
        try {
            const response = await this.callBackend(message);
            this.removeTypingIndicator();
            this.addMessage('assistant', response);
            this.updateStatus('ready', 'Ready');
            this.updateStats();
        } catch (error) {
            this.removeTypingIndicator();
            this.addMessage('assistant', 'Sorry, I encountered an error. Please try again.');
            this.updateStatus('error', 'Error');
            console.error('Error:', error);
        }
    }

    async callBackend(message) {
        // Call the real backend API
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.success) {
                // Update stats from backend
                if (data.stats) {
                    this.updateStatsFromBackend(data.stats);
                }
                return data.response;
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        } catch (error) {
            console.error('Backend error:', error);
            throw error;
        }
    }

    updateStatsFromBackend(stats) {
        // Update UI with real backend stats
        if (stats.tokens_retained !== undefined && stats.max_tokens) {
            document.getElementById('tokensUsed').textContent = 
                `${stats.tokens_retained}/${this.settings.maxTokens}`;
        }
        // Message count is tracked locally
        document.getElementById('messageCount').textContent = this.messages.length;
        document.getElementById('policyName').textContent = this.settings.policy;
    }

    addMessage(role, content) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? 'U' : 'AI';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble';
        bubble.textContent = content;

        const time = document.createElement('div');
        time.className = 'message-time';
        time.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        contentDiv.appendChild(bubble);
        contentDiv.appendChild(time);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);

        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        this.messages.push({ role, content, timestamp: new Date() });
    }

    showTypingIndicator() {
        const messagesContainer = document.getElementById('chatMessages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant typing-message';
        typingDiv.id = 'typingIndicator';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = 'AI';

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble typing-indicator';
        bubble.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';

        contentDiv.appendChild(bubble);
        typingDiv.appendChild(avatar);
        typingDiv.appendChild(contentDiv);

        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    removeTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    updateStatus(type, text) {
        const badge = document.getElementById('statusBadge');
        badge.innerHTML = `<span class="status-dot"></span>${text}`;
        
        badge.className = 'status-badge';
        if (type === 'thinking') {
            badge.style.background = 'var(--warning)';
        } else if (type === 'error') {
            badge.style.background = 'var(--error)';
        } else {
            badge.style.background = 'var(--success)';
        }
    }

    updateStats() {
        // Simulate stats - Replace with actual backend stats
        const tokensUsed = Math.min(this.messages.length * 20, this.settings.maxTokens);
        document.getElementById('tokensUsed').textContent = `${tokensUsed}/${this.settings.maxTokens}`;
        document.getElementById('messageCount').textContent = this.messages.length;
        document.getElementById('policyName').textContent = this.settings.policy;
    }

    newChat() {
        if (this.messages.length > 0) {
            if (!confirm('Start a new chat? Current conversation will be saved to history.')) {
                return;
            }
        }

        this.messages = [];
        const messagesContainer = document.getElementById('chatMessages');
        messagesContainer.innerHTML = `
            <div class="welcome-screen">
                <div class="welcome-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                </div>
                <h2>Welcome to Finite Memory AI</h2>
                <p>Start a conversation with intelligent memory management</p>
                <div class="feature-grid">
                    <div class="feature-card">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path>
                        </svg>
                        <span>Fast & Efficient</span>
                    </div>
                    <div class="feature-card">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <path d="M12 2v20M2 12h20"></path>
                        </svg>
                        <span>Smart Context</span>
                    </div>
                    <div class="feature-card">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                        </svg>
                        <span>Real-time Stats</span>
                    </div>
                </div>
                <div class="example-prompts">
                    <p class="example-title">Try asking:</p>
                    <button class="example-prompt" data-prompt="Explain quantum computing in simple terms">
                        Explain quantum computing in simple terms
                    </button>
                    <button class="example-prompt" data-prompt="Write a Python function to sort a list">
                        Write a Python function to sort a list
                    </button>
                    <button class="example-prompt" data-prompt="What are the benefits of AI?">
                        What are the benefits of AI?
                    </button>
                </div>
            </div>
        `;

        // Re-bind example prompt events
        document.querySelectorAll('.example-prompt').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const prompt = e.target.dataset.prompt;
                document.getElementById('messageInput').value = prompt;
                this.sendMessage();
            });
        });

        this.updateStats();
    }

    clearChat() {
        if (this.messages.length === 0) return;

        if (confirm('Clear all messages? This cannot be undone.')) {
            this.newChat();
        }
    }

    exportChat() {
        if (this.messages.length === 0) {
            alert('No messages to export');
            return;
        }

        const chatData = {
            timestamp: new Date().toISOString(),
            settings: this.settings,
            messages: this.messages
        };

        const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat-export-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    openSettings() {
        const modal = document.getElementById('settingsModal');
        modal.classList.add('active');

        // Populate current settings
        document.getElementById('policySelect').value = this.settings.policy;
        document.getElementById('maxTokensRange').value = this.settings.maxTokens;
        document.getElementById('maxTokensValue').textContent = this.settings.maxTokens;
        document.getElementById('modelSelect').value = this.settings.model;
        document.getElementById('telemetryToggle').checked = this.settings.telemetry;
        document.getElementById('darkModeToggle').checked = this.settings.darkMode;
    }

    closeSettings() {
        const modal = document.getElementById('settingsModal');
        modal.classList.remove('active');
    }

    saveSettings() {
        this.settings.policy = document.getElementById('policySelect').value;
        this.settings.maxTokens = parseInt(document.getElementById('maxTokensRange').value);
        this.settings.model = document.getElementById('modelSelect').value;
        this.settings.telemetry = document.getElementById('telemetryToggle').checked;
        this.settings.darkMode = document.getElementById('darkModeToggle').checked;

        localStorage.setItem('chatSettings', JSON.stringify(this.settings));
        this.updateStats();
        this.applyTheme();
        this.closeSettings();

        // Show success message
        this.updateStatus('ready', 'Settings saved');
        setTimeout(() => this.updateStatus('ready', 'Ready'), 2000);
    }

    resetSettings() {
        if (confirm('Reset all settings to defaults?')) {
            this.settings = {
                policy: 'sliding',
                maxTokens: 512,
                model: 'gpt2',
                telemetry: true,
                darkMode: false
            };
            this.openSettings(); // Refresh modal
        }
    }

    loadSettings() {
        const saved = localStorage.getItem('chatSettings');
        if (saved) {
            this.settings = JSON.parse(saved);
        }
    }

    applyTheme() {
        if (this.settings.darkMode) {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
});
