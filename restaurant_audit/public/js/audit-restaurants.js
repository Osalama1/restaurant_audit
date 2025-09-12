let allRestaurants = [];
let filteredRestaurants = [];
let currentFilter = 'all';
let selectedRestaurant = null;
let userDashboard = {};

document.addEventListener('DOMContentLoaded', function() {
    initializePage();
    setupSearchListener();
});

async function initializePage() {
    try {
        // Load user dashboard first
        await loadUserDashboard();
        
        // Then load restaurants
        await loadRestaurants();
    } catch (error) {
        console.error('Initialization error:', error);
        showError('Failed to initialize page. Please refresh.');
    }
}

async function loadUserDashboard() {
    try {
        const response = await fetch('/api/method/restaurant_audit.api.audit_api.get_user_dashboard', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        });

        const result = await response.json();
        if (result.message?.success) {
            userDashboard = result.message.dashboard;
            updateUserInfo();
            updateDashboardStats();
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

function updateUserInfo() {
    const userNameEl = document.getElementById('user-name');
    const userAvatarEl = document.getElementById('user-avatar');
    
    if (userDashboard.user) {
        const fullName = userDashboard.user.full_name || userDashboard.user.name;
        userNameEl.textContent = fullName;
        userAvatarEl.textContent = fullName.charAt(0).toUpperCase();
    }
}

function updateDashboardStats() {
    if (userDashboard.stats) {
        document.getElementById('total-audits').textContent = userDashboard.stats.total_audits || 0;
        document.getElementById('avg-score').textContent = userDashboard.stats.avg_score ? 
            parseFloat(userDashboard.stats.avg_score).toFixed(1) : '0.0';
    }
    
    document.getElementById('pending-progress').textContent = 
        userDashboard.pending_progress ? userDashboard.pending_progress.length : 0;
}
// Replace loadRestaurants function in audit-restaurants.html

async function loadRestaurants() {
    try {
console.log('Loading restaurants with week status...');
const response = await fetch('/api/method/restaurant_audit.api.audit_api.get_restaurants_with_week_status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include'
});

console.log('Response status:', response.status);
const result = await response.json();
console.log('API Response:', result);

if (result.message?.success) {
    allRestaurants = result.message.restaurants;
    console.log('Loaded restaurants:', allRestaurants.length);
    document.getElementById('total-restaurants').textContent = allRestaurants.length;
    
    // Check for pending progress
    await checkPendingProgress();
    
    filteredRestaurants = [...allRestaurants];
    
    document.getElementById('loading').style.display = 'none';
    
    if (allRestaurants.length === 0) {
        console.log('No restaurants found, showing empty state');
        document.getElementById('empty-state').style.display = 'block';
    } else {
        document.getElementById('restaurants-container').style.display = 'grid';
        renderRestaurants();
    }
} else {
    console.error('API returned error:', result.message);
    throw new Error(result.message?.message || 'Failed to load restaurants');
}
    } catch (error) {
console.error('Error loading restaurants:', error);
showError(error.message || 'Failed to load restaurants. Please try again.');
    }
}
async function checkPendingProgress() {
    for (let restaurant of allRestaurants) {
        try {
            const response = await fetch('/api/method/restaurant_audit.api.audit_api.get_audit_progress', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ restaurant_id: restaurant.name }),
                credentials: 'include'
            });

            const result = await response.json();
            if (result.message?.success && result.message.has_progress) {
                restaurant.has_progress = true;
                restaurant.progress_data = result.message;
            }
        } catch (error) {
            console.error('Error checking progress for', restaurant.name, error);
        }
    }
}

