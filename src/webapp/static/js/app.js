/**
 * MODULUS Consumer Web App - JavaScript
 * 
 * Session 15.1 - FASE 5: Pack 3
 */

(function() {
    'use strict';

    // ==========================================================================
    // Form Validation & Enhancement
    // ==========================================================================

    /**
     * Initialize form enhancements
     */
    function initForm() {
        const form = document.querySelector('.personalize-form');
        if (!form) return;

        // Weight input formatting
        const weightInput = document.getElementById('weight_kg');
        if (weightInput) {
            weightInput.addEventListener('blur', function() {
                if (this.value) {
                    const value = parseFloat(this.value);
                    if (value >= 30 && value <= 250) {
                        this.value = value.toFixed(1);
                    }
                }
            });
        }

        // Form submission with loading state
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('.submit-btn');
            if (submitBtn) {
                submitBtn.classList.add('loading');
                submitBtn.innerHTML = 'Calculating... <span class="btn-arrow">⏳</span>';
            }
        });

        // Time validation helper
        const activityTime = document.getElementById('activity_time');
        const wakeTime = document.getElementById('wake_time');
        
        if (activityTime && wakeTime) {
            activityTime.addEventListener('change', validateTimes);
            wakeTime.addEventListener('change', validateTimes);
        }
    }

    /**
     * Validate that times make sense
     */
    function validateTimes() {
        const wakeTime = document.getElementById('wake_time');
        const activityTime = document.getElementById('activity_time');
        
        if (!wakeTime || !activityTime) return;
        
        // Convert to minutes for comparison
        const wakeMinutes = timeToMinutes(wakeTime.value);
        const activityMinutes = timeToMinutes(activityTime.value);
        
        // If activity is before wake (assuming same day), show info
        if (activityMinutes < wakeMinutes) {
            console.info('Activity time is before wake time - handling overnight scenario');
        }
    }

    /**
     * Convert HH:MM to minutes
     */
    function timeToMinutes(timeStr) {
        const [hours, minutes] = timeStr.split(':').map(Number);
        return hours * 60 + minutes;
    }

    // ==========================================================================
    // Results Enhancement
    // ==========================================================================

    /**
     * Initialize results page enhancements
     */
    function initResults() {
        const resultMain = document.querySelector('.result-main');
        if (!resultMain) return;

        // Add share functionality if Web Share API available
        if (navigator.share) {
            addShareButton();
        }

        // Save to localStorage for reference
        saveResultToStorage();
    }

    /**
     * Add share button
     */
    function addShareButton() {
        const actionsSection = document.querySelector('.actions-section');
        if (!actionsSection) return;

        const shareBtn = document.createElement('button');
        shareBtn.className = 'action-btn secondary';
        shareBtn.innerHTML = '📤 Share';
        shareBtn.addEventListener('click', shareResults);
        
        actionsSection.appendChild(shareBtn);
    }

    /**
     * Share results using Web Share API
     */
    async function shareResults() {
        const timing = document.querySelector('.timing-value')?.textContent;
        const productName = document.querySelector('.product-name')?.textContent;
        
        try {
            await navigator.share({
                title: 'My Personalized Supplement Timing',
                text: `Best time to take ${productName}: ${timing}`,
                url: window.location.href
            });
        } catch (err) {
            console.log('Share cancelled or failed:', err);
        }
    }

    /**
     * Save result to localStorage
     */
    function saveResultToStorage() {
        const timing = document.querySelector('.timing-value')?.textContent;
        const productName = document.querySelector('.product-name')?.textContent;
        
        if (timing && productName && window.localStorage) {
            const result = {
                product: productName,
                timing: timing,
                timestamp: new Date().toISOString(),
                url: window.location.href
            };
            
            localStorage.setItem('lastResult', JSON.stringify(result));
            
            // Also save to history array
            const history = JSON.parse(localStorage.getItem('resultHistory') || '[]');
            history.unshift(result);
            // Keep only last 10 results
            if (history.length > 10) history.pop();
            localStorage.setItem('resultHistory', JSON.stringify(history));
        }
    }

    // ==========================================================================
    // UI Helpers
    // ==========================================================================

    /**
     * Show toast notification
     */
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        Object.assign(toast.style, {
            position: 'fixed',
            bottom: '20px',
            left: '50%',
            transform: 'translateX(-50%)',
            padding: '12px 24px',
            borderRadius: '8px',
            backgroundColor: type === 'error' ? '#EF4444' : '#6366F1',
            color: 'white',
            fontWeight: '500',
            zIndex: '1000',
            animation: 'fadeIn 0.3s ease'
        });
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    /**
     * Format time for display
     */
    function formatTime(timeStr) {
        const [hours, minutes] = timeStr.split(':');
        const hour = parseInt(hours);
        const ampm = hour >= 12 ? 'PM' : 'AM';
        const displayHour = hour % 12 || 12;
        return `${displayHour}:${minutes} ${ampm}`;
    }

    // ==========================================================================
    // Analytics (placeholder)
    // ==========================================================================

    /**
     * Track event (placeholder for analytics integration)
     */
    function trackEvent(eventName, eventData = {}) {
        console.log('Track:', eventName, eventData);
        
        // Placeholder for actual analytics
        // Example: gtag('event', eventName, eventData);
        // Example: mixpanel.track(eventName, eventData);
    }

    // ==========================================================================
    // Initialize
    // ==========================================================================

    document.addEventListener('DOMContentLoaded', function() {
        initForm();
        initResults();
        
        // Track page view
        trackEvent('page_view', {
            page: window.location.pathname
        });
    });

    // Export for potential external use
    window.ModulusApp = {
        showToast,
        formatTime,
        trackEvent
    };

})();
