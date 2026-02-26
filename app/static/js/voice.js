/**
 * Voice Interface for Train Booking Platform
 * Speech-to-Text using Web Speech API
 */

class VoiceInterface {
    constructor(options = {}) {
        this.options = {
            apiEndpoint: '/voice/process-command',
            language: 'en-IN',
            continuous: false,  // Changed to false for reliability
            interimResults: true,
            ...options
        };
        
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.isListening = false;
        this.isProcessing = false;
        this.sessionId = this.generateSessionId();
        
        // DOM elements
        this.voiceBtn = null;
        this.voiceIcon = null;
        this.voiceText = null;
        this.voiceStatus = null;
        this.interimResults = null;
        this.finalCommand = null;
        this.assistantResponse = null;
        this.actionResults = null;
        this.speakBtn = null;
        this.volumeIndicator = null;
        
        this.lastResponse = '';
        this.commandHistory = [];
    }
    
    generateSessionId() {
        return 'voice_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    initialize() {
        console.log('[Voice] Initializing Voice Interface...');
        
        // Check browser support
        if (!this.checkBrowserSupport()) {
            this.showError('Your browser does not support voice recognition. Please use Chrome or Edge.');
            return;
        }
        
        // Initialize DOM elements
        if (!this.initializeDOMElements()) {
            console.error('[Voice] Failed to initialize DOM elements');
            return;
        }
        
        // Setup speech recognition
        this.setupSpeechRecognition();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Show ready status
        this.updateStatus('Ready - Click microphone to speak', 'ready');
        
        console.log('[Voice] Voice Interface initialized successfully');
        console.log('[Voice] Session ID:', this.sessionId);
    }
    
    checkBrowserSupport() {
        const supported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
        console.log('[Voice] Browser support:', supported);
        return supported;
    }
    
    initializeDOMElements() {
        this.voiceBtn = document.getElementById('voiceBtn');
        this.voiceIcon = document.getElementById('voiceIcon');
        this.voiceText = document.getElementById('voiceText');
        this.voiceStatus = document.getElementById('voiceStatus');
        this.interimResults = document.getElementById('interimResults');
        this.finalCommand = document.getElementById('finalCommand');
        this.assistantResponse = document.getElementById('assistantResponse');
        this.actionResults = document.getElementById('actionResults');
        this.speakBtn = document.getElementById('speakBtn');
        this.volumeIndicator = document.getElementById('volumeIndicator');
        
        if (!this.voiceBtn) {
            console.error('[Voice] Required DOM elements not found');
            return false;
        }
        
        return true;
    }
    
    setupSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        // Configure recognition for reliability
        this.recognition.continuous = false;  // One command at a time
        this.recognition.interimResults = true;  // Show real-time text
        this.recognition.lang = this.options.language;
        this.recognition.maxAlternatives = 1;
        
        // Event handlers
        this.recognition.onstart = () => {
            console.log('[Voice] Recognition started');
            this.isListening = true;
            this.updateUI('listening');
            this.updateStatus('🎤 Listening... Speak now!', 'listening');
            this.updateInterimResults('Listening...');
        };
        