function renderRestaurants() {
    const container = document.getElementById('restaurants-container');
    container.innerHTML = '';

    filteredRestaurants.forEach((restaurant, index) => {
        const card = createRestaurantCard(restaurant, index);
        container.appendChild(card);
    });
}
// Updated restaurant card creation with week status
function createRestaurantCard(restaurant, index) {
    const card = document.createElement('div');
    
    // Determine card class based on week status
    let cardClass = 'restaurant-card';
    if (restaurant.has_progress) {
cardClass += ' has-progress';
    }
    if (restaurant.week_complete) {
cardClass += ' week-completed';
    }
    
    card.className = cardClass;
    card.style.animationDelay = `${index * 0.1}s`;
    card.dataset.restaurantId = restaurant.name;
    card.dataset.status = restaurant.status || 'active';

    const lastAuditText = restaurant.last_audit_date ? 
`${formatDateDiff(restaurant.last_audit_date)} days ago` : 'Never';
    
    const progressIndicator = restaurant.has_progress ? 
'<div class="progress-indicator">!</div>' : '';
    
    // Week status indicator
    const weekStatusIndicator = restaurant.week_complete ? 
'<div class="week-status-indicator">✅ Week Complete</div>' : 
'<div class="week-status-indicator available">📝 Available</div>';
    
    // Determine if card should be clickable
    const clickable = restaurant.can_access && !restaurant.week_complete;
    const cardStyle = clickable ? '' : 'style="opacity: 0.6; cursor: not-allowed;"';
    
    card.innerHTML = `
${progressIndicator}
${weekStatusIndicator}
<div class="restaurant-header">
    <div>
        <div class="restaurant-name">${restaurant.restaurant_name}</div>
        ${restaurant.week_complete ? 
            `<div class="week-message">${restaurant.week_message}</div>` : 
            ''
        }
    </div>
    <div style="display: flex; align-items: center; gap: 0.5rem;">
        ${clickable ? 
            `<button class="schedule-visit-btn" onclick="event.stopPropagation(); openScheduleModal('${restaurant.name}', '${restaurant.restaurant_name}')" title="Schedule Visit">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="12" y1="5" x2="12" y2="19"/>
                    <line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
            </button>` : ''
        }
        <div class="restaurant-status status-${restaurant.status || 'active'}">
            ${restaurant.status || 'active'}
        </div>
    </div>
</div>

<div class="restaurant-address">${restaurant.address || 'Address not specified'}</div>
<div class="restaurant-employee">
    <strong>Auditor:</strong> ${restaurant.employee_name || 'Unassigned'} 
    (${restaurant.designation || '—'})
</div>

<div class="restaurant-stats">
    <div class="stat-item">
        <div class="stat-item-value">${restaurant.total_audits || 0}</div>
        <div class="stat-item-label">Total Audits</div>
    </div>
    <div class="stat-item">
        <div class="stat-item-value">${restaurant.my_audits || 0}</div>
        <div class="stat-item-label">My Audits</div>
    </div>
</div>

<div class="restaurant-meta">
    <div class="location-info">
        <div class="location-dot"></div>
        <span>${restaurant.location_radius || 100}m radius</span>
    </div>
    <div>Last audit: ${lastAuditText}</div>
</div>

${restaurant.week_complete && restaurant.next_access ? 
    `<div class="next-access-info">
        📅 Next access: ${formatDate(restaurant.next_access)}
    </div>` : ''
}
    `;
    function showWeekCompletionMessage(restaurant) {
    const nextAccessDate = restaurant.next_access ? 
new Date(restaurant.next_access).toLocaleDateString('en-US', { 
    weekday: 'long', 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
}) : 'Next week';
    
    alert(`${restaurant.week_message}\n\nNext access: ${nextAccessDate}`);
}
    // Only add click listener if restaurant is accessible
    if (clickable) {
card.addEventListener('click', () => selectRestaurant(restaurant));
    } else {
card.addEventListener('click', () => {
    if (restaurant.week_complete) {
        showWeekCompletionMessage(restaurant);
    } else {
        alert('This restaurant is not accessible. Please contact your administrator.');
    }
});
    }
    
    return card;
}
// Updated selectRestaurant function with validation
function selectRestaurant(restaurant) {
    selectedRestaurant = restaurant;
    
    // Double-check access before proceeding
    if (restaurant.week_complete || !restaurant.can_access) {
showWeekCompletionMessage(restaurant);
return;
    }
    
    // Check if there's saved progress
    if (restaurant.has_progress) {
showProgressModal(restaurant);
    } else {
startAudit(restaurant);
    }
}


function showProgressModal(restaurant) {
    const modal = document.getElementById('progress-modal');
    const details = document.getElementById('progress-details');
    
    const progressData = restaurant.progress_data;
    const lastUpdated = new Date(progressData.last_updated).toLocaleString();
    const answeredCount = Object.keys(progressData.answers || {}).length;
    
    details.textContent = `You have ${answeredCount} answers saved from ${lastUpdated}. Would you like to continue or start fresh?`;
    modal.classList.add('active');
}

function startNewAudit() {
    const modal = document.getElementById('progress-modal');
    modal.classList.remove('active');
    
    // Delete existing progress
    if (selectedRestaurant.progress_data.progress_id) {
        deleteProgress(selectedRestaurant.progress_data.progress_id);
    }
    
    startAudit(selectedRestaurant);
}

function continueAudit() {
    const modal = document.getElementById('progress-modal');
    modal.classList.remove('active');
    startAudit(selectedRestaurant);
}

function startAudit(restaurant) {
    // Store selected restaurant in sessionStorage
    sessionStorage.setItem('selectedRestaurant', JSON.stringify(restaurant));
    
    // Redirect to audit form
    window.location.href = `/audit-form?restaurant=${restaurant.name}`;
}

async function deleteProgress(progressId) {
    try {
        await fetch('/api/method/restaurant_audit.api.audit_api.delete_audit_progress', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ progress_id: progressId }),
            credentials: 'include'
        });
    } catch (error) {
        console.error('Error deleting progress:', error);
    }
}

function filterRestaurants(filter) {
    currentFilter = filter;
    
    // Update filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    event.target.classList.add('active');
    
    // Apply filter
    applyFiltersAndSearch();
}

function setupSearchListener() {
    const searchInput = document.getElementById('search-input');
    searchInput.addEventListener('input', (e) => {
        applyFiltersAndSearch();
    });
}

