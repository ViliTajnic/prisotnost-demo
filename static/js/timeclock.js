// Time Clock functionality

let breakStartTime = null;
let isOnBreak = false;

function toggleTimeClock() {
    const modal = new bootstrap.Modal(document.getElementById('timeClockModal'));

    // Load projects for dropdown
    loadProjects();

    // Update current time in modal
    updateModalTime();

    modal.show();
}

function updateModalTime() {
    const currentDateTimeElement = document.getElementById('currentDateTime');
    if (currentDateTimeElement) {
        const now = new Date();
        const options = {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        currentDateTimeElement.textContent = now.toLocaleDateString('en-US', options);
    }
}

function loadProjects() {
    fetch('/api/projects')
    .then(response => response.json())
    .then(projects => {
        const projectSelect = document.getElementById('projectSelect');
        if (projectSelect) {
            projectSelect.innerHTML = '<option value="">Select Project (Optional)</option>';
            projects.forEach(project => {
                const option = document.createElement('option');
                option.value = project.id;
                option.textContent = `${project.name} (${project.project_code})`;
                projectSelect.appendChild(option);
            });
        }
    })
    .catch(error => {
        console.error('Error loading projects:', error);
    });
}

function clockIn() {
    const projectId = document.getElementById('projectSelect').value;
    const notes = document.getElementById('clockNotes').value;
    const button = document.getElementById('clockInBtn');

    // Show loading state
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Clocking In...';
    button.disabled = true;

    const clockInData = {
        project_id: projectId || null,
        notes: notes,
        latitude: (window.app && window.app.currentLocation) ? window.app.currentLocation.latitude : null,
        longitude: (window.app && window.app.currentLocation) ? window.app.currentLocation.longitude : null
    };

    fetch('/api/clock-in', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(clockInData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            });
        }
        return response.json();
    })
    .then(data => {
        showAlert('Successfully clocked in!', 'success');

        // Update UI
        if (window.app) window.app.isClocked = true;
        updateTimeClockButtons(true);
        loadCurrentStatus();

        // Clear form
        document.getElementById('clockNotes').value = '';

        // Close modal after short delay
        setTimeout(() => {
            const modal = bootstrap.Modal.getInstance(document.getElementById('timeClockModal'));
            modal.hide();
        }, 1500);

        // Log activity
        logActivity('Clock In', data.clock_in_time);
    })
    .catch(error => {
        console.error('Clock in error:', error);

        // If already clocked in, refresh status to sync UI
        if (error.message && error.message.includes('Already clocked in')) {
            showAlert(error.message, 'warning');
            loadCurrentStatus(); // Refresh to sync UI with actual status
        } else {
            showAlert('Failed to clock in. Please try again.', 'danger');
        }
    })
    .finally(() => {
        // Reset button
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

function clockOut() {
    console.log('clockOut() function called');

    const notesElement = document.getElementById('clockNotes');
    const notes = notesElement ? notesElement.value : '';
    const button = document.getElementById('clockOutBtn');

    if (!button) {
        console.error('Clock out button not found');
        return;
    }

    // Calculate break duration if on break
    let breakDuration = 0;
    if (isOnBreak && breakStartTime) {
        const now = new Date();
        breakDuration = (now - breakStartTime) / 1000 / 3600; // Convert to hours
        isOnBreak = false;
        breakStartTime = null;
    }

    // Show loading state
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Clocking Out...';
    button.disabled = true;

    const clockOutData = {
        notes: notes,
        break_duration: breakDuration
    };

    fetch('/api/clock-out', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(clockOutData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            });
        }
        return response.json();
    })
    .then(data => {
        const overtimeMessage = data.is_overtime ? ' (Overtime detected)' : '';
        showAlert(`Successfully clocked out! Total hours: ${data.total_hours.toFixed(2)}${overtimeMessage}`, 'success');

        // Update UI
        if (window.app) window.app.isClocked = false;
        updateTimeClockButtons(false);
        loadCurrentStatus();

        // Clear form
        document.getElementById('clockNotes').value = '';

        // Close modal after short delay
        setTimeout(() => {
            const modal = bootstrap.Modal.getInstance(document.getElementById('timeClockModal'));
            modal.hide();
        }, 1500);

        // Log activity
        logActivity('Clock Out', new Date().toISOString(), data.total_hours);
    })
    .catch(error => {
        console.error('Clock out error:', error);

        // If not currently clocked in, refresh status to sync UI
        if (error.message && error.message.includes('Not currently clocked in')) {
            showAlert(error.message, 'warning');
            loadCurrentStatus(); // Refresh to sync UI with actual status
        } else {
            showAlert('Failed to clock out. Please try again.', 'danger');
        }
    })
    .finally(() => {
        // Reset button
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

function startBreak() {
    console.log('startBreak() function called');
    const button = document.getElementById('breakStartBtn');
    const endButton = document.getElementById('breakEndBtn');

    // Show loading state
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Starting...';
    button.disabled = true;

    fetch('/api/break-start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert(data.error, 'danger');
        } else {
            showAlert('Break started', 'info');

            // Update state
            isOnBreak = true;
            breakStartTime = new Date();

            // Update buttons
            button.disabled = true;
            endButton.disabled = false;
            endButton.classList.remove('btn-info');
            endButton.classList.add('btn-success');

            // Log activity
            logActivity('Break Start', data.break_start_time);
        }
    })
    .catch(error => {
        console.error('Start break error:', error);
        showAlert('Failed to start break. Please try again.', 'danger');
    })
    .finally(() => {
        // Reset button
        button.innerHTML = originalText;
    });
}

