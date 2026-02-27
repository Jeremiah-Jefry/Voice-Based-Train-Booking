/**
 * Voice Widget for Train Booking Platform
 * Floating microphone button with offcanvas panel
 */

class VoiceWidget {
    constructor() {
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.isListening = false;
        this.isProcessing = false;
        this.sessionId = null;
        this.offcanvasInstance = null;
        
        this.initElements();
    }
    
    initElements() {
        // Button and controls
        this.btn = document.getElementById('voiceWidgetBtn');
        this.micBtn = document.getElementById('voiceWidgetMicBtn');
        this.micIcon = document.getElementById('voiceWidgetMicIcon');
        this.micText = document.getElementById('voiceWidgetMicText');
        this.statusBadge = document.getElementById('voiceWidgetStatus');
        
        // Display elements
        this.commandDisplay = document.getElementById('voiceWidgetCommand');
        this.responseDisplay = document.getElementById('voiceWidgetResponse');
        
        // Offcanvas
        this.offcanvas = document.getElementById('voiceOffcanvas');
        this.offcanvasInstance = new bootstrap.Offcanvas(this.offcanvas);
    }
    
    initialize() {
        if (!this.checkBrowserSupport()) {
            console.warn('Voice recognition not supported');
            this.btn.style.display = 'none';
            return;
        }
        
        this.setupSpeechRecognition();
        this.setupEventListeners();
        console.log('Voice Widget initialized');
    }
    
    checkBrowserSupport() {
        return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
    }
    
    setupSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-IN';
        
