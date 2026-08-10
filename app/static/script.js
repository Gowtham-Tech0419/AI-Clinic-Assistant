const chatBox = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

// Add a message to the chat
function addMessage(text, sender) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    // Preserve newlines
    div.innerText = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// Send user message to backend
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    // Display user message
    addMessage(message, 'user');
    userInput.value = '';
    userInput.disabled = true;
    sendBtn.disabled = true;

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        // In the sendMessage function, after getting the response:
        const data = await response.json();
        const reply = data.reply || "I'm sorry, I didn't understand that.";

        // Ensure reply is a string
        const replyText = typeof reply === 'string' ? reply : JSON.stringify(reply);
        addMessage(replyText, 'bot');
    } catch (error) {
        addMessage('⚠️ Error connecting to server.', 'bot');
    } finally {
        userInput.disabled = false;
        sendBtn.disabled = false;
        userInput.focus();
    }
}

// Event listeners
sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// Focus input on load
userInput.focus();