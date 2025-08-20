document.addEventListener('DOMContentLoaded', () => {
    // This safety check waits for Frappe's JS library to load.
    const checkFrappe = setInterval(() => {
        if (window.frappe) {
            clearInterval(checkFrappe);
            initializeDashboard();
        }
    }, 100);
});

function initializeDashboard() {
    loadDashboardData();

    const fab = document.getElementById('fab-new-audit');
    if (fab) {
        fab.onclick = () => {
            window.location.href = '/app/restaurant';
        };
    }
}

async function loadDashboardData() {
    try {
        // Use frappe.call - it will work perfectly now.
        const stats = await frappe.call({ method: "restaurant_audit.api.audit_api.get_dashboard_stats" });
        if (stats.message) {
            populateStatCards(stats.message);
        }

        const history = await frappe.call({ method: "restaurant_audit.api.audit_api.get_recent_audits" });
        if (history.message) {
            populateRecentAudits(history.message);
        }

    } catch (error) {
        console.error("Error loading dashboard data:", error);
        const listContainer = document.getElementById('audit-list');
        if(listContainer) {
            listContainer.innerHTML = `<p style="color: red;">Failed to load dashboard data. Please refresh.</p>`;
        }
    }
}

function populateStatCards(stats) {
    document.getElementById('overall-score').textContent = `${stats.overall_score || 0}%`;
    const circle = document.getElementById('overall-score-circle');
    if (circle) {
        const radius = circle.r.baseVal.value;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - ((stats.overall_score || 0) / 100) * circumference;
        circle.style.strokeDashoffset = offset;
    }
    document.getElementById('total-restaurants').textContent = stats.total_restaurants || 0;
    document.getElementById('pending-audits').textContent = stats.pending_audits || 0;
    document.getElementById('critical-issues').textContent = stats.critical_issues || 0;
}

function populateRecentAudits(audits) {
    const listContainer = document.getElementById('audit-list');
    listContainer.innerHTML = '';
    if (!audits || audits.length === 0) {
        listContainer.innerHTML = '<p>You have no recent audits. Start a new one!</p>';
        return;
    }
    audits.forEach(audit => {
        const item = document.createElement('div');
        item.className = 'audit-item';
        item.onclick = () => {
            window.location.href = `/app/audit-submission/${audit.name}`;
        };
        const auditDate = new Date(audit.audit_date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
        const statusClass = audit.status.toLowerCase().replace(/\s+/g, '-');
        let icon = '🏪';
        if (audit.status === 'Completed') icon = '✅';
        if (audit.status === 'In Progress') icon = '⏱️';
        if (audit.status === 'Critical Issues') icon = '⚠️';
        item.innerHTML = `
            <div class="audit-header">
                <div class="restaurant-name">${icon} ${audit.restaurant}</div>
                <div class="audit-status status-${statusClass}">${audit.status}</div>
            </div>
            <div class="audit-meta">
                <span>📅 ${auditDate}</span>
                <span>👤 ${audit.auditor}</span>
                <span>⭐ Score: ${audit.score}</span>
            </div>
        `;
        listContainer.appendChild(item);
    });
}