// Global JavaScript for Time Management App

// Application state
const app = {
    currentUser: null,
    accessToken: localStorage.getItem('access_token'),
    isClocked: false,
    currentLocation: null
};

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Always load status (session-based)
    loadCurrentStatus();
    requestLocationPermission();

    // Initialize real-time updates
    setInterval(updateCurrentTime, 1000);
    setInterval(loadCurrentStatus, 30000); // Update status every 30 seconds

    // Initialize event listeners
    setupEventListeners();
}

function setupEventListeners() {
    // Global error handling
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled promise rejection:', event.reason);
        showAlert('An unexpected error occurred. Please try again.', 'danger');
    });

    // Handle browser back/forward
    window.addEventListener('popstate', function(event) {
        if (event.state && event.state.page) {
            loadPage(event.state.page);
        }
    });
}

// Authentication functions
function getCurrentUser() {
    // Skip this for now as we don't have a current-user endpoint
    return;

    // Commented out for now:
    // fetch('/api/current-user')
    // .then(response => {
    //     if (!response.ok) {
    //         throw new Error('Failed to get user info');
    //     }
    //     return response.json();
    // })
    // .then(user => {
    //     app.currentUser = user;
    //     updateUserInterface();
    // })
    // .catch(error => {
    //     console.error('Error getting current user:', error);
    //     logout();
    // });
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_id');
    localStorage.removeItem('user_role');
    app.accessToken = null;
    app.currentUser = null;
    window.location.href = '/logout';
}

// Time and status functions
function updateCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleString();

    const currentTimeElements = document.querySelectorAll('#currentTime, #currentDateTime');
    currentTimeElements.forEach(element => {
        if (element) {
            element.textContent = timeString;
        }
    });
}

function loadCurrentStatus() {
    fetch('/api/current-status')
    .then(response => {
        if (response.ok) {
            return response.json();
        } else if (response.status === 302 || response.redirected) {
            // User not authenticated, redirect to login
            window.location.href = '/login';
            return null;
        } else {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
    })
    .then(data => {
        if (data) {
            updateClockStatus(data);
        }
    })
    .catch(error => {
        console.error('Error loading status:', error);
        // If authentication error, show default clocked out status
        updateClockStatus({ status: 'clocked_out' });
    });
}

function updateClockStatus(data) {
    const statusElement = document.getElementById('clockStatus');
    const statusBar = document.getElementById('statusBar');

    if (data.status === 'clocked_in') {
        app.isClocked = true;

        if (statusElement) {
            statusElement.textContent = 'Clocked In';
            statusElement.className = 'badge bg-success me-2';
        }

        if (statusBar) {
            statusBar.classList.remove('d-none');
        }

        // Update button states in modal
        updateTimeClockButtons(true);

        // Calculate elapsed time
        if (data.clock_in_time) {
            const clockInTime = new Date(data.clock_in_time);
            const now = new Date();
            const elapsed = Math.floor((now - clockInTime) / 1000 / 60);
            const hours = Math.floor(elapsed / 60);
            const minutes = elapsed % 60;

            const dailyHoursElement = document.getElementById('dailyHours');
            if (dailyHoursElement) {
                dailyHoursElement.textContent = `Daily Hours: ${hours}h ${minutes}m`;
            }
        }
    } else {
        app.isClocked = false;

        if (statusElement) {
            statusElement.textContent = 'Clocked Out';
            statusElement.className = 'badge bg-secondary me-2';
        }

        updateTimeClockButtons(false);
    }
}

function updateTimeClockButtons(isClockedIn) {
    const clockInBtn = document.getElementById('clockInBtn');
    const clockOutBtn = document.getElementById('clockOutBtn');
    const breakStartBtn = document.getElementById('breakStartBtn');
    const breakEndBtn = document.getElementById('breakEndBtn');

    if (clockInBtn && clockOutBtn) {
        clockInBtn.disabled = isClockedIn;
        clockOutBtn.disabled = !isClockedIn;
    }

    if (breakStartBtn && breakEndBtn) {
        breakStartBtn.disabled = !isClockedIn;
        breakEndBtn.disabled = true; // Will be enabled when break starts
    }
}

function updateUserInterface() {
    if (!app.currentUser) return;

    // Update user-specific UI elements
    const userNameElements = document.querySelectorAll('.user-name');
    userNameElements.forEach(element => {
        element.textContent = app.currentUser.first_name;
    });

    // Show/hide role-specific elements
    const adminElements = document.querySelectorAll('.admin-only');
    const managerElements = document.querySelectorAll('.manager-only');

    if (app.currentUser.role === 'admin') {
        adminElements.forEach(element => element.style.display = 'block');
        managerElements.forEach(element => element.style.display = 'block');
    } else if (app.currentUser.role === 'manager') {
        adminElements.forEach(element => element.style.display = 'none');
        managerElements.forEach(element => element.style.display = 'block');
    } else {
        adminElements.forEach(element => element.style.display = 'none');
        managerElements.forEach(element => element.style.display = 'none');
    }
}

// Location functions
function requestLocationPermission() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                app.currentLocation = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                };
                updateLocationStatus('Location detected');
            },
            function(error) {
                console.log('Location access denied or failed:', error.message);
                updateLocationStatus('Location not available');
            }
        );
    } else {
        updateLocationStatus('Geolocation not supported');
    }
}

function updateLocationStatus(message) {
    const locationStatusElement = document.getElementById('locationStatus');
    if (locationStatusElement) {
        locationStatusElement.textContent = message;
    }
}

// Utility functions
function showAlert(message, type = 'info', timeout = 5000) {
    const alertContainer = document.getElementById('alertContainer');
    if (!alertContainer) return;

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    alertContainer.appendChild(alert);

    // Auto-remove alert
    if (timeout > 0) {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, timeout);
    }

    return alert;
}

function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
}

function formatTime(dateString) {
    if (!dateString) return '--:--';
    const date = new Date(dateString);
    return date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

function formatDate(dateString) {
    if (!dateString) return '--';
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

// API helper functions
function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json'
        }
    };

    const requestOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

    return fetch(url, requestOptions)
        .then(response => {
            if (!response.ok) {
                if (response.status === 401) {
                    window.location.href = '/login';
                    throw new Error('Authentication failed');
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        });
}

// Export functions for global use
window.app = app;
window.showAlert = showAlert;
window.formatDuration = formatDuration;
window.formatTime = formatTime;
window.formatDate = formatDate;
window.apiRequest = apiRequest;
window.logout = logout;