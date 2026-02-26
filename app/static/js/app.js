/**
 * Main Application JavaScript
 * Voice Train Booking Platform
 */

// Global app configuration
const APP_CONFIG = {
    name: 'Voice Train Booking',
    version: '1.0.0',
    environment: 'development'
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log(`Initializing ${APP_CONFIG.name} v${APP_CONFIG.version}`);
    
    // Initialize common features
    initializeTooltips();
    initializeAlerts();
    initializeFormValidation();
    initializeNavigation();
    
    console.log('App initialization completed');
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize alert auto-dismiss
 */
function initializeAlerts() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        if (!alert.querySelector('.btn-close')) {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        }
    });
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    // Add Bootstrap validation classes
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Real-time validation for important fields
    const emailInputs = document.querySelectorAll('input[type="email"]');
    emailInputs.forEach(input => {
        input.addEventListener('blur', validateEmail);
    });
    
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(input => {
        input.addEventListener('input', validatePassword);
    });
}

/**
 * Initialize navigation enhancements
 */
function initializeNavigation() {
    // Highlight current page in navigation
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
    
    // Add loading states to navigation links
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (this.getAttribute('href') !== '#') {
                this.classList.add('loading');
            }
        });
    });
}

/**
 * Email validation
 */
function validateEmail(event) {
    const email = event.target.value;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (email && !emailRegex.test(email)) {
        event.target.setCustomValidity('Please enter a valid email address');
    } else {
        event.target.setCustomValidity('');
    }
}

/**
 * Password validation
 */
function validatePassword(event) {
    const password = event.target.value;
    const minLength = 8;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    
    let message = '';
    if (password.length < minLength) {
        message = `Password must be at least ${minLength} characters long`;
    } else if (!hasUpperCase || !hasLowerCase) {
        message = 'Password must contain both uppercase and lowercase letters';
    } else if (!hasNumbers) {
        message = 'Password must contain at least one number';
    }
    
    event.target.setCustomValidity(message);
    
    // Update password strength indicator if exists
    const strengthIndicator = document.getElementById('password-strength');
    if (strengthIndicator) {
        updatePasswordStrength(password, strengthIndicator);
    }
}

/**
 * Update password strength indicator
 */
function updatePasswordStrength(password, indicator) {
    let strength = 0;
    let label = 'Weak';
    let colorClass = 'bg-danger';
    
    if (password.length >= 8) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength++;
    
    switch (strength) {
        case 0:
        case 1:
            label = 'Very Weak';
            colorClass = 'bg-danger';
            break;
        case 2:
            label = 'Weak';
            colorClass = 'bg-warning';
            break;
        case 3:
            label = 'Fair';
            colorClass = 'bg-info';
            break;
        case 4:
            label = 'Good';
            colorClass = 'bg-primary';
            break;
        case 5:
            label = 'Strong';
            colorClass = 'bg-success';
            break;
    }
    
    indicator.innerHTML = `
        <div class="progress" style="height: 5px;">
            <div class="progress-bar ${colorClass}" style="width: ${(strength / 5) * 100}%"></div>
        </div>
        <small class="text-muted">${label}</small>
    `;
}

/**
 * Utility function to show loading state
 */
function showLoading(element, message = 'Loading...') {
    element.disabled = true;
    element.innerHTML = `
        <span class="spinner-border spinner-border-sm me-2" role="status"></span>
        ${message}
    `;
}

/**
 * Utility function to hide loading state
 */
function hideLoading(element, originalText) {
    element.disabled = false;
    element.innerHTML = originalText;
}

/**
 * Show notification
 */
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after duration
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(notification);
        bsAlert.close();
    }, duration);
}

/**
 * Format Indian Railway time
 */
function formatTime(timeString) {
    const time = new Date(`1970-01-01T${timeString}`);
    return time.toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });
}

/**
 * Format Indian currency
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(amount);
}

/**
 * CSRF Token helper
 */
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

/**
 * API request helper with error handling
 */
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    };
    
    const config = { ...defaultOptions, ...options };
    
    try {
        const response = await fetch(url, config);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        showNotification(`Request failed: ${error.message}`, 'danger');
        throw error;
    }
}

// Export utilities for other modules
window.AppUtils = {
    showLoading,
    hideLoading,
    showNotification,
    formatTime,
    formatCurrency,
    getCSRFToken,
    apiRequest
};