function endBreak() {
    console.log('endBreak() function called');
    if (!isOnBreak || !breakStartTime) return;

    const button = document.getElementById('breakEndBtn');
    const startButton = document.getElementById('breakStartBtn');

    // Calculate break duration
    const now = new Date();
    const breakDuration = (now - breakStartTime) / 1000 / 3600; // Convert to hours

    // Show loading state
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Ending...';
    button.disabled = true;

    fetch('/api/break-end', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            break_duration: breakDuration
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showAlert(data.error, 'danger');
        } else {
            const breakTime = Math.round(breakDuration * 60); // Convert to minutes
            showAlert(`Break ended. Duration: ${breakTime} minutes`, 'info');

            // Update state
            isOnBreak = false;
            breakStartTime = null;

            // Update buttons
            startButton.disabled = false;
            button.disabled = true;
            button.classList.remove('btn-success');
            button.classList.add('btn-info');

            // Log activity
            logActivity('Break End', new Date().toISOString(), null, breakDuration);
        }
    })
    .catch(error => {
        console.error('End break error:', error);
        showAlert('Failed to end break. Please try again.', 'danger');
    })
    .finally(() => {
        // Reset button
        button.innerHTML = originalText;
    });
}

function logActivity(action, timestamp, hours = null, breakDuration = null) {
    // This function logs activities for display in recent activity feeds
    // In a real application, this might send to analytics or audit systems

    console.log(`Activity: ${action}`, {
        timestamp,
        hours,
        breakDuration,
        user: (window.app && window.app.currentUser) ? window.app.currentUser.username : 'unknown'
    });

    // Trigger refresh of activity displays
    if (typeof loadRecentActivity === 'function') {
        setTimeout(loadRecentActivity, 1000);
    }
}

// Time clock status updates
function updateTimeClockModal() {
    if (!window.app || !window.app.isClocked) return;

    // Update elapsed time display in modal
    const statusElement = document.querySelector('#timeClockModal .current-session');
    if (statusElement && window.app.clockInTime) {
        const now = new Date();
        const elapsed = Math.floor((now - new Date(window.app.clockInTime)) / 1000 / 60);
        const hours = Math.floor(elapsed / 60);
        const minutes = elapsed % 60;
        statusElement.textContent = `Current session: ${hours}h ${minutes}m`;
    }
}

// Initialize time clock functionality
document.addEventListener('DOMContentLoaded', function() {
    // Update modal time every second when open
    const timeClockModal = document.getElementById('timeClockModal');
    if (timeClockModal) {
        timeClockModal.addEventListener('shown.bs.modal', function() {
            updateModalTime();
            const interval = setInterval(updateModalTime, 1000);

            timeClockModal.addEventListener('hidden.bs.modal', function() {
                clearInterval(interval);
            }, { once: true });
        });
    }

    // Handle keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+Shift+T to toggle time clock
        if (e.ctrlKey && e.shiftKey && e.key === 'T') {
            e.preventDefault();
            toggleTimeClock();
        }

        // Escape to close time clock modal
        if (e.key === 'Escape') {
            const modal = bootstrap.Modal.getInstance(document.getElementById('timeClockModal'));
            if (modal) {
                modal.hide();
            }
        }
    });
});

// Debug function to test if updated file is loaded
window.testTimeclockLoaded = function() {
    console.log('Updated timeclock.js is loaded - added debugging to all functions');
    return 'v2.0-debug';
};

// Export functions for global use
window.toggleTimeClock = toggleTimeClock;
window.clockIn = clockIn;
window.clockOut = clockOut;
window.startBreak = startBreak;
window.endBreak = endBreak;