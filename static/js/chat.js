document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const sessionList = document.getElementById('sessions');
    const newChatButton = document.getElementById('new-chat-button');
    const newChatForm = document.getElementById('new-chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatHistory = document.getElementById('chat-history');
    const sendNewChatButton = document.getElementById('send-new-chat');
    const sendMessageButton = document.getElementById('send-message-button');

    // State
    let currentUser = null;
    let activeSessionId = null;

    // --- Authentication ---
    auth.onAuthStateChanged(user => {
        if (user) {
            currentUser = user;
            fetchSessions();
            setupEventListeners();
            // Initially, show the new chat form
            showNewChatForm();
        } else {
            window.location.href = '/';
        }
    });

    // --- UI State Management ---
    const showNewChatForm = () => {
        activeSessionId = null;
        newChatForm.style.display = 'block';
        chatInput.style.display = 'none';
        chatHistory.innerHTML = '<p>Select a session or start a new one.</p>';
    };

    const showExistingChat = () => {
        newChatForm.style.display = 'none';
        chatInput.style.display = 'block';
    };

    // --- Data Fetching and Rendering ---
    const fetchSessions = () => {
        currentUser.getIdToken().then(token => {
            fetch('/api/sessions', {
                headers: { 'Authorization': `Bearer ${token}` }
            })
            .then(res => res.json())
            .then(sessions => {
                if (Array.isArray(sessions)) {
                    renderSessionList(sessions);
                } else {
                    console.error('Error fetching sessions:', sessions.error || 'Unknown error');
                }
            })
            .catch(error => console.error('Error fetching sessions:', error));
        });
    };

    const renderSessionList = (sessions) => {
        sessionList.innerHTML = ''; // Clear existing list
        sessions.forEach(session => {
            const li = document.createElement('li');
            li.textContent = session.title || session.sessionId;
            li.dataset.sessionId = session.sessionId;
            li.classList.add('session-item');
            sessionList.appendChild(li);
        });
    };

    const fetchAndRenderSession = (sessionId) => {
        activeSessionId = sessionId;
        currentUser.getIdToken().then(token => {
            fetch(`/api/sessions/${sessionId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })
            .then(res => res.json())
            .then(sessionData => {
                renderChatHistory(sessionData.conversation_history);
                showExistingChat();
            })
            .catch(error => console.error('Error fetching session details:', error));
        });
    };

    const renderChatHistory = (history) => {
        chatHistory.innerHTML = '';
        if (history && history.length > 0) {
            history.forEach(message => {
                appendMessageToHistory(message);
            });
        } else {
            chatHistory.innerHTML = '<p>No messages in this chat yet.</p>';
        }
        chatHistory.scrollTop = chatHistory.scrollHeight; // Scroll to bottom
    };

    const appendMessageToHistory = (message) => {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', message.role);
        messageDiv.textContent = message.content;

        if (message.role === 'model') {
            const debugButton = document.createElement('button');
            debugButton.textContent = 'Debug';
            debugButton.classList.add('debug-button');
            debugButton.addEventListener('click', () => {
                const modal = document.getElementById('debug-modal');
                const debugContent = document.getElementById('debug-content');
                const debugInfo = message.debug_info;
                
                debugContent.innerHTML = `
                    <div class="debug-card">
                        <h3>System Prompt</h3>
                        <pre>${debugInfo.system_prompt}</pre>
                    </div>
                    <div class="debug-card">
                        <h3>Conversation History</h3>
                        <pre>${JSON.stringify(debugInfo.conversation_history, null, 2)}</pre>
                    </div>
                    <div class="debug-card">
                        <h3>Tool Calls</h3>
                        <pre>${JSON.stringify(debugInfo.tool_calls, null, 2)}</pre>
                    </div>
                    <div class="debug-card">
                        <h3>Tool Responses</h3>
                        <pre>${JSON.stringify(debugInfo.tool_responses, null, 2)}</pre>
                    </div>
                    <div class="debug-card">
                        <h3>Full Response</h3>
                        <pre>${debugInfo.full_response}</pre>
                    </div>
                `;

                modal.style.display = 'block';
            });
            messageDiv.appendChild(debugButton);
        }

        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    };

    // --- Event Listeners Setup ---
    const setupEventListeners = () => {
        newChatButton.addEventListener('click', showNewChatForm);

        sessionList.addEventListener('click', (event) => {
            if (event.target && event.target.matches('li.session-item')) {
                const sessionId = event.target.dataset.sessionId;
                fetchAndRenderSession(sessionId);
            }
        });

        sendNewChatButton.addEventListener('click', handleSendMessage);
        sendMessageButton.addEventListener('click', handleSendMessage);

        // Modal close button
        const modal = document.getElementById('debug-modal');
        const closeButton = document.getElementsByClassName('close')[0];
        closeButton.onclick = function() {
            modal.style.display = 'none';
        }
        window.onclick = function(event) {
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }
    };

    // --- Message Sending ---
    const handleSendMessage = () => {
        let messagePayload;
        let userMessageContent;

        if (activeSessionId) {
            // Sending message in an existing chat
            const messageInput = document.getElementById('user-message-existing');
            userMessageContent = messageInput.value.trim();
            if (!userMessageContent) return;

            messagePayload = {
                sessionId: activeSessionId,
                message: userMessageContent
            };
            messageInput.value = '';

        } else {
            // Starting a new chat
            const jsonInput = document.getElementById('json-input').value;
            if (!jsonInput) {
                alert('JSON input is required to start a new chat.');
                return;
            }

            try {
                const parsedJson = JSON.parse(jsonInput);
                userMessageContent = parsedJson.thread_contents;
                messagePayload = {
                    thread_id: parsedJson.thread_id,
                    recipients: parsedJson.recipients,
                    message: userMessageContent
                };
            } catch (error) {
                alert('Invalid JSON format.');
                return;
            }
            
            // Clear new chat form
            document.getElementById('json-input').value = '';
        }

        // Append user message to UI immediately
        appendMessageToHistory({ role: 'user', content: userMessageContent });

        // Send to backend
        currentUser.getIdToken().then(token => {
            fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(messagePayload)
            })
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                // Append assistant response to UI
                appendMessageToHistory({ role: 'model', content: data.response, debug_info: data.debug_info });

                // If it was a new chat, we now have a session ID
                if (!activeSessionId) {
                    activeSessionId = data.sessionId;
                    showExistingChat();
                    fetchSessions(); // Refresh session list
                }
            })
            .catch(error => {
                console.error('Error sending message:', error);
                appendMessageToHistory({ role: 'model', content: `Error: ${error.message}` });
            });
        });
    };
});