        this.recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                const confidence = event.results[i][0].confidence;
                
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                    console.log('[Voice] Final:', transcript, 'Confidence:', confidence);
                } else {
                    interimTranscript += transcript;
                }
            }
            
            // Show real-time transcription
            if (interimTranscript) {
                this.updateInterimResults('🗣️ ' + interimTranscript);
            }
            
            // Process final command
            if (finalTranscript && finalTranscript.trim()) {
                this.updateFinalCommand(finalTranscript.trim());
                this.processVoiceCommand(finalTranscript.trim());
            }
        };
        
        this.recognition.onerror = (event) => {
            console.error('[Voice] Error:', event.error);
            this.isListening = false;
            this.updateUI('idle');
            
            switch (event.error) {
                case 'no-speech':
                    this.updateStatus('No speech detected. Click microphone to try again.', 'ready');
                    this.updateInterimResults('No speech detected. Try again.');
                    break;
                case 'audio-capture':
                    this.showError('Microphone not available. Check your microphone settings.');
                    break;
                case 'not-allowed':
                    this.showError('Microphone access denied. Please allow microphone access in browser settings.');
                    break;
                case 'network':
                    this.showError('Network error. Please check your internet connection.');
                    break;
                case 'aborted':
                    this.updateStatus('Ready - Click microphone to speak', 'ready');
                    break;
                default:
                    this.updateStatus('Error: ' + event.error + '. Try again.', 'ready');
            }
        };
        
        this.recognition.onend = () => {
            console.log('[Voice] Recognition ended');
            this.isListening = false;
            this.updateUI('idle');
            if (!this.isProcessing) {
                this.updateStatus('Ready - Click microphone to speak', 'ready');
            }
        };
    }
    
    setupEventListeners() {
        // Voice button click
        this.voiceBtn.addEventListener('click', () => {
            if (this.isProcessing) {
                console.log('[Voice] Still processing, please wait...');
                return;
            }
            this.toggleListening();
        });
        
        // Speak response button
        if (this.speakBtn) {
            this.speakBtn.addEventListener('click', () => this.speakResponse());
        }
        
        // Keyboard shortcut: Ctrl+Space
        document.addEventListener('keydown', (event) => {
            if (event.ctrlKey && event.key === ' ') {
                event.preventDefault();
                if (!this.isProcessing) {
                    this.toggleListening();
                }
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
        if (this.isListening || this.isProcessing) {
            console.log('[Voice] Already listening or processing');
            return;
        }
        
        console.log('[Voice] Starting recognition...');
        
        try {
            this.recognition.start();
        } catch (error) {
            console.error('[Voice] Start error:', error);
            if (error.name === 'InvalidStateError') {
                // Already running, stop and restart
                this.recognition.stop();
                setTimeout(() => this.recognition.start(), 100);
            } else {
                this.showError('Could not start voice recognition: ' + error.message);
            }
        }
    }
    
    stopListening() {
        if (!this.isListening) return;
        
        console.log('[Voice] Stopping recognition...');
        try {
            this.recognition.stop();
        } catch (error) {
            console.warn('[Voice] Stop error:', error);
        }
        this.isListening = false;
        this.updateUI('idle');
        this.updateStatus('Ready - Click microphone to speak', 'ready');
    }
    
    async processVoiceCommand(command) {
        if (!command || this.isProcessing) {
            console.log('[Voice] Skipping - empty or already processing');
            return;
        }
        
        console.log('[Voice] Processing command:', command);
        
        this.isProcessing = true;
        this.updateStatus('⏳ Processing your request...', 'processing');
        this.voiceBtn.disabled = true;
        
        // Add to history
        this.commandHistory.push({
            command: command,
            timestamp: new Date().toISOString()
        });
        
        try {
            const response = await fetch(this.options.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    command: command,
                    session_id: this.sessionId
                })
            });
            
            console.log('[Voice] Response status:', response.status);
            
            if (!response.ok) {
                throw new Error('Server error: ' + response.status);
            }
            
            const data = await response.json();
            console.log('[Voice] Response data:', data);
            
            if (data.status === 'success') {
                // Keep same session for continuity
                if (data.session_id) {
                    this.sessionId = data.session_id;
                }
                this.handleSuccessResponse(data);
            } else {
                this.showError(data.message || 'Error processing command');
            }
            
        } catch (error) {
            console.error('[Voice] Fetch error:', error);
            this.showError('Connection error. Please try again.');
        } finally {
            this.isProcessing = false;
            this.voiceBtn.disabled = false;
            this.updateStatus('Ready - Click microphone to speak', 'ready');
        }
    }
    
    handleSuccessResponse(data) {
        // Update chat display
        this.updateAssistantResponse(data.response);
        
        // Store for text-to-speech
        this.lastResponse = data.speak || data.response;
        if (this.speakBtn) {
            this.speakBtn.disabled = false;
        }
        
        // Handle specific actions (show trains, etc.)
        if (data.action && data.data) {
            this.handleAction(data.action, data.data);
        }
        
        // Auto-speak the response
        this.speakResponse();
    }
    
    handleAction(action, data) {
        console.log('[Voice] Action:', action, data);
        
        const container = this.actionResults;
        if (!container) return;
        
        switch (action) {
            case 'show_trains':
                this.displayTrainResults(data);
                break;
            case 'show_pnr':
                this.displayPNRStatus(data);
                break;
            case 'show_bookings':
                this.displayBookingHistory(data);
                break;
            case 'booking_complete':
                this.displayBookingConfirmation(data);
                break;
            default:
                console.log('[Voice] Unknown action:', action);
        }
    }
    
    displayTrainResults(data) {
        if (!this.actionResults || !data.trains) return;
        
        const trains = data.trains;
        let html = `
            <div class="alert alert-success">
                <h6><i class="fas fa-train me-2"></i>Found ${trains.length} trains: ${data.source} → ${data.destination}</h6>
            </div>
            <div class="row">
        `;
        
        trains.forEach((train, index) => {
            html += `
                <div class="col-md-6 mb-2">
                    <div class="card">
                        <div class="card-body p-2">
                            <div class="d-flex justify-content-between">
                                <div>
                                    <strong>${index + 1}. ${train.train_name || 'Train'}</strong><br>
                                    <small class="text-muted">${train.train_number || ''}</small>
                                </div>
                                <div class="text-end">
                                    <span class="badge bg-primary">${train.departure_time || train.departure || 'N/A'}</span><br>
                                    <small class="text-success fw-bold">₹${train.price_sleeper || train.price || 500}</small>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += `</div>
            <div class="alert alert-info mt-2">
                <strong>Say "Book 1", "Book 2", etc. to book a train</strong>
            </div>
        `;
        
        this.actionResults.innerHTML = html;
        this.actionResults.style.display = 'block';
    }
    
    displayPNRStatus(data) {
        if (!this.actionResults) return;
        
        this.actionResults.innerHTML = `
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <i class="fas fa-ticket-alt me-2"></i>PNR Status: ${data.pnr_number || data.pnr || 'N/A'}
                </div>
                <div class="card-body">
                    <p><strong>Passenger:</strong> ${data.passenger_name || 'N/A'}</p>
                    <p><strong>Train:</strong> ${data.train_name || 'N/A'}</p>
                    <p><strong>Status:</strong> <span class="badge bg-success">${data.booking_status || 'Confirmed'}</span></p>
                </div>
            </div>
        `;
        this.actionResults.style.display = 'block';
    }
    
    displayBookingHistory(data) {
        if (!this.actionResults) return;
        
        const bookings = data.bookings || [];
        let html = `<h6><i class="fas fa-history me-2"></i>Your Bookings (${bookings.length})</h6>`;
        
        if (bookings.length === 0) {
            html += '<p class="text-muted">No bookings found</p>';
        } else {
            bookings.slice(0, 5).forEach(b => {
                html += `<div class="card mb-2"><div class="card-body p-2">
                    <strong>PNR: ${b.pnr_number}</strong> - ${b.passenger_name || 'N/A'}
                    <span class="badge bg-success float-end">${b.booking_status || 'Confirmed'}</span>
                </div></div>`;
            });
        }
        
        this.actionResults.innerHTML = html;
        this.actionResults.style.display = 'block';
    }
    
    displayBookingConfirmation(data) {
        if (!this.actionResults) return;
        
        this.actionResults.innerHTML = `
            <div class="alert alert-success">
                <h5><i class="fas fa-check-circle me-2"></i>Booking Confirmed!</h5>
                <hr>
                <p><strong>PNR:</strong> <span class="fs-4">${data.pnr || 'N/A'}</span></p>
                <p><strong>Seat:</strong> ${data.seat_number || 'N/A'}</p>
                <p><strong>Amount:</strong> ₹${data.total_amount || 0}</p>
                <a href="/booking-history" class="btn btn-primary btn-sm">View Booking History</a>
            </div>
        `;
        this.actionResults.style.display = 'block';
    }
    
    speakResponse() {
        if (!this.lastResponse || !this.synthesis) return;
        
        // Cancel any ongoing speech
        this.synthesis.cancel();
        
        // Clean text for speech (remove markdown, emojis)
        let text = this.lastResponse
            .replace(/\*\*/g, '')
            .replace(/[🚂🎫✅❌💰📋🎉👤📍📅🪑📱]/g, '')
            .replace(/\n/g, ' ')
            .substring(0, 500);  // Limit length
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = this.options.language;
        utterance.rate = 0.9;
        utterance.pitch = 1.1;
        utterance.volume = 1.0;
        
        // Try to get a good voice
        const voices = this.synthesis.getVoices();
        const preferredVoice = voices.find(v => 
            v.lang.includes('en') && v.name.includes('Google')
        ) || voices.find(v => v.lang.includes('en'));
        
        if (preferredVoice) {
            utterance.voice = preferredVoice;
        }
        
        utterance.onstart = () => this.updateStatus('🔊 Speaking...', 'speaking');
        utterance.onend = () => this.updateStatus('Ready - Click microphone to speak', 'ready');
        utterance.onerror = (e) => console.error('[Voice] Speech error:', e);
        
        this.synthesis.speak(utterance);
    }
    
    updateUI(state) {
        if (!this.voiceBtn || !this.voiceIcon || !this.voiceText) return;
        
        switch (state) {
            case 'listening':
                this.voiceIcon.className = 'fas fa-stop-circle';
                this.voiceText.textContent = 'Stop';
                this.voiceBtn.className = 'btn btn-danger btn-lg me-3 pulse-animation';
                break;
            case 'processing':
                this.voiceIcon.className = 'fas fa-spinner fa-spin';
                this.voiceText.textContent = 'Processing...';
                this.voiceBtn.className = 'btn btn-warning btn-lg me-3';
                break;
            case 'idle':
            default:
                this.voiceIcon.className = 'fas fa-microphone';
                this.voiceText.textContent = 'Click to Speak';
                this.voiceBtn.className = 'btn btn-primary btn-lg me-3';
        }
    }
    
    updateStatus(text, type) {
        if (!this.voiceStatus) return;
        
        let badgeClass = 'bg-secondary';
        switch (type) {
            case 'listening': badgeClass = 'bg-danger'; break;
            case 'processing': badgeClass = 'bg-warning text-dark'; break;
            case 'speaking': badgeClass = 'bg-info'; break;
            case 'ready': badgeClass = 'bg-success'; break;
            case 'error': badgeClass = 'bg-danger'; break;
        }
        
        this.voiceStatus.innerHTML = `<span class="badge ${badgeClass}">${text}</span>`;
    }
    
    updateInterimResults(text) {
        if (this.interimResults) {
            this.interimResults.innerHTML = `<span class="text-primary fw-bold">${text}</span>`;
        }
    }
    
    updateFinalCommand(command) {
        if (this.finalCommand) {
            this.finalCommand.innerHTML = `<strong>You said:</strong> <span class="text-success">"${command}"</span>`;
        }
    }
    
    updateAssistantResponse(response) {
        if (this.assistantResponse) {
            // Convert markdown-style formatting to HTML
            let html = response
                .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>')
                .replace(/•/g, '&bull;');
            this.assistantResponse.innerHTML = html;
        }
    }
    
    showError(message) {
        console.error('[Voice] Error:', message);
        
        if (this.assistantResponse) {
            this.assistantResponse.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-triangle me-2"></i>${message}</div>`;
        }
        
        this.updateStatus('Error - Try again', 'error');
    }
    
    getCSRFToken() {
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
}

// Add CSS for pulse animation
const style = document.createElement('style');
style.textContent = `
    .pulse-animation {
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.7); }
        70% { box-shadow: 0 0 0 15px rgba(220, 53, 69, 0); }
        100% { box-shadow: 0 0 0 0 rgba(220, 53, 69, 0); }
    }
`;
document.head.appendChild(style);

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceInterface;
} else {
    window.VoiceInterface = VoiceInterface;
}