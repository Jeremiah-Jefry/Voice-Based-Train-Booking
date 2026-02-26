/**
 * Voice Interface for Train Booking Platform
 * Integrates Web Speech API for voice commands and text-to-speech
 */

class VoiceInterface {
    constructor(options = {}) {
        this.options = {
            apiEndpoint: '/voice/process-command',
            language: 'en-IN',
            continuous: true,
            interimResults: true,
            ...options
        };
        
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.isListening = false;
        this.isProcessing = false;
        this.shouldKeepListening = false;
        this.restartAttempts = 0;
        this.maxRestartAttempts = 3;
        this.sessionId = null;
        
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
    }
    
    initialize() {
        console.log('Initializing Voice Interface...');
        
        // Check browser support
        if (!this.checkBrowserSupport()) {
            this.showError('Your browser does not support voice recognition. Please use Chrome, Edge, or Safari.');
            return;
        }
        
        // Initialize DOM elements
        this.initializeDOMElements();
        
        // Setup speech recognition
        this.setupSpeechRecognition();
        
        // Setup event listeners
        this.setupEventListeners();
        
        console.log('Voice Interface initialized successfully');
    }
    
    checkBrowserSupport() {
        return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
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
            console.error('Required DOM elements not found');
            return false;
        }
        
        return true;
    }
    
    setupSpeechRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        // Configure recognition
        this.recognition.continuous = this.options.continuous;
        this.recognition.interimResults = this.options.interimResults;
        this.recognition.lang = this.options.language;
        this.recognition.maxAlternatives = 1;
        
        // Event handlers
        this.recognition.onstart = () => this.onRecognitionStart();
        this.recognition.onresult = (event) => this.onRecognitionResult(event);
        this.recognition.onerror = (event) => this.onRecognitionError(event);
        this.recognition.onend = () => this.onRecognitionEnd();
    }
    
    setupEventListeners() {
        // Voice button
        this.voiceBtn.addEventListener('click', () => this.toggleListening());
        
        // Speak response button
        this.speakBtn.addEventListener('click', () => this.speakResponse());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            if (event.ctrlKey && event.key === ' ') {
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
        if (this.isListening) return;
        
        console.log('Starting voice recognition...');
        this.shouldKeepListening = true;
        this.restartAttempts = 0;
        
        try {
            this.recognition.start();
            this.isListening = true;
            this.updateUI('listening');
            this.updateStatus('Listening...', 'listening');
        } catch (error) {
            console.error('Error starting recognition:', error);
            // If already started, just mark as listening
            if (error.message && error.message.includes('already started')) {
                this.isListening = true;
                this.updateUI('listening');
                this.updateStatus('Listening...', 'listening');
            } else {
                this.showError('Failed to start voice recognition: ' + error.message);
                this.shouldKeepListening = false;
            }
        }
    }
    
    stopListening() {
        if (!this.isListening && !this.shouldKeepListening) return;
        
        console.log('Stopping voice recognition...');
        this.shouldKeepListening = false;
        
        try {
            this.recognition.stop();
        } catch (error) {
            console.warn('Error stopping recognition:', error);
        }
        
        this.isListening = false;
        this.updateUI('idle');
        this.updateStatus('Ready', 'ready');
    }
    
    onRecognitionStart() {
        console.log('Recognition started');
        this.updateStatus('Listening...', 'listening');
    }
    
    onRecognitionResult(event) {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }
        
        // Update interim results
        if (interimTranscript) {
            this.updateInterimResults(interimTranscript);
        }
        
        // Process final command
        if (finalTranscript) {
            console.log('Final transcript:', finalTranscript);
            this.updateFinalCommand(finalTranscript);
            this.processVoiceCommand(finalTranscript.trim());
        }
    }
    
    onRecognitionError(event) {
        console.error('Recognition error:', event.error);
        
        // Handle errors that should auto-restart
        if (event.error === 'no-speech' || event.error === 'aborted') {
            // Don't show error for no-speech or aborted - just restart
            if (this.shouldKeepListening) {
                console.log('Auto-restarting after', event.error);
                this.isListening = false;
                return; // Let onend handle restart
            }
        }
        
        let errorMessage = 'Voice recognition error: ';
        switch (event.error) {
            case 'audio-capture':
                errorMessage += 'Microphone access denied or not available.';
                this.shouldKeepListening = false;
                break;
            case 'network':
                errorMessage += 'Network error. Please check your connection.';
                break;
            case 'not-allowed':
                errorMessage += 'Microphone permission denied. Please allow microphone access.';
                this.shouldKeepListening = false;
                break;
            default:
                errorMessage += event.error;
        }
        
        if (event.error !== 'no-speech' && event.error !== 'aborted') {
            this.showError(errorMessage);
        }
        
        if (!this.shouldKeepListening) {
            this.stopListening();
        }
    }
    
    onRecognitionEnd() {
        console.log('Recognition ended, shouldKeepListening:', this.shouldKeepListening);
        this.isListening = false;
        
        // Auto-restart if user wants to keep listening
        if (this.shouldKeepListening && this.restartAttempts < this.maxRestartAttempts) {
            this.restartAttempts++;
            console.log('Auto-restarting recognition (attempt', this.restartAttempts, ')');
            
            // Brief delay before restart to avoid rapid fire restarts
            setTimeout(() => {
                if (this.shouldKeepListening && !this.isListening) {
                    try {
                        this.recognition.start();
                        this.isListening = true;
                        this.restartAttempts = 0; // Reset on successful start
                        this.updateUI('listening');
                        this.updateStatus('Listening...', 'listening');
                    } catch (error) {
                        console.error('Failed to restart recognition:', error);
                        if (this.restartAttempts >= this.maxRestartAttempts) {
                            this.showError('Voice recognition stopped. Click microphone to restart.');
                            this.shouldKeepListening = false;
                            this.updateUI('idle');
                            this.updateStatus('Ready', 'ready');
                        }
                    }
                }
            }, 300);
        } else {
            this.updateUI('idle');
            if (!this.shouldKeepListening) {
                this.updateStatus('Ready', 'ready');
            }
        }
    }
    
    async processVoiceCommand(command) {
        if (!command || this.isProcessing) return;
        
        this.isProcessing = true;
        this.updateStatus('Processing...', 'processing');
        this.voiceBtn.disabled = true;
        
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
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('Voice command response:', data);
            
            if (data.status === 'success') {
                this.sessionId = data.session_id;
                this.handleSuccessResponse(data);
            } else {
                this.showError(data.message || 'Unknown error occurred');
            }
            
        } catch (error) {
            console.error('Error processing voice command:', error);
            this.showError('Failed to process voice command: ' + error.message);
        } finally {
            this.isProcessing = false;
            // Only set to Ready if not actively listening
            if (!this.shouldKeepListening) {
                this.updateStatus('Ready', 'ready');
            } else {
                this.updateStatus('Listening...', 'listening');
            }
            this.voiceBtn.disabled = false;
        }
    }
    
    handleSuccessResponse(data) {
        // Update assistant response
        this.updateAssistantResponse(data.response);
        
        // Store for speaking
        this.lastResponse = data.speak || data.response;
        this.speakBtn.disabled = false;
        
        // Handle specific actions
        if (data.action) {
            this.handleAction(data.action, data.data);
        }
        
        // Auto-speak response if enabled
        if (this.shouldAutoSpeak()) {
            this.speakResponse();
        }
    }
    
    handleAction(action, data) {
        console.log('Handling action:', action, data);
        
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
            default:
                console.log('Unknown action:', action);
        }
    }
    
    displayTrainResults(data) {
        const container = this.actionResults;
        container.innerHTML = `
            <div class="train-results">
                <h6 class="text-primary mb-3">
                    <i class="fas fa-train me-2"></i>
                    Trains from ${data.source} to ${data.destination}
                </h6>
                <div class="row">
                    ${data.trains.map(train => `
                        <div class="col-md-6 mb-2">
                            <div class="card border-light">
                                <div class="card-body py-2">
                                    <div class="d-flex justify-content-between align-items-center">
                                        <div>
                                            <strong>${train.train_name}</strong><br>
                                            <small class="text-muted">${train.train_number}</small>
                                        </div>
                                        <div class="text-end">
                                            <div class="fw-bold">${train.departure}</div>
                                            <div class="text-success">₹${train.price}</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        container.style.display = 'block';
    }
    
    displayPNRStatus(data) {
        const container = this.actionResults;
        container.innerHTML = `
            <div class="pnr-status">
                <h6 class="text-primary mb-3">
                    <i class="fas fa-ticket-alt me-2"></i>
                    PNR Status
                </h6>
                <div class="card border-light">
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-4">
                                <strong>PNR Number:</strong><br>
                                <span class="h5 text-primary">${data.pnr}</span>
                            </div>
                            <div class="col-md-4">
                                <strong>Status:</strong><br>
                                <span class="badge bg-${data.status === 'confirmed' ? 'success' : 'warning'}">${data.status.toUpperCase()}</span>
                            </div>
                            <div class="col-md-4">
                                <strong>Train:</strong><br>
                                ${data.train}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        container.style.display = 'block';
    }
    
    displayBookingHistory(data) {
        const container = this.actionResults;
        container.innerHTML = `
            <div class="booking-history">
                <h6 class="text-primary mb-3">
                    <i class="fas fa-history me-2"></i>
                    Recent Bookings
                </h6>
                <div class="text-center">
                    <p class="text-muted">Booking history will be displayed here</p>
                    <a href="/booking-history" class="btn btn-outline-primary btn-sm">View All Bookings</a>
                </div>
            </div>
        `;
        container.style.display = 'block';
    }
    
    speakResponse() {
        if (!this.lastResponse || !this.synthesis) return;
        
        // Cancel any ongoing speech
        this.synthesis.cancel();
        
        const utterance = new SpeechSynthesisUtterance(this.lastResponse);
        utterance.lang = this.options.language;
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
        
        utterance.onstart = () => {
            this.updateStatus('Speaking...', 'speaking');
        };
        
        utterance.onend = () => {
            this.updateStatus('Ready', 'ready');
        };
        
        this.synthesis.speak(utterance);
    }
    
    updateUI(state) {
        switch (state) {
            case 'listening':
                this.voiceIcon.className = 'fas fa-microphone-slash text-white';
                this.voiceText.textContent = 'Stop Listening';
                this.voiceBtn.className = 'btn btn-danger btn-lg me-3';
                break;
            case 'processing':
                this.voiceIcon.className = 'fas fa-spinner fa-spin';
                this.voiceText.textContent = 'Processing...';
                this.voiceBtn.className = 'btn btn-warning btn-lg me-3';
                break;
            case 'idle':
            default:
                this.voiceIcon.className = 'fas fa-microphone';
                this.voiceText.textContent = 'Start Listening';
                this.voiceBtn.className = 'btn btn-primary btn-lg me-3';
        }
    }
    
    updateStatus(text, type) {
        if (!this.voiceStatus) return;
        
        let badgeClass = 'bg-secondary';
        switch (type) {
            case 'listening': badgeClass = 'bg-danger'; break;
            case 'processing': badgeClass = 'bg-warning'; break;
            case 'speaking': badgeClass = 'bg-info'; break;
            case 'ready': badgeClass = 'bg-success'; break;
        }
        
        this.voiceStatus.innerHTML = `<span class="badge ${badgeClass}">${text}</span>`;
    }
    
    updateInterimResults(text) {
        if (this.interimResults) {
            this.interimResults.innerHTML = `<em class="text-primary">${text}</em>`;
        }
    }
    
    updateFinalCommand(command) {
        if (this.finalCommand) {
            this.finalCommand.innerHTML = `<strong>Last Command:</strong> <span class="text-primary">${command}</span>`;
        }
    }
    
    updateAssistantResponse(response) {
        if (this.assistantResponse) {
            this.assistantResponse.innerHTML = response.replace(/\\n/g, '<br>');
        }
    }
    
    showError(message) {
        console.error('Voice Interface Error:', message);
        
        if (this.assistantResponse) {
            this.assistantResponse.innerHTML = `<div class="alert alert-danger">${message}</div>`;
        }
        
        this.updateStatus('Error', 'error');
    }
    
    shouldAutoSpeak() {
        // Check user preferences for auto-speak
        return false; // Disabled by default
    }
    
    getCSRFToken() {
        // Get CSRF token from meta tag or cookie
        const token = document.querySelector('meta[name="csrf-token"]');
        return token ? token.getAttribute('content') : '';
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoiceInterface;
} else {
    window.VoiceInterface = VoiceInterface;
}