function applyFiltersAndSearch() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    
    filteredRestaurants = allRestaurants.filter(restaurant => {
        // Apply status filter
        const statusMatch = currentFilter === 'all' || 
            (restaurant.status || 'active') === currentFilter;
        
        // Apply search filter
        const searchMatch = !searchTerm || 
            restaurant.restaurant_name.toLowerCase().includes(searchTerm) ||
            (restaurant.address && restaurant.address.toLowerCase().includes(searchTerm));
        
        return statusMatch && searchMatch;
    });
    
    renderRestaurants();
    
    // Show/hide empty state
    if (filteredRestaurants.length === 0 && allRestaurants.length > 0) {
        document.getElementById('restaurants-container').style.display = 'none';
        document.getElementById('empty-state').style.display = 'block';
        document.getElementById('empty-state').innerHTML = `
            <div class="empty-state-icon">🔍</div>
            <h3>No Results Found</h3>
            <p>No restaurants match your current filter and search criteria.</p>
        `;
    } else if (filteredRestaurants.length > 0) {
        document.getElementById('restaurants-container').style.display = 'grid';
        document.getElementById('empty-state').style.display = 'none';
    }
}

function showError(message) {
    document.getElementById('loading').style.display = 'none';
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        // Clear stored data
        sessionStorage.clear();
        localStorage.clear();
        
        // Redirect to login
        window.location.href = '/audit-login';
    }
}

// Close modal when clicking outside
document.getElementById('progress-modal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) {
        e.currentTarget.classList.remove('active');
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.getElementById('progress-modal').classList.remove('active');
    }
});

// Employee cleanup functions
function cleanupEmployeeLocalData(employeeId, restaurantId) {
    try {
        // Clear localStorage data for this employee and restaurant
        const keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && (key.includes(`audit_progress_${restaurantId}`) || key.includes(`employee_${employeeId}`))) {
                keysToRemove.push(key);
            }
        }
        
        keysToRemove.forEach(key => {
            localStorage.removeItem(key);
        });
        
        console.log(`Cleaned up localStorage data for employee ${employeeId} and restaurant ${restaurantId}`);
        
        // Refresh the page to reflect changes
        setTimeout(() => {
            window.location.reload();
        }, 1000);
        
    } catch (error) {
        console.error('Error cleaning up employee local data:', error);
    }
}

// Listen for employee removal events (this would be triggered by the backend)
function checkForEmployeeRemovals() {
    // This function can be called periodically or triggered by specific events
    // For now, we'll check on page load
    fetch('/api/method/restaurant_audit.api.audit_api.check_employee_removals')
        .then(response => response.json())
        .then(data => {
            if (data.message && data.message.removed_employees) {
                data.message.removed_employees.forEach(removal => {
                    cleanupEmployeeLocalData(removal.employee_id, removal.restaurant_id);
                });
            }
        })
        .catch(error => {
            console.error('Error checking for employee removals:', error);
        });
}

// Add periodic check for employee removals (every 30 seconds)
setInterval(() => {
    checkForEmployeeRemovals();
}, 30000);

// Call on page load
checkForEmployeeRemovals();

// Debug function to check user assignments
async function debugUserAssignments() {
    try {
        const response = await fetch('/api/method/restaurant_audit.api.audit_api.verify_user_assignments', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        });
        
        const result = await response.json();
        console.log('User Assignment Debug:', result);
        
        if (result.message && result.message.success) {
            alert(`Debug Info:\nEmployee: ${result.message.employee}\nTotal Assignments: ${result.message.total_assignments}\nActive Assignments: ${result.message.active_assignments}\nRestaurants: ${result.message.assigned_restaurants.join(', ')}`);
        } else {
            console.error('Debug failed:', result.message);
        }
    } catch (error) {
        console.error('Error in debug:', error);
    }
}

// Add debug button (temporary)
window.debugAssignments = debugUserAssignments;

// Cleanup function for old scheduled visits
async function cleanupOldVisits() {
    try {
        const response = await fetch('/api/method/restaurant_audit.api.audit_api.cleanup_old_scheduled_visits', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        });
        
        const result = await response.json();
        console.log('Cleanup Result:', result);
        
        if (result.message && result.message.success) {
            // Only show message if there were actually visits cleaned up
            if (result.message.cleaned_visits > 0) {
                alert(`Cleanup completed!\nCleaned up ${result.message.cleaned_visits} old scheduled visits.`);
                // Refresh the page to show updated data
                window.location.reload();
            } else {
                console.log('No old visits to clean up');
            }
        } else {
            console.error('Cleanup failed:', result.message);
        }
    } catch (error) {
        console.error('Error in cleanup:', error);
    }
}

// Add cleanup button (temporary) - only call manually
window.cleanupOldVisits = cleanupOldVisits;

// Run cleanup silently in background without popup
cleanupOldVisits();

