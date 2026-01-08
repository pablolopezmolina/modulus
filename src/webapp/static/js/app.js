/**
 * MODULUS Consumer Web App - JavaScript
 * Version: 1.0
 * Description: Form validation, interactions, and utility functions
 */

(function() {
    'use strict';

    // ==========================================================================
    // ModulusApp Namespace
    // ==========================================================================
    
    window.ModulusApp = {
        // Configuration
        config: {
            minWeight: 30,
            maxWeight: 300,
            validTimeFormat: /^([01]?[0-9]|2[0-3]):([0-5][0-9])$/
        },

        // ==========================================================================
        // Form Validation
        // ==========================================================================
        
        /**
         * Initialize form validation for a given form
         * @param {string} formId - The ID of the form to validate
         */
        initFormValidation: function(formId) {
            const form = document.getElementById(formId);
            if (!form) {
                console.warn('Form not found:', formId);
                return;
            }

            // Add input listeners
            const weightInput = form.querySelector('input[name="weight_kg"]');
            const wakeTimeInput = form.querySelector('input[name="wake_time"]');
            const activityTimeInput = form.querySelector('input[name="activity_time"]');

            if (weightInput) {
                weightInput.addEventListener('input', () => this.validateWeight(weightInput));
                weightInput.addEventListener('blur', () => this.validateWeight(weightInput));
            }

            if (wakeTimeInput) {
                wakeTimeInput.addEventListener('change', () => this.validateTime(wakeTimeInput, 'wake-time'));
            }

            if (activityTimeInput) {
                activityTimeInput.addEventListener('change', () => this.validateTime(activityTimeInput, 'activity-time'));
            }

            // Form submit handler
            form.addEventListener('submit', (e) => this.handleFormSubmit(e, form));
        },

        /**
         * Validate weight input
         * @param {HTMLInputElement} input - The weight input element
         * @returns {boolean} - Whether the input is valid
         */
        validateWeight: function(input) {
            const value = parseFloat(input.value);
            const errorEl = document.getElementById('weight-error');
            let isValid = true;
            let errorMsg = '';

            if (isNaN(value) || value === '') {
                isValid = false;
                errorMsg = 'Please enter your weight';
            } else if (value < this.config.minWeight) {
                isValid = false;
                errorMsg = `Weight must be at least ${this.config.minWeight} kg`;
            } else if (value > this.config.maxWeight) {
                isValid = false;
                errorMsg = `Weight must be less than ${this.config.maxWeight} kg`;
            }

            this.setFieldState(input, errorEl, isValid, errorMsg);
            return isValid;
        },

        /**
         * Validate time input
         * @param {HTMLInputElement} input - The time input element
         * @param {string} fieldId - The field ID prefix for error element
         * @returns {boolean} - Whether the input is valid
         */
        validateTime: function(input, fieldId) {
            const value = input.value;
            const errorEl = document.getElementById(`${fieldId}-error`);
            let isValid = true;
            let errorMsg = '';

            if (!value) {
                isValid = false;
                errorMsg = 'Please select a time';
            } else if (!this.config.validTimeFormat.test(value)) {
                isValid = false;
                errorMsg = 'Invalid time format';
            }

            this.setFieldState(input, errorEl, isValid, errorMsg);
            return isValid;
        },

        /**
         * Set the validation state of a field
         * @param {HTMLInputElement} input - The input element
         * @param {HTMLElement} errorEl - The error message element
         * @param {boolean} isValid - Whether the field is valid
         * @param {string} errorMsg - The error message to display
         */
        setFieldState: function(input, errorEl, isValid, errorMsg) {
            if (isValid) {
                input.classList.remove('error');
                if (errorEl) errorEl.textContent = '';
            } else {
                input.classList.add('error');
                if (errorEl) errorEl.textContent = errorMsg;
            }
        },

        /**
         * Handle form submission
         * @param {Event} e - The submit event
         * @param {HTMLFormElement} form - The form element
         */
        handleFormSubmit: function(e, form) {
            const weightInput = form.querySelector('input[name="weight_kg"]');
            const wakeTimeInput = form.querySelector('input[name="wake_time"]');
            const activityTimeInput = form.querySelector('input[name="activity_time"]');

            let isValid = true;

            if (weightInput && !this.validateWeight(weightInput)) {
                isValid = false;
            }

            if (wakeTimeInput && !this.validateTime(wakeTimeInput, 'wake-time')) {
                isValid = false;
            }

            if (activityTimeInput && !this.validateTime(activityTimeInput, 'activity-time')) {
                isValid = false;
            }

            if (!isValid) {
                e.preventDefault();
                // Scroll to first error
                const firstError = form.querySelector('.error');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    firstError.focus();
                }
                return;
            }

            // Show loading state
            this.setLoadingState(form, true);
        },

        /**
         * Set the loading state of the form
         * @param {HTMLFormElement} form - The form element
         * @param {boolean} isLoading - Whether to show loading state
         */
        setLoadingState: function(form, isLoading) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (!submitBtn) return;

            const btnText = submitBtn.querySelector('.btn-text');
            const btnIcon = submitBtn.querySelector('.btn-icon');
            const btnLoading = submitBtn.querySelector('.btn-loading');

            if (isLoading) {
                submitBtn.disabled = true;
                if (btnText) btnText.style.display = 'none';
                if (btnIcon) btnIcon.style.display = 'none';
                if (btnLoading) btnLoading.style.display = 'inline-flex';
            } else {
                submitBtn.disabled = false;
                if (btnText) btnText.style.display = '';
                if (btnIcon) btnIcon.style.display = '';
                if (btnLoading) btnLoading.style.display = 'none';
            }
        },

        // ==========================================================================
        // Results Page Functions
        // ==========================================================================

        /**
         * Share the personalization results
         */
        shareResults: function() {
            const results = window.personalizationResults;
            if (!results) {
                console.warn('No results to share');
                return;
            }

            const shareText = `My personalized protocol for ${results.product}:\n` +
                `⏰ Optimal timing: ${results.timing}\n` +
                `📊 Dose: ${results.dosage}x serving\n\n` +
                `Get your personalized recommendation at ${window.location.origin}`;

            // Try native share API first
            if (navigator.share) {
                navigator.share({
                    title: 'My Personalized Protocol',
                    text: shareText,
                    url: window.location.href
                }).catch(err => {
                    // Fallback to clipboard if share was cancelled
                    if (err.name !== 'AbortError') {
                        this.copyToClipboard(shareText);
                    }
                });
            } else {
                // Fallback to clipboard
                this.copyToClipboard(shareText);
            }
        },

        /**
         * Copy text to clipboard and show feedback
         * @param {string} text - The text to copy
         */
        copyToClipboard: function(text) {
            navigator.clipboard.writeText(text)
                .then(() => {
                    this.showToast('Results copied to clipboard!', 'success');
                })
                .catch(err => {
                    console.error('Failed to copy:', err);
                    this.showToast('Failed to copy results', 'error');
                });
        },

        // ==========================================================================
        // UI Helpers
        // ==========================================================================

        /**
         * Show a toast notification
         * @param {string} message - The message to display
         * @param {string} type - The type of toast ('success', 'error', 'info')
         */
        showToast: function(message, type = 'info') {
            // Remove existing toast
            const existingToast = document.querySelector('.toast');
            if (existingToast) {
                existingToast.remove();
            }

            // Create toast element
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.innerHTML = `
                <span class="toast-icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
                <span class="toast-message">${message}</span>
            `;

            // Add styles
            Object.assign(toast.style, {
                position: 'fixed',
                bottom: '24px',
                left: '50%',
                transform: 'translateX(-50%) translateY(100px)',
                padding: '12px 24px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '14px',
                fontWeight: '500',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                zIndex: '9999',
                transition: 'transform 0.3s ease-out',
                background: type === 'success' ? '#10B981' : type === 'error' ? '#EF4444' : '#3B82F6',
                color: 'white'
            });

            document.body.appendChild(toast);

            // Animate in
            requestAnimationFrame(() => {
                toast.style.transform = 'translateX(-50%) translateY(0)';
            });

            // Remove after delay
            setTimeout(() => {
                toast.style.transform = 'translateX(-50%) translateY(100px)';
                setTimeout(() => toast.remove(), 300);
            }, 3000);
        },

        // ==========================================================================
        // Time Utilities
        // ==========================================================================

        /**
         * Parse a time string to minutes from midnight
         * @param {string} timeStr - Time string in HH:MM format
         * @returns {number} - Minutes from midnight
         */
        parseTimeToMinutes: function(timeStr) {
            const [hours, minutes] = timeStr.split(':').map(Number);
            return hours * 60 + minutes;
        },

        /**
         * Format minutes from midnight to HH:MM
         * @param {number} minutes - Minutes from midnight
         * @returns {string} - Formatted time string
         */
        formatMinutesToTime: function(minutes) {
            const hours = Math.floor(minutes / 60) % 24;
            const mins = minutes % 60;
            return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
        },

        // ==========================================================================
        // Analytics (placeholder)
        // ==========================================================================

        /**
         * Track an event (placeholder for analytics integration)
         * @param {string} eventName - The name of the event
         * @param {Object} eventData - Additional event data
         */
        trackEvent: function(eventName, eventData = {}) {
            console.debug('[Analytics]', eventName, eventData);
            // Integrate with actual analytics service here
            // e.g., gtag('event', eventName, eventData);
        }
    };

    // ==========================================================================
    // Document Ready
    // ==========================================================================
    
    document.addEventListener('DOMContentLoaded', function() {
        // Track page view
        ModulusApp.trackEvent('page_view', {
            page: window.location.pathname
        });

        // Add smooth scroll behavior for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });

        // Handle sensitivity card keyboard navigation
        const sensitivityCards = document.querySelectorAll('.sensitivity-option');
        sensitivityCards.forEach(card => {
            card.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    const radio = this.querySelector('input[type="radio"]');
                    if (radio) {
                        radio.checked = true;
                        radio.dispatchEvent(new Event('change'));
                    }
                }
            });
        });

        // Initialize any animations on scroll
        if ('IntersectionObserver' in window) {
            const animatedElements = document.querySelectorAll('.animate-on-scroll');
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('animated');
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.1 });

            animatedElements.forEach(el => observer.observe(el));
        }
    });

    // ==========================================================================
    // Service Worker Registration (for PWA support)
    // ==========================================================================
    
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function() {
            // Service worker can be added later for offline support
            // navigator.serviceWorker.register('/sw.js');
        });
    }

})();
