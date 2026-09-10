const chatBox   = document.getElementById('chat-box');
const userInput = document.getElementById('user-input');
const sendBtn   = document.getElementById('send-btn');
const micBtn    = document.getElementById('mic-btn');
const statusEl  = document.getElementById('voice-status');

// Add a message to the chat
function addMessage(text, sender) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    div.innerText = text;          // preserves newlines
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function setStatus(txt) {
    if (statusEl) statusEl.innerText = txt || '';
}

// ---------------- Text chat (unchanged) ----------------
async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

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
        const data = await response.json();
        const reply = data.reply || "I'm sorry, I didn't understand that.";
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

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendMessage();
});
userInput.focus();

// ---------------- Voice chat ----------------
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let recordingStartTime = 0;

async function startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        addMessage('⚠️ Your browser does not support microphone access.', 'bot');
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        const preferred = 'audio/webm;codecs=opus';
        const mimeType = MediaRecorder.isTypeSupported(preferred)
            ? preferred
            : (MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '');

        mediaRecorder = mimeType
            ? new MediaRecorder(stream, { mimeType })
            : new MediaRecorder(stream);

        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = async () => {
            stream.getTracks().forEach(t => t.stop());

            const duration = Date.now() - recordingStartTime;
            console.log('[voice] recording stopped, duration(ms):', duration);

            if (duration < 500) {
                addMessage('⚠️ Recording too short — please speak for at least half a second.', 'bot');
                setStatus('');
                return;
            }

            const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
            console.log('[voice] blob size (bytes):', blob.size);

            if (blob.size === 0) {
                addMessage('⚠️ No audio captured. Try again.', 'bot');
                setStatus('');
                return;
            }

            await sendVoice(blob);
        };

        recordingStartTime = Date.now();
        mediaRecorder.start();
        isRecording = true;
        micBtn.classList.add('recording');
        micBtn.innerText = '⏹';
        setStatus('🎙️ Recording... click ⏹ to stop.');
    } catch (err) {
        console.error('[voice] getUserMedia error:', err);
        addMessage('⚠️ Microphone permission denied.', 'bot');
        setStatus('');
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        micBtn.classList.remove('recording');
        micBtn.innerText = '🎤';
        setStatus('⏳ Transcribing...');
    }
}

micBtn.addEventListener('click', () => {
    if (isRecording) stopRecording();
    else startRecording();
});

async function sendVoice(blob) {
    userInput.disabled = true;
    sendBtn.disabled = true;
    micBtn.disabled = true;

    const form = new FormData();
    form.append('audio', blob, 'clip.webm');

    try {
        const response = await fetch('/voice/chat', { method: 'POST', body: form });
        console.log('[voice] HTTP status:', response.status);

        if (!response.ok) {
            const errText = await response.text();
            console.error('[voice] server error body:', errText);
            throw new Error(`HTTP ${response.status}: ${errText}`);
        }

        const data = await response.json();
        console.log('[voice] response payload:', data);

        // Show transcript — BOTH in chat AND momentarily in the input field
        const transcript = (data.transcript || '').trim();
        if (transcript) {
            addMessage(transcript, 'user');

            // Mirror into the input field so you can see exactly what was heard
            userInput.value = transcript;
            setTimeout(() => {
                if (userInput.value === transcript) userInput.value = '';
            }, 1500);
        } else {
            addMessage('⚠️ (empty transcript — nothing was heard)', 'bot');
        }

        // Show bot reply
        const reply = data.reply || "I'm sorry, I didn't understand that.";
        const replyText = typeof reply === 'string' ? reply : JSON.stringify(reply);
        addMessage(replyText, 'bot');

        // Play audio if the backend produced any
        if (data.audio_b64) {
            const audio = new Audio('data:audio/wav;base64,' + data.audio_b64);
            audio.play().catch(e => console.warn('[voice] autoplay blocked:', e));
        } else {
            console.warn('[voice] no audio_b64 in response — TTS may still be failing');
        }

        setStatus('');
    } catch (error) {
        console.error('[voice] request failed:', error);
        addMessage('⚠️ Voice request failed. Open DevTools → Console for details.', 'bot');
        setStatus('❌ Voice request failed.');
    } finally {
        userInput.disabled = false;
        sendBtn.disabled = false;
        micBtn.disabled = false;
        userInput.focus();
    }
}