// Add function to refresh week periods when day changes
function checkAndRefreshWeekPeriods() {
    const today = new Date();
    const lastRefresh = localStorage.getItem('lastWeekRefresh');
    const lastRefreshDate = lastRefresh ? new Date(lastRefresh) : null;
    
    // Check if it's a new day since last refresh
    if (!lastRefreshDate || today.toDateString() !== lastRefreshDate.toDateString()) {
        console.log('New day detected, refreshing week periods...');
        localStorage.setItem('lastWeekRefresh', today.toISOString());
        
        // Reload all data to refresh week periods
        loadRestaurants();
        loadMyScheduledVisits();
    }
}

// Check for day change every hour
setInterval(checkAndRefreshWeekPeriods, 60 * 60 * 1000); // 1 hour

// Check on page load
checkAndRefreshWeekPeriods();

// New functionality variables
let selectedRestaurantForScheduling = null;
let templateSchedule = { openTime: '06:00', closeTime: '08:30', cashierOpenTime: '09:00' };

// Tab switching functionality
function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.querySelectorAll('.tab-button').forEach(button => button.classList.remove('active'));
    document.getElementById(tabName + '-content').classList.add('active');
    event.target.classList.add('active');
    if (tabName === 'daily-audit') loadDailyAuditData();
}

// Scheduling functions
function openScheduleModal(restaurantId, restaurantName) {
    selectedRestaurantForScheduling = restaurantId;
    document.getElementById('modal-restaurant-name').value = restaurantName;
    document.getElementById('schedule-visit-modal').classList.add('active');
}

function closeScheduleModal() {
    document.getElementById('schedule-visit-modal').classList.remove('active');
}

// Template functions - now read-only from backend

function isTemplateOpen() {
    const now = new Date();
    const currentTime = now.getHours() * 60 + now.getMinutes();
    const openTime = parseInt(templateSchedule.openTime.split(':')[0]) * 60 + parseInt(templateSchedule.openTime.split(':')[1]);
    const closeTime = parseInt(templateSchedule.closeTime.split(':')[0]) * 60 + parseInt(templateSchedule.closeTime.split(':')[1]);
    return currentTime >= openTime && currentTime <= closeTime;
}

async function loadDailyAuditData() {
    updateTemplateStatus();
    await loadDailyTemplatesFromBackend();
}
// Replace these functions in audit-restaurants.html

async function loadScheduledAudits() {
    try {
console.log('Loading scheduled audits for current and next week only...');
const response = await fetch('/api/method/restaurant_audit.api.audit_api.get_weekly_scheduled_audits', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include'
});

console.log('Weekly scheduled audits response status:', response.status);
const result = await response.json();
console.log('Weekly scheduled audits API Response:', result);

if (result.message?.success) {
    console.log('Weekly scheduled audits loaded');
    renderWeeklyScheduledAudits(result.message.current_week, result.message.next_week);
    
    // Process last week status updates
    await processLastWeekUpdates();
} else {
    console.error('Failed to load weekly scheduled audits:', result.message);
}
    } catch (error) {
console.error('Error loading weekly scheduled audits:', error);
    }
}

async function loadMyScheduledVisits() {
    try {
console.log('Loading my scheduled visits for current and next week only...');
const response = await fetch('/api/method/restaurant_audit.api.audit_api.get_my_weekly_visits', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include'
});

console.log('My weekly visits response status:', response.status);
const result = await response.json();
console.log('My weekly visits API Response:', result);

if (result.message?.success) {
    console.log('My weekly visits loaded');
    renderMyWeeklyVisits(result.message.current_week, result.message.next_week);
    
    // Update weekly summary display
    updateWeeklySummary(result.message);
    
    // Update week period display for the table
    if (result.message.current_week && result.message.current_week.start && result.message.current_week.end) {
        const weekLabel = `${formatDate(result.message.current_week.start)} - ${formatDate(result.message.current_week.end)}`;
        console.log('Week period:', weekLabel);
        document.querySelector('.my-visits-section h3').innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 11l3 3 8-8"/>
                <path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9c1.51 0 2.93.37 4.18 1.03"/>
            </svg>
            My Scheduled Visits for the Week (${weekLabel})
        `;
    }
} else {
    console.error('Failed to load my weekly visits:', result.message);
}
    } catch (error) {
console.error('Error loading my weekly visits:', error);
    }
}

function renderWeeklyScheduledAudits(currentWeek, nextWeek) {
    const grid = document.getElementById('scheduled-visits-grid');
    grid.innerHTML = '';

    // Add current week header
    if (currentWeek.scheduled_audits.length > 0) {
const currentWeekHeader = document.createElement('div');
currentWeekHeader.className = 'week-header';
currentWeekHeader.innerHTML = `
    <h4>Current Week (${formatDate(currentWeek.start)} - ${formatDate(currentWeek.end)})</h4>
`;
grid.appendChild(currentWeekHeader);

currentWeek.scheduled_audits.forEach(audit => {
    grid.appendChild(createScheduledAuditCard(audit, 'current'));
});
    }

    // Add next week header
    if (nextWeek.scheduled_audits.length > 0) {
const nextWeekHeader = document.createElement('div');
nextWeekHeader.className = 'week-header';
nextWeekHeader.innerHTML = `
    <h4>Next Week (${formatDate(nextWeek.start)} - ${formatDate(nextWeek.end)})</h4>
`;
grid.appendChild(nextWeekHeader);

nextWeek.scheduled_audits.forEach(audit => {
    grid.appendChild(createScheduledAuditCard(audit, 'next'));
});
    }

    if (currentWeek.scheduled_audits.length === 0 && nextWeek.scheduled_audits.length === 0) {
grid.innerHTML = '<p style="text-align: center; color: var(--neutral-500); grid-column: 1 / -1;">No scheduled audits for current and next week.</p>';
    }
}

function createScheduledAuditCard(audit, weekType) {
    const card = document.createElement('div');
    card.className = `scheduled-visit-card ${weekType}-week`;
    
    // Add visual indicator for week type
    const weekIndicator = weekType === 'current' ? '📅' : '⏳';
    
    card.innerHTML = `
<div class="week-indicator">${weekIndicator} ${weekType.toUpperCase()}</div>
<div class="visit-restaurant-name">${audit.restaurant_name}</div>
<div class="visit-date">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/>
        <line x1="8" y1="2" x2="8" y2="6"/>
        <line x1="3" y1="10" x2="21" y2="10"/>
    </svg>
    ${formatDate(audit.visit_date)}
</div>
<div class="visit-status ${audit.status.toLowerCase()}">${audit.status}</div>
${weekType === 'current' ? `<div class="urgency-indicator">⚠️ This Week</div>` : ''}
    `;
    return card;
}

function renderMyWeeklyVisits(currentWeek, nextWeek) {
    const tbody = document.getElementById('my-visits-tbody');
    tbody.innerHTML = '';

    // Combine current and next week visits
    const allVisits = [
...currentWeek.visits.map(v => ({...v, week_type: 'Current'})),
...nextWeek.visits.map(v => ({...v, week_type: 'Next'}))
    ];

    if (allVisits.length === 0) {
tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--neutral-500);">No scheduled visits for current and next week.</td></tr>';
return;
    }

    allVisits.forEach(visit => {
const row = document.createElement('tr');
const weekBadge = visit.week_type === 'Current' ? 
    '<span class="week-badge current">📅 This Week</span>' : 
    '<span class="week-badge next">⏳ Next Week</span>';

row.innerHTML = `
    <td>${visit.restaurant_name}</td>
    <td>${formatDate(visit.visit_date)}</td>
    <td><span class="visit-status ${visit.status.toLowerCase()}">${visit.status}</span></td>
    <td>${weekBadge}</td>
`;
tbody.appendChild(row);
    });
}

async function processLastWeekUpdates() {
    try {
console.log('Processing last week status updates...');
const response = await fetch('/api/method/restaurant_audit.api.audit_api.process_last_week_status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include'
});

const result = await response.json();
if (result.message?.success) {
    console.log('Last week processed:', result.message);
    
    // Show notification if there were updates
    if (result.message.updates_made > 0) {
        showNotification(`Last week processed: ${result.message.updates_made} audits updated to Overdue`, 'info');
    }
}
    } catch (error) {
console.error('Error processing last week updates:', error);
    }
}

function updateWeeklySummary(weeklyData) {
    // Update the weekly summary section
    const currentWeekSummary = document.getElementById('current-week-summary');
    const nextWeekSummary = document.getElementById('next-week-summary');
    
    if (currentWeekSummary) {
const currentTotal = weeklyData.current_week.visits.length;
const currentCompleted = weeklyData.current_week.visits.filter(v => v.status === 'Completed').length;
const currentPending = currentTotal - currentCompleted;

currentWeekSummary.innerHTML = `
    <h4>This Week Summary</h4>
    <div class="summary-stats">
        <span class="stat">📊 Total: ${currentTotal}</span>
        <span class="stat">✅ Completed: ${currentCompleted}</span>
        <span class="stat">⏳ Pending: ${currentPending}</span>
    </div>
`;
    }
    
    if (nextWeekSummary) {
const nextTotal = weeklyData.next_week.visits.length;

nextWeekSummary.innerHTML = `
    <h4>Next Week Summary</h4>
    <div class="summary-stats">
        <span class="stat">📅 Scheduled: ${nextTotal}</span>
        <span class="stat ${nextTotal === 0 ? 'warning' : ''}">
            ${nextTotal === 0 ? '⚠️ No audits scheduled!' : '✅ Ready to go'}
        </span>
    </div>
`;
    }
}

// Add CSS for weekly display
const weeklyStyles = `
<style>
.week-header {
    grid-column: 1 / -1;
    padding: 1rem;
    background: var(--primary-color);
    color: white;
    border-radius: 8px;
    margin: 1rem 0 0.5rem 0;
    text-align: center;
}

.week-header h4 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
}

.scheduled-visit-card.current-week {
    border-left: 4px solid var(--warning-color);
    background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
}

.scheduled-visit-card.next-week {
    border-left: 4px solid var(--primary-color);
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
}

.week-indicator {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--primary-color);
    margin-bottom: 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.urgency-indicator {
    margin-top: 0.5rem;
    padding: 0.25rem 0.5rem;
    background: var(--warning-color);
    color: white;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-align: center;
}

.week-badge {
    padding: 0.25rem 0.5rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
}

.week-badge.current {
    background: #fef3c7;
    color: #92400e;
}

.week-badge.next {
    background: #e0f2fe;
    color: #0369a1;
}

.summary-stats {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    margin-top: 0.5rem;
}

.summary-stats .stat {
    padding: 0.25rem 0.5rem;
    background: var(--neutral-100);
    border-radius: 6px;
    font-size: 0.875rem;
}

.summary-stats .stat.warning {
    background: #fee2e2;
    color: #991b1b;
}

#my-scheduled-visits-table th:last-child,
#my-scheduled-visits-table td:last-child {
    text-align: center;
}
</style>
`;

// Add the styles to the page
if (!document.getElementById('weekly-styles')) {
    const styleElement = document.createElement('style');
    styleElement.id = 'weekly-styles';
    styleElement.textContent = weeklyStyles.replace('<style>', '').replace('</style>', '');
    document.head.appendChild(styleElement);
}

// Update the visits table header to include week column
document.addEventListener('DOMContentLoaded', function() {
    const visitsTableHeader = document.querySelector('#my-scheduled-visits-table thead tr');
    if (visitsTableHeader && !visitsTableHeader.querySelector('.week-column')) {
const weekHeader = document.createElement('th');
weekHeader.className = 'week-column';
weekHeader.textContent = 'Week';
visitsTableHeader.appendChild(weekHeader);
    }
});
function renderScheduledAudits(audits) {
    const grid = document.getElementById('scheduled-visits-grid');
    grid.innerHTML = '';

    if (audits.length === 0) {
        grid.innerHTML = '<p style="text-align: center; color: var(--neutral-500); grid-column: 1 / -1;">No scheduled audits found.</p>';
        return;
    }

    audits.forEach(audit => {
        const card = document.createElement('div');
        card.className = 'scheduled-visit-card';
        card.innerHTML = `
            <div class="visit-restaurant-name">${audit.restaurant_name}</div>
            <div class="visit-date">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                    <line x1="16" y1="2" x2="16" y2="6"/>
                    <line x1="8" y1="2" x2="8" y2="6"/>
                    <line x1="3" y1="10" x2="21" y2="10"/>
                </svg>
                ${formatDate(audit.visit_date)}
            </div>
            <div class="visit-status ${audit.status.toLowerCase()}">${audit.status}</div>
            <div style="font-size: 0.75rem; color: var(--neutral-500); margin-top: 0.5rem;">
                Week: ${formatDate(audit.week_start_date)} - ${formatDate(audit.week_end_date)}
            </div>
        `;
        grid.appendChild(card);
    });
}

// Removed duplicate loadMyScheduledVisits function - using the first one that calls get_my_weekly_visits

function renderMyScheduledVisits(visits) {
    const tbody = document.getElementById('my-visits-tbody');
    tbody.innerHTML = '';

    if (visits.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--neutral-500);">No scheduled visits for this week.</td></tr>';
        return;
    }

    visits.forEach(visit => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${visit.restaurant_name}</td>
            <td>${formatDate(visit.visit_date)}</td>
            <td><span class="visit-status ${visit.status.toLowerCase()}">${visit.status}</span></td>
        `;
        tbody.appendChild(row);
    });
}

async function loadDailyTemplatesFromBackend() {
    try {
        const response = await fetch('/api/method/restaurant_audit.api.audit_api.get_daily_templates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        });

        const result = await response.json();
        if (result.message?.success) {
            renderDailyTemplatesFromBackend(result.message.templates);
        } else {
            // Fallback to sample templates if no backend templates
            renderSampleTemplates();
        }
    } catch (error) {
        console.error('Error loading daily templates:', error);
        renderSampleTemplates();
    }
}

function renderDailyTemplatesFromBackend(templates) {
    const container = document.getElementById('templates-list');
    container.innerHTML = '';

    if (templates.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: var(--neutral-500);">No templates found. Create templates from ERPNext backend.</p>';
        return;
    }

    templates.forEach(template => {
        const card = document.createElement('div');
        card.className = `template-card ${!template.is_currently_open ? 'disabled' : ''}`;
        card.style.position = 'relative';

        card.innerHTML = `
            <div class="template-header">
                <div class="template-name">${template.template_name}</div>
                <div class="template-status ${template.current_status.toLowerCase()}">${template.current_status}</div>
            </div>
            <div class="template-description">${template.description || 'No description available'}</div>
            <div class="template-schedule">
                📍 ${template.applies_to_all_restaurants ? 'All Restaurants' : (template.restaurant_name || 'Specific Restaurant')}
                | 📝 ${template.questions_count} questions
            </div>
            <div class="template-schedule" style="margin-bottom: 1rem;">
                🕐 ${template.open_time} - ${template.close_time} (Cashier: ${template.cashier_opening_time})
            </div>
            <div class="template-actions">
                <button class="btn btn-primary" ${!template.is_currently_open ? 'disabled' : ''} 
                        onclick="${template.is_currently_open ? `startDailyAudit('${template.name}')` : ''}"}>
                    ${template.is_currently_open ? 'Start Audit' : 'Closed'}
                </button>
            </div>
        `;
        container.appendChild(card);
    });
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}
// Replace the startDailyAudit function in your audit-restaurants.html

// Updated start daily audit with restrictions
async function startDailyAudit(templateName) {
    try {
// First check if daily audit can be started
const canStartResponse = await fetch('/api/method/restaurant_audit.api.audit_api.can_start_daily_audit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        template_name: templateName
    }),
    credentials: 'include'
});

