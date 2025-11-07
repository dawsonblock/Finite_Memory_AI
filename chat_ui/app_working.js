// Simple Working Chat UI - JavaScript
class ChatApp {
    constructor() {
        console.log('ChatApp constructor called');
        this.messages = [];
        this.settings = {
            policy: 'sliding',
            maxTokens: 512,
            model: 'deepseek-chat',
            darkMode: false
        };
        
        this.init();
    }

    init() {
        console.log('Initializing ChatApp...');
        this.bindEvents();
        this.updateStats();
        console.log('ChatApp initialized successfully');
    }

    bindEvents() {
        const messageInput = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');

        if (!messageInput || !sendBtn) {
            console.error('Required elements not found!');
            return;
        }

        // Input auto-resize
        messageInput.addEventListener('input', (e) => {
            this.autoResize(e.target);
            const charCount = document.getElementById('charCount');
            if (charCount) {
                charCount.textContent = `${e.target.value.length} characters`;
            }
        });

        // Enter key to send
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                console.log('Enter key pressed');
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Send button click
        sendBtn.addEventListener('click', () => {
            console.log('Send button clicked');
            this.sendMessage();
        });

        // New chat button
        const newChatBtn = document.getElementById('newChatBtn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => this.newChat());
        }

        // Clear chat button
        const clearBtn = document.getElementById('clearBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearChat());
        }

        // Export chat button
        const exportBtn = document.getElementById('exportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportChat());
        }

        // Settings button
        const settingsBtn = document.getElementById('settingsBtn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.openSettings());
        }

        // Close settings button
        const closeSettingsBtn = document.getElementById('closeSettingsBtn');
        if (closeSettingsBtn) {
            closeSettingsBtn.addEventListener('click', () => this.closeSettings());
        }

        // Save settings button
        const saveSettingsBtn = document.getElementById('saveSettingsBtn');
        if (saveSettingsBtn) {
            saveSettingsBtn.addEventListener('click', () => this.saveSettings());
        }

        // Reset settings button
        const resetSettingsBtn = document.getElementById('resetSettingsBtn');
        if (resetSettingsBtn) {
            resetSettingsBtn.addEventListener('click', () => this.resetSettings());
        }

        // Max tokens range slider
        const maxTokensRange = document.getElementById('maxTokensRange');
        if (maxTokensRange) {
            maxTokensRange.addEventListener('input', (e) => {
                const maxTokensValue = document.getElementById('maxTokensValue');
                if (maxTokensValue) {
                    maxTokensValue.textContent = e.target.value;
                }
            });
        }

        // Dark mode toggle
        const darkModeToggle = document.getElementById('darkModeToggle');
        if (darkModeToggle) {
            darkModeToggle.addEventListener('change', (e) => {
                this.settings.darkMode = e.target.checked;
                this.applyTheme();
            });
        }

        // Close modal on outside click
        const settingsModal = document.getElementById('settingsModal');
        if (settingsModal) {
            settingsModal.addEventListener('click', (e) => {
                if (e.target.id === 'settingsModal') {
                    this.closeSettings();
                }
            });
        }

        // Attach file button
        const attachBtn = document.getElementById('attachBtn');
        if (attachBtn) {
            attachBtn.addEventListener('click', () => this.handleFileUpload());
        }

        // Example prompts
        document.querySelectorAll('.example-prompt').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const prompt = e.target.dataset.prompt;
                const input = document.getElementById('messageInput');
                if (input) {
                    input.value = prompt;
                    this.sendMessage();
                }
            });
        });

        console.log('Event listeners bound');
    }

    autoResize(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }

    async sendMessage() {
        console.log('sendMessage called');
        const input = document.getElementById('messageInput');
        const message = input.value.trim();

        if (!message) {
            console.log('Empty message, returning');
            return;
        }

        console.log('Sending message:', message);

        // Clear input
        input.value = '';
        input.style.height = 'auto';
        const charCount = document.getElementById('charCount');
        if (charCount) {
            charCount.textContent = '0 characters';
        }

        // Hide welcome screen
        const welcomeScreen = document.querySelector('.welcome-screen');
        if (welcomeScreen) {
            welcomeScreen.remove();
        }

        // Add user message
        this.addMessage('user', message);

        // Show typing indicator
        this.showTypingIndicator();

        try {
            console.log('Calling backend...');
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Got response:', data);

            this.removeTypingIndicator();

            if (data.success) {
                this.addMessage('assistant', data.response);
                if (data.stats) {
                    this.updateStatsFromBackend(data.stats);
                }
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        } catch (error) {
            console.error('Error:', error);
            this.removeTypingIndicator();
            this.addMessage('assistant', 'Sorry, I encountered an error: ' + error.message);
        }

        this.updateStats();
    }

    addMessage(role, content) {
        console.log('Adding message:', role, content.substring(0, 50));
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

        // Parse thinking/reasoning if present (for AI messages)
        if (role === 'assistant' && content.includes('**Thinking:**')) {
            console.log('Found thinking section');
            bubble.classList.add('has-thinking');

            // Split thinking and response
            const parts = content.split('**Thinking:**');
            if (parts.length > 1) {
                const thinkingAndResponse = parts[1].split('\n\n');
                const thinking = thinkingAndResponse[0].trim();
                const response = thinkingAndResponse.slice(1).join('\n\n').trim();

                console.log('Thinking:', thinking);
                console.log('Response:', response.substring(0, 50));

                // Create thinking section
                const thinkingSection = document.createElement('div');
                thinkingSection.className = 'thinking-section';
                thinkingSection.innerHTML = `
                    <h4>💭 AI Reasoning Process</h4>
                    <div class="thinking-content">${this.escapeHtml(thinking)}</div>
                `;

                // Create response section
                const responseSection = document.createElement('div');
                responseSection.className = 'response-section';
                responseSection.innerHTML = this.formatMarkdown(response);

                bubble.appendChild(thinkingSection);
                bubble.appendChild(responseSection);
            } else {
                bubble.innerHTML = this.formatMarkdown(content);
            }
        } else {
            // Regular message
            bubble.innerHTML = this.formatMarkdown(content);
        }

        const time = document.createElement('div');
        time.className = 'message-time';
        time.textContent = new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });

        contentDiv.appendChild(bubble);
        contentDiv.appendChild(time);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(contentDiv);
        messagesContainer.appendChild(messageDiv);

        this.messages.push({ role, content, timestamp: Date.now() });
        this.scrollToBottom();
    }

    formatMarkdown(text) {
        // Simple markdown formatting
        return text
            .replace(/### (.*?)(\n|$)/g, '<h3>$1</h3>')
            .replace(/## (.*?)(\n|$)/g, '<h2>$1</h2>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showTypingIndicator() {
        const messagesContainer = document.getElementById('chatMessages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant';
        typingDiv.id = 'typingIndicator';
        typingDiv.innerHTML = `
            <div class="message-avatar">AI</div>
            <div class="message-content">
                <div class="message-bubble thinking-bubble">
                    <div class="thinking-animation">
                        <svg class="thinking-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                            <circle cx="9" cy="10" r="1" fill="currentColor"/>
                            <circle cx="12" cy="10" r="1" fill="currentColor"/>
                            <circle cx="15" cy="10" r="1" fill="currentColor"/>
                        </svg>
                        <span class="thinking-text">AI is thinking...</span>
                    </div>
                </div>
            </div>
        `;
        messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    updateStats() {
        const messageCount = document.getElementById('messageCount');
        if (messageCount) {
            messageCount.textContent = this.messages.length;
        }
    }

    updateStatsFromBackend(stats) {
        console.log('Updating stats from backend:', stats);
        
        // Update tokens
        if (stats.tokens_retained !== undefined) {
            const tokensUsed = document.getElementById('tokensUsed');
            if (tokensUsed) {
                tokensUsed.textContent = `${stats.tokens_retained}/${this.settings.maxTokens}`;
            }
        }
        
        // Update message count
        const messageCount = document.getElementById('messageCount');
        if (messageCount) {
            messageCount.textContent = this.messages.length;
        }
        
        // Show eviction notification if any
        if (stats.evictions && stats.evictions > 0) {
            const totalEvictions = stats.evictions;
            this.showNotification(
                `Memory limit reached! Evicted ${totalEvictions} old message${totalEvictions > 1 ? 's' : ''} to stay within ${this.settings.maxTokens} token limit.`,
                'warning'
            );
        }
        
        // Update policy display
        const policyName = document.getElementById('policyName');
        if (policyName && this.settings.policy) {
            policyName.textContent = this.settings.policy;
        }
    }

    newChat() {
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
                const input = document.getElementById('messageInput');
                if (input) {
                    input.value = prompt;
                    this.sendMessage();
                }
            });
        });
        
        this.updateStats();
        console.log('New chat started');
    }

    clearChat() {
        if (confirm('Are you sure you want to clear the chat history?')) {
            this.newChat();
        }
    }

    exportChat() {
        const chatData = {
            messages: this.messages,
            timestamp: new Date().toISOString(),
            settings: this.settings
        };

        const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat-export-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        console.log('Chat exported');
    }

    openSettings() {
        const modal = document.getElementById('settingsModal');
        if (modal) {
            modal.style.display = 'flex';
            
            // Load current settings into form
            const policySelect = document.getElementById('policySelect');
            const maxTokensRange = document.getElementById('maxTokensRange');
            const maxTokensValue = document.getElementById('maxTokensValue');
            const modelSelect = document.getElementById('modelSelect');
            const telemetryToggle = document.getElementById('telemetryToggle');
            const darkModeToggle = document.getElementById('darkModeToggle');

            if (policySelect) policySelect.value = this.settings.policy;
            if (maxTokensRange) maxTokensRange.value = this.settings.maxTokens;
            if (maxTokensValue) maxTokensValue.textContent = this.settings.maxTokens;
            if (modelSelect) modelSelect.value = this.settings.model;
            if (telemetryToggle) telemetryToggle.checked = this.settings.telemetry !== false;
            if (darkModeToggle) darkModeToggle.checked = this.settings.darkMode;
        }
    }

    closeSettings() {
        const modal = document.getElementById('settingsModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    saveSettings() {
        const policySelect = document.getElementById('policySelect');
        const maxTokensRange = document.getElementById('maxTokensRange');
        const modelSelect = document.getElementById('modelSelect');
        const telemetryToggle = document.getElementById('telemetryToggle');
        const darkModeToggle = document.getElementById('darkModeToggle');

        if (policySelect) this.settings.policy = policySelect.value;
        if (maxTokensRange) this.settings.maxTokens = parseInt(maxTokensRange.value);
        if (modelSelect) this.settings.model = modelSelect.value;
        if (telemetryToggle) this.settings.telemetry = telemetryToggle.checked;
        if (darkModeToggle) this.settings.darkMode = darkModeToggle.checked;

        // Update UI
        const policyName = document.getElementById('policyName');
        if (policyName) {
            policyName.textContent = this.settings.policy;
        }

        this.applyTheme();
        this.closeSettings();

        console.log('Settings saved:', this.settings);
    }

    resetSettings() {
        if (confirm('Reset all settings to defaults?')) {
            this.settings = {
                policy: 'sliding',
                maxTokens: 512,
                model: 'deepseek-chat',
                telemetry: true,
                darkMode: false
            };

            this.openSettings(); // Reload form with defaults
            console.log('Settings reset to defaults');
        }
    }

    applyTheme() {
        if (this.settings.darkMode) {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
    }

    handleFileUpload() {
        // Create hidden file input
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = '*/*'; // Accept all file types
        fileInput.style.display = 'none';
        
        fileInput.addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            // Check file size (max 10MB)
            if (file.size > 10 * 1024 * 1024) {
                alert('File too large! Maximum size is 10MB.');
                return;
            }

            try {
                const input = document.getElementById('messageInput');
                if (!input) return;

                // Detect file type
                const isTextFile = this.isTextFile(file.name);
                const isBinaryFile = !isTextFile;

                if (isTextFile) {
                    // Read text files
                    const text = await file.text();
                    const preview = text.substring(0, 3000);
                    const truncated = text.length > 3000;
                    
                    const filePrompt = `I've uploaded a text file named "${file.name}" (${this.formatFileSize(file.size)}):\n\n\`\`\`\n${preview}${truncated ? '\n... (truncated, showing first 3000 characters)' : ''}\n\`\`\`\n\nPlease analyze this file.`;
                    input.value = filePrompt;
                } else {
                    // Handle binary files (images, zip, etc.)
                    const fileInfo = this.getFileInfo(file);
                    const filePrompt = `I've uploaded a ${fileInfo.type} file:\n\n**File Name:** ${file.name}\n**File Size:** ${this.formatFileSize(file.size)}\n**File Type:** ${file.type || 'unknown'}\n**Extension:** ${fileInfo.extension}\n\nPlease provide information about this type of file and what you can help me with regarding it.`;
                    input.value = filePrompt;
                }

                this.autoResize(input);
                this.showNotification(`File "${file.name}" (${this.formatFileSize(file.size)}) loaded!`, 'success');
                
            } catch (error) {
                console.error('Error reading file:', error);
                this.showNotification('Error reading file: ' + error.message, 'error');
            }
            
            // Clean up
            document.body.removeChild(fileInput);
        });
        
        // Trigger file selection
        document.body.appendChild(fileInput);
        fileInput.click();
    }

    isTextFile(filename) {
        const textExtensions = [
            'txt', 'md', 'json', 'csv', 'log', 'xml', 'html', 'htm', 'css', 'js', 'ts', 
            'jsx', 'tsx', 'py', 'java', 'c', 'cpp', 'h', 'hpp', 'cs', 'php', 'rb', 'go',
            'rs', 'swift', 'kt', 'scala', 'sh', 'bash', 'yml', 'yaml', 'toml', 'ini',
            'conf', 'config', 'sql', 'r', 'matlab', 'm', 'vue', 'svelte', 'dockerfile'
        ];
        const ext = filename.split('.').pop().toLowerCase();
        return textExtensions.includes(ext);
    }

    getFileInfo(file) {
        const ext = file.name.split('.').pop().toLowerCase();
        const typeMap = {
            'zip': 'compressed archive',
            'rar': 'compressed archive',
            '7z': 'compressed archive',
            'tar': 'archive',
            'gz': 'compressed archive',
            'pdf': 'PDF document',
            'doc': 'Word document',
            'docx': 'Word document',
            'xls': 'Excel spreadsheet',
            'xlsx': 'Excel spreadsheet',
            'ppt': 'PowerPoint presentation',
            'pptx': 'PowerPoint presentation',
            'jpg': 'image',
            'jpeg': 'image',
            'png': 'image',
            'gif': 'image',
            'bmp': 'image',
            'svg': 'vector image',
            'webp': 'image',
            'mp3': 'audio',
            'wav': 'audio',
            'mp4': 'video',
            'avi': 'video',
            'mov': 'video',
            'exe': 'executable',
            'dll': 'library',
            'so': 'library',
            'dylib': 'library'
        };
        
        return {
            extension: ext,
            type: typeMap[ext] || 'binary'
        };
    }

    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        const colors = {
            'success': '#10b981',
            'error': '#ef4444',
            'info': '#4f46e5',
            'warning': '#f59e0b'
        };
        
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            background: ${colors[type] || colors.info};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                if (notification.parentNode) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing ChatApp...');
    window.chatApp = new ChatApp();
    console.log('ChatApp ready:', window.chatApp);
});