        this.recognition.onstart = () => this.onStart();
        this.recognition.onresult = (event) => this.onResult(event);
        this.recognition.onerror = (event) => this.onError(event);
        this.recognition.onend = () => this.onEnd();
    }
    
    setupEventListeners() {
        // Floating button - open offcanvas
        this.btn.addEventListener('click', () => {
            this.offcanvasInstance.show();
            this.showInitialGreeting();
        });
        
        // Microphone button - toggle listening
        this.micBtn.addEventListener('click', () => this.toggleListening());
        
        // Keyboard shortcut - Ctrl+Space
        document.addEventListener('keydown', (event) => {
            if (event.ctrlKey && event.code === 'Space') {
                event.preventDefault();
                this.toggleListening();
            }
        });
    }
    
    toggleListening() {
        if (this.isListening) {
            this.stopListening();
        } else {
            this.startListening();
        }
    }
    
    startListening() {
        if (this.isListening || this.isProcessing) return;
        
        try {
            this.isListening = true;
            this.recognition.start();
            this.updateUI('listening');
            this.updateStatus('Listening...', 'warning');
            this.commandDisplay.innerHTML = '<em class="text-muted">Listening for your command...</em>';
        } catch (error) {
            console.error('Error starting recognition:', error);
            this.updateStatus('Error', 'danger');
        }
    }
    
    stopListening() {
        if (!this.isListening) return;
        this.isListening = false;
        this.recognition.stop();
        this.updateUI('idle');
        this.updateStatus('Ready', 'secondary');
    }
    
    onStart() {
        // Recognition started
        this.btn.classList.add('listening');
    }
    
    onResult(event) {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            
            if (event.results[i].isFinal) {
                finalTranscript += transcript + ' ';
            } else {
                interimTranscript += transcript;
            }
        }
        
        if (finalTranscript) {
            this.displayCommand(finalTranscript);
            this.processCommand(finalTranscript);
        } else if (interimTranscript) {
            this.commandDisplay.innerHTML = `<em class="text-muted">${interimTranscript}</em>`;
        }
    }
    
    onError(event) {
        console.error('Speech recognition error:', event.error);
        this.updateStatus('Error: ' + event.error, 'danger');
        
        const errorMessages = {
            'no-speech': 'No speech detected. Please try again.',
            'audio-capture': 'No microphone found. Please check your audio settings.',
            'network': 'Network error. Please check your connection.',
            'not-allowed': 'Microphone permission denied.'
        };
        
        const message = errorMessages[event.error] || 'An error occurred.';
        this.responseDisplay.innerHTML = `<em class="text-danger">${message}</em>`;
    }
    
    onEnd() {
        this.isListening = false;
        this.btn.classList.remove('listening');
        this.updateUI('idle');
    }
    
    displayCommand(command) {
        this.commandDisplay.innerHTML = `<strong>${command}</strong>`;
    }
    
    processCommand(command) {
        if (!command || this.isProcessing) return;
        
        this.isProcessing = true;
        this.updateStatus('Processing...', 'info');
        
        fetch('/voice/process-command', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                command: command,
                session_id: this.sessionId
            })
        })
        .then(response => response.json())
        .then(data => {
            this.sessionId = data.session_id;
            this.displayResponse(data.speak || data.response);
            this.updateStatus('Ready', 'secondary');
            this.isProcessing = false;
            
            // Auto-read response
            this.speakResponse(data.speak || data.response);
            
            // Handle action results
            if (data.action) {
                this.handleAction(data.action, data.data);
            }
        })
        .catch(error => {
            console.error('Error processing command:', error);
            this.responseDisplay.innerHTML = '<em class="text-danger">Error processing command. Please try again.</em>';
            this.updateStatus('Error', 'danger');
            this.isProcessing = false;
        });
    }
    
    displayResponse(responseText) {
        // Limit response text length for display
        const displayText = responseText.length > 200 
            ? responseText.substring(0, 200) + '...' 
            : responseText;
        
        this.responseDisplay.innerHTML = `<div>${displayText}</div>`;
    }
    
    speakResponse(text) {
        if (!this.synthesis) return;
        
        // Cancel any ongoing speech
        this.synthesis.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-IN';
        utterance.rate = 0.95;  // Slightly slower for clarity
        utterance.pitch = 1.4;  // Female voice pitch
        utterance.volume = 1.0;
        
        // Try to select a female voice
        const voices = this.synthesis.getVoices();
        const femaleVoice = voices.find(voice => 
            voice.lang.includes('en') && (voice.name.includes('Female') || voice.name.includes('female'))
        );
        
        if (femaleVoice) {
            utterance.voice = femaleVoice;
        }
        
        this.synthesis.speak(utterance);
    }
    
    handleAction(action, data) {
        console.log('Action:', action, 'Data:', data);
        
        switch (action) {
            case 'show_pnr':
                this.displayPNRStatus(data);
                break;
            // Add other actions here
        }
    }
    
    displayPNRStatus(data) {
        const html = `
            <div class="card mt-2 border-primary shadow-sm">
                <div class="card-header bg-primary text-white py-1 px-2 small">
                    <i class="fas fa-ticket-alt me-1"></i>PNR Check Result
                </div>
                <div class="card-body p-2 small">
                    <p class="mb-1"><strong>PNR:</strong> ${data.pnr_number}</p>
                    <p class="mb-1"><strong>Passenger:</strong> ${data.passenger_name}</p>
                    <p class="mb-1"><strong>Train:</strong> ${data.train_name}</p>
                    <p class="mb-1"><strong>Status:</strong> <span class="badge bg-success">${data.booking_status}</span></p>
                    <p class="mb-0"><strong>Journey:</strong> ${data.source} to ${data.destination}</p>
                </div>
            </div>
        `;
        this.responseDisplay.innerHTML += html;
    }
    
    showInitialGreeting() {
        this.responseDisplay.innerHTML = '<div><strong>Hello! 👋 I\'m Sarah, your voice train booking assistant.</strong><br><br>I can help you search trains, check PNR status, or view your bookings. Just say "Help" to see all commands, or ask me something like "Search trains from Mumbai to Delhi"!</div>';
    }
    
    updateUI(state) {
        if (state === 'listening') {
            this.micIcon.className = 'fas fa-stop-circle';
            this.micText.textContent = 'Stop';
            this.micBtn.classList.add('btn-danger');
            this.micBtn.classList.remove('btn-primary');
        } else {
            this.micIcon.className = 'fas fa-microphone';
            this.micText.textContent = 'Start';
            this.micBtn.classList.add('btn-primary');
            this.micBtn.classList.remove('btn-danger');
        }
    }
    
    updateStatus(text, badgeClass) {
        this.statusBadge.textContent = text;
        this.statusBadge.className = `badge bg-${badgeClass} ms-2`;
    }
}

// Initialize voice widget when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const voiceWidget = new VoiceWidget();
    voiceWidget.initialize();
});