const canStartResult = await canStartResponse.json();
if (!canStartResult.message?.success) {
    alert(canStartResult.message?.message || 'Cannot start daily audit');
    return;
}

console.log("🚀 Starting daily audit for template:", templateName);

const response = await fetch('/api/method/restaurant_audit.api.audit_api.start_daily_audit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        template_name: templateName
    }),
    credentials: 'include'
});

const result = await response.json();
console.log("📊 Daily audit API response:", result);

if (result.message?.success) {
    // Store audit data in sessionStorage for the audit form
    sessionStorage.setItem('dailyAuditData', JSON.stringify({
        template: result.message.template,
        questions_data: result.message.questions_data,
        progress_id: result.message.progress_id,
        restaurant: result.message.restaurant,
        is_daily_audit: true
    }));
    
    console.log("💾 Stored daily audit data:", {
        restaurant: result.message.restaurant,
        progress_id: result.message.progress_id,
        questions_count: result.message.questions_data?.length || 0
    });
    
    // Redirect to audit form
    window.location.href = `/audit-form?daily_audit=1&progress_id=${result.message.progress_id}`;
} else {
    alert(result.message?.message || 'Failed to start daily audit');
}
    } catch (error) {
console.error('Error starting daily audit:', error);
alert('Error starting daily audit. Please try again.');
    }
}

// New functions to load data with status updates
async function loadScheduledAuditsWithStatusUpdate() {
    try {
// First trigger status update
await fetch('/api/method/restaurant_audit.api.audit_api.process_last_week_status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include'
});

// Then load the updated data
await loadScheduledAudits();
    } catch (error) {
console.error('Error loading scheduled audits with status update:', error);
// Fallback to regular loading
await loadScheduledAudits();
    }
}

async function loadMyScheduledVisitsWithStatusUpdate() {
    try {
// First trigger status update  
await fetch('/api/method/restaurant_audit.api.audit_api.process_last_week_status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include'
});

// Then load the updated data
await loadMyScheduledVisits();
    } catch (error) {
console.error('Error loading my visits with status update:', error);
// Fallback to regular loading
await loadMyScheduledVisits();
    }
}

function updateTemplateStatus() {
    const isOpen = isTemplateOpen();
    document.getElementById('current-template-status').innerHTML = 
        `Templates are currently: <strong style="color: ${isOpen ? 'var(--success-color)' : 'var(--error-color)'};">${isOpen ? 'Open' : 'Closed'}</strong>`;
}

function renderSampleTemplates() {
    const container = document.getElementById('templates-list');
    const isOpen = isTemplateOpen();
    container.innerHTML = `
        <div class="template-card ${isOpen ? '' : 'disabled'}" style="position: relative;">
            <div class="template-header">
                <div class="template-name">Morning Opening Checklist</div>
                <div class="template-status ${isOpen ? 'active' : 'closed'}">${isOpen ? 'Active' : 'Closed'}</div>
            </div>
            <div class="template-description">Pre-opening checklist to ensure restaurant readiness before cashier opening</div>
            <div class="template-schedule">📍 All Restaurants | 📝 15 questions</div>
            <div class="template-schedule">🕐 Daily ${templateSchedule.openTime} - ${templateSchedule.closeTime}</div>
            <div class="template-actions">
                <button class="btn btn-primary" ${isOpen ? '' : 'disabled'}>${isOpen ? 'Start Audit' : 'Closed'}</button>
            </div>
        </div>
    `;
}

// Additional functions for scheduling and template management
// Updated schedule audit with validation
async function scheduleAudit() {
    const restaurantId = document.getElementById('restaurant-select').value;
    const visitDate = document.getElementById('visit-date').value;
    
    if (!restaurantId || !visitDate) {
alert('Please select both restaurant and visit date.');
return;
    }
    
    // Client-side date validation
    const today = new Date();
    const selectedDate = new Date(visitDate);
    const maxDate = new Date();
    maxDate.setDate(today.getDate() + 21);
    
    if (selectedDate < today.setHours(0,0,0,0)) {
alert('Cannot schedule audit for past dates.');
return;
    }
    
    if (selectedDate > maxDate) {
alert('Cannot schedule audit more than 3 weeks in advance.');
return;
    }
    
    try {
const response = await fetch('/api/method/restaurant_audit.api.audit_api.schedule_audit_visit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        restaurant: restaurantId,
        visit_date: visitDate
    }),
    credentials: 'include'
});

const result = await response.json();
if (result.message?.success) {
    alert('Audit visit scheduled successfully!');
    document.getElementById('restaurant-select').value = '';
    document.getElementById('visit-date').value = '';
    
    // Reload data
    await loadScheduledAuditsWithStatusUpdate();
    await loadMyScheduledVisitsWithStatusUpdate();
} else {
    alert(result.message?.message || 'Failed to schedule audit visit');
}
    } catch (error) {
console.error('Error scheduling audit:', error);
alert('Error scheduling audit. Please try again.');
    }
}
async function confirmScheduleVisit() {
    const visitDate = document.getElementById('modal-visit-date').value;
    if (!visitDate) {
alert('Please select a visit date.');
return;
    }
    
    // Client-side validation
    const today = new Date();
    const selectedDate = new Date(visitDate);
    const maxDate = new Date();
    maxDate.setDate(today.getDate() + 21);
    
    if (selectedDate < today.setHours(0,0,0,0)) {
alert('Cannot schedule audit for past dates.');
return;
    }
    
    if (selectedDate > maxDate) {
alert('Cannot schedule audit more than 3 weeks in advance.');
return;
    }
    
    try {
const response = await fetch('/api/method/restaurant_audit.api.audit_api.schedule_audit_visit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        restaurant: selectedRestaurantForScheduling,
        visit_date: visitDate
    }),
    credentials: 'include'
});

const result = await response.json();
if (result.message?.success) {
    alert('Audit visit scheduled successfully!');
    closeScheduleModal();
    
    // Reload data
    await loadScheduledAuditsWithStatusUpdate();
    await loadMyScheduledVisitsWithStatusUpdate();
} else {
    alert(result.message?.message || 'Failed to schedule audit visit');
}
    } catch (error) {
console.error('Error scheduling audit:', error);
alert('Error scheduling audit. Please try again.');
    }
}

// Initialize date inputs and load restaurant options
document.addEventListener('DOMContentLoaded', function() {
    const today = new Date()
    const todayStr = today.toISOString().split('T')[0];
    
    // Calculate 3 weeks from today
    const maxDate = new Date();
    maxDate.setDate(today.getDate() + 21);
    const maxDateStr = maxDate.toISOString().split('T')[0];
    
    // Set date restrictions
    const visitDateInput = document.getElementById('visit-date');
    const modalVisitDateInput = document.getElementById('modal-visit-date');
    
    if (visitDateInput) {
visitDateInput.min = todayStr;
visitDateInput.max = maxDateStr;
    }
    
    if (modalVisitDateInput) {
modalVisitDateInput.min = todayStr;
modalVisitDateInput.max = maxDateStr;
    }


    
    
    // Load restaurant options after restaurants are loaded
    setTimeout(() => {
        if (allRestaurants.length > 0) {
            const select = document.getElementById('restaurant-select');
            select.innerHTML = '<option value="">Choose a restaurant...</option>';
            allRestaurants.forEach(restaurant => {
                const option = document.createElement('option');
                option.value = restaurant.name;
                option.textContent = restaurant.restaurant_name;
                select.appendChild(option);
            });

            // Load scheduled visits data
            loadScheduledAudits();
            loadMyScheduledVisits();
        }
    }, 2000);
    
    // Update template status every minute for daily audit tab
    setInterval(() => {
        if (document.getElementById('daily-audit-content').classList.contains('active')) {
            loadDailyTemplatesFromBackend();
        }
    }, 60000);
});

// Helper function to format date difference
function formatDateDiff(dateString) {
    const date = new Date(dateString);
    const today = new Date();
    const diffTime = Math.abs(today - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
}

// Add CSS for week status indicators
const weekStatusStyles = `
<style>
.week-status-indicator {
    position: absolute;
    top: 0.5rem;
    left: 0.5rem;
    padding: 0.25rem 0.5rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    background: #d1fae5;
    color: #065f46;
}

.week-status-indicator.available {
    background: #dbeafe;
    color: #1d4ed8;
}

.restaurant-card.week-completed {
    border-left: 4px solid #10b981;
    background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%);
}

.week-message {
    font-size: 0.75rem;
    color: #10b981;
    font-weight: 500;
    margin-top: 0.25rem;
}

.next-access-info {
    margin-top: 1rem;
    padding: 0.5rem;
    background: #fef3c7;
    border-radius: 6px;
    font-size: 0.75rem;
    color: #92400e;
    text-align: center;
}
</style>
`;
if (!document.getElementById('week-status-styles')) {
    const styleElement = document.createElement('style');
    styleElement.id = 'week-status-styles';
    styleElement.textContent = weekStatusStyles.replace('<style>', '').replace('</style>', '');
    document.head.appendChild(styleElement);
}
