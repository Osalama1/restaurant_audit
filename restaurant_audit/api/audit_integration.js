// Frontend API Integration for Restaurant Audit System
// This file handles all API calls between the UI and backend

class AuditAPI {
    constructor() {
        this.baseUrl = '/api/resource';
    }

    // Schedule new audit visit
    async scheduleAuditVisit(data) {
        try {
            const response = await frappe.call({
                method: 'frappe.client.insert',
                args: {
                    doc: {
                        doctype: 'Scheduled Audit Visit',
                        restaurant: data.restaurant,
                        auditor: data.auditor || frappe.session.user,
                        visit_date: data.visit_date,
                        status: 'Pending'
                    }
                }
            });
            return response.message;
        } catch (error) {
            console.error('Error scheduling audit visit:', error);
            frappe.msgprint({
                title: 'Error',
                message: 'Failed to schedule audit visit. Please try again.',
                indicator: 'red'
            });
            throw error;
        }
    }

    // Get scheduled visits for current user
    async getMyScheduledVisits(filters = {}) {
        try {
            const response = await frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Scheduled Audit Visit',
                    fields: [
                        'name', 'restaurant', 'visit_date', 'status', 
                        'week_start_date', 'week_end_date', 'creation'
                    ],
                    filters: {
                        auditor: frappe.session.user,
                        ...filters
                    },
                    order_by: 'visit_date desc'
                }
            });
            return response.message || [];
        } catch (error) {
            console.error('Error fetching scheduled visits:', error);
            return [];
        }
    }

    // Get current week's visits
    async getCurrentWeekVisits() {
        const today = new Date();
        const monday = new Date(today.setDate(today.getDate() - today.getDay() + 1));
        const sunday = new Date(today.setDate(today.getDate() - today.getDay() + 7));
        
        return await this.getMyScheduledVisits({
            visit_date: ['between', [
                monday.toISOString().split('T')[0],
                sunday.toISOString().split('T')[0]
            ]]
        });
    }

    // Get all restaurants
    async getRestaurants() {
        try {
            const response = await frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Restaurant',
                    fields: ['name', 'restaurant_name', 'location', 'status'],
                    filters: {
                        status: 'Active'
                    }
                }
            });
            return response.message || [];
        } catch (error) {
            console.error('Error fetching restaurants:', error);
            return [];
        }
    }

    // Mark visit as completed
    async completeVisit(visitName, auditData = {}) {
        try {
            const response = await frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: 'Scheduled Audit Visit',
                    name: visitName,
                    fieldname: {
                        status: 'Completed',
                        completed_date: frappe.datetime.now_datetime(),
                        ...auditData
                    }
                }
            });
            return response.message;
        } catch (error) {
            console.error('Error completing visit:', error);
            throw error;
        }
    }

    // Get audit statistics
    async getAuditStats(filters = {}) {
        try {
            const response = await frappe.call({
                method: 'restaurant_audit.api.get_audit_statistics',
                args: {
                    filters: filters
                }
            });
            return response.message || {};
        } catch (error) {
            console.error('Error fetching audit stats:', error);
            return {};
        }
    }

    // Get overdue audits
    async getOverdueAudits() {
        return await this.getMyScheduledVisits({
            status: 'Overdue'
        });
    }

    // Reschedule visit
    async rescheduleVisit(visitName, newDate) {
        try {
            const response = await frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: 'Scheduled Audit Visit',
                    name: visitName,
                    fieldname: {
                        visit_date: newDate,
                        status: 'Pending'
                    }
                }
            });
            return response.message;
        } catch (error) {
            console.error('Error rescheduling visit:', error);
            throw error;
        }
    }

    // Cancel scheduled visit
    async cancelVisit(visitName, reason = '') {
        try {
            const response = await frappe.call({
                method: 'frappe.client.set_value',
                args: {
                    doctype: 'Scheduled Audit Visit',
                    name: visitName,
                    fieldname: {
                        status: 'Cancelled',
                        cancellation_reason: reason
                    }
                }
            });
            return response.message;
        } catch (error) {
            console.error('Error cancelling visit:', error);
            throw error;
        }
    }

    // Get notifications for current user
    async getNotifications() {
        try {
            const response = await frappe.call({
                method: 'restaurant_audit.api.get_user_notifications',
                args: {}
            });
            return response.message || [];
        } catch (error) {
            console.error('Error fetching notifications:', error);
            return [];
        }
    }

    // Mark notification as read
    async markNotificationRead(notificationId) {
        try {
            const response = await frappe.call({
                method: 'restaurant_audit.api.mark_notification_read',
                args: {
                    notification_id: notificationId
                }
            });
            return response.message;
        } catch (error) {
            console.error('Error marking notification as read:', error);
            throw error;
        }
    }
}

// UI Controller for Restaurant Audit
class AuditUIController {
    constructor() {
        this.api = new AuditAPI();
        this.currentTab = 'regular';
        this.restaurants = [];
        this.scheduledVisits = [];
        this.init();
    }

    async init() {
        await this.loadInitialData();
        this.bindEvents();
        this.renderUI();
    }

    async loadInitialData() {
        try {
            // Load restaurants and scheduled visits in parallel
            const [restaurants, visits, stats] = await Promise.all([
                this.api.getRestaurants(),
                this.api.getCurrentWeekVisits(),
                this.api.getAuditStats()
            ]);

            this.restaurants = restaurants;
            this.scheduledVisits = visits;
            this.stats = stats;
        } catch (error) {
            console.error('Error loading initial data:', error);
            frappe.msgprint('Error loading data. Please refresh the page.');
        }
    }

    bindEvents() {
        // Tab switching
        $(document).on('click', '.tab-button', (e) => {
            const tabId = $(e.target).data('tab');
            this.switchTab(tabId);
        });

        // Schedule visit form
        $(document).on('submit', '#schedule-visit-form', (e) => {
            e.preventDefault();
            this.handleScheduleVisit(e);
        });

        // Individual restaurant scheduling
        $(document).on('click', '.schedule-btn', (e) => {
            const restaurantId = $(e.target).data('restaurant-id');
            this.showScheduleModal(restaurantId);
        });

        // Complete visit
        $(document).on('click', '.complete-visit-btn', (e) => {
            const visitId = $(e.target).data('visit-id');
            this.completeVisit(visitId);
        });

        // Reschedule visit
        $(document).on('click', '.reschedule-btn', (e) => {
            const visitId = $(e.target).data('visit-id');
            this.showRescheduleModal(visitId);
        });

        // Cancel visit
        $(document).on('click', '.cancel-visit-btn', (e) => {
            const visitId = $(e.target).data('visit-id');
            this.cancelVisit(visitId);
        });

        // Refresh data
        $(document).on('click', '.refresh-btn', () => {
            this.refreshData();
        });
    }

    switchTab(tabId) {
        this.currentTab = tabId;
        $('.tab-button').removeClass('active');
        $(`.tab-button[data-tab="${tabId}"]`).addClass('active');
        
        $('.tab-content').removeClass('active');
        $(`#${tabId}-tab`).addClass('active');
    }

    async handleScheduleVisit(e) {
        const formData = new FormData(e.target);
        const visitData = {
            restaurant: formData.get('restaurant'),
            visit_date: formData.get('visit_date'),
            auditor: formData.get('auditor') || frappe.session.user
        };

        try {
            await this.api.scheduleAuditVisit(visitData);
            frappe.msgprint({
                title: 'Success',
                message: 'Audit visit scheduled successfully!',
                indicator: 'green'
            });
            
            // Reset form and refresh data
            e.target.reset();
            await this.refreshData();
        } catch (error) {
            // Error handling is done in the API method
        }
    }

    showScheduleModal(restaurantId) {
        const restaurant = this.restaurants.find(r => r.name === restaurantId);
        if (!restaurant) return;

        const modal = $(`
            <div class="modal fade" id="scheduleModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Schedule Audit for ${restaurant.restaurant_name}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <form id="modal-schedule-form">
                            <div class="modal-body">
                                <input type="hidden" name="restaurant" value="${restaurantId}">
                                <div class="mb-3">
                                    <label class="form-label">Visit Date</label>
                                    <input type="date" class="form-control" name="visit_date" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Notes (Optional)</label>
                                    <textarea class="form-control" name="notes" rows="3"></textarea>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-primary">Schedule Visit</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `);

        $('body').append(modal);
        $('#scheduleModal').modal('show');

        $('#modal-schedule-form').on('submit', async (e) => {
            e.preventDefault();
            await this.handleScheduleVisit(e);
            $('#scheduleModal').modal('hide');
            $('#scheduleModal').remove();
        });

        $('#scheduleModal').on('hidden.bs.modal', () => {
            $('#scheduleModal').remove();
        });
    }

    async completeVisit(visitId) {
        try {
            await this.api.completeVisit(visitId);
            frappe.msgprint({
                title: 'Success',
                message: 'Visit marked as completed!',
                indicator: 'green'
            });
            await this.refreshData();
        } catch (error) {
            frappe.msgprint({
                title: 'Error',
                message: 'Failed to complete visit. Please try again.',
                indicator: 'red'
            });
        }
    }

    showRescheduleModal(visitId) {
        const visit = this.scheduledVisits.find(v => v.name === visitId);
        if (!visit) return;

        const modal = $(`
            <div class="modal fade" id="rescheduleModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Reschedule Visit</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <form id="reschedule-form">
                            <div class="modal-body">
                                <div class="mb-3">
                                    <label class="form-label">New Visit Date</label>
                                    <input type="date" class="form-control" name="new_date" value="${visit.visit_date}" required>
                                </div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button type="submit" class="btn btn-primary">Reschedule</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `);

        $('body').append(modal);
        $('#rescheduleModal').modal('show');

        $('#reschedule-form').on('submit', async (e) => {
            e.preventDefault();
            const newDate = $(e.target).find('[name="new_date"]').val();
            try {
                await this.api.rescheduleVisit(visitId, newDate);
                frappe.msgprint({
                    title: 'Success',
                    message: 'Visit rescheduled successfully!',
                    indicator: 'green'
                });
                await this.refreshData();
                $('#rescheduleModal').modal('hide');
            } catch (error) {
                frappe.msgprint({
                    title: 'Error',
                    message: 'Failed to reschedule visit. Please try again.',
                    indicator: 'red'
                });
            }
        });

        $('#rescheduleModal').on('hidden.bs.modal', () => {
            $('#rescheduleModal').remove();
        });
    }

    async cancelVisit(visitId) {
        frappe.confirm('Are you sure you want to cancel this visit?', async () => {
            try {
                await this.api.cancelVisit(visitId);
                frappe.msgprint({
                    title: 'Success',
                    message: 'Visit cancelled successfully!',
                    indicator: 'green'
                });
                await this.refreshData();
            } catch (error) {
                frappe.msgprint({
                    title: 'Error',
                    message: 'Failed to cancel visit. Please try again.',
                    indicator: 'red'
                });
            }
        });
    }

    async refreshData() {
        await this.loadInitialData();
        this.renderScheduledVisitsTable();
        this.renderRestaurantCards();
        this.renderStats();
    }

    renderUI() {
        this.renderScheduledVisitsTable();
        this.renderRestaurantCards();
        this.renderStats();
        this.renderRestaurantDropdown();
    }

    renderScheduledVisitsTable() {
        const tableBody = $('#scheduled-visits-table tbody');
        tableBody.empty();

        if (this.scheduledVisits.length === 0) {
            tableBody.append('<tr><td colspan="5" class="text-center">No scheduled visits for this week</td></tr>');
            return;
        }

        this.scheduledVisits.forEach(visit => {
            const statusClass = this.getStatusClass(visit.status);
            const actionButtons = this.getActionButtons(visit);
            
            const row = $(`
                <tr>
                    <td>${visit.restaurant}</td>
                    <td>${frappe.datetime.str_to_user(visit.visit_date)}</td>
                    <td><span class="badge ${statusClass}">${visit.status}</span></td>
                    <td>${frappe.datetime.str_to_user(visit.creation)}</td>
                    <td>${actionButtons}</td>
                </tr>
            `);
            tableBody.append(row);
        });
    }

    renderRestaurantCards() {
        const container = $('#restaurant-cards-container');
        container.empty();

        this.restaurants.forEach(restaurant => {
            const card = $(`
                <div class="col-md-4 mb-3">
                    <div class="card restaurant-card">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <h6 class="card-title">${restaurant.restaurant_name}</h6>
                                    <p class="card-text text-muted">${restaurant.location || ''}</p>
                                </div>
                                <button class="btn btn-outline-primary btn-sm schedule-btn" 
                                        data-restaurant-id="${restaurant.name}">
                                    <i class="fa fa-plus"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `);
            container.append(card);
        });
    }

    renderStats() {
        if (!this.stats) return;

        $('#total-visits').text(this.stats.total_visits || 0);
        $('#completed-visits').text(this.stats.completed_visits || 0);
        $('#pending-visits').text(this.stats.pending_visits || 0);
        $('#overdue-visits').text(this.stats.overdue_visits || 0);
    }

    renderRestaurantDropdown() {
        const select = $('#restaurant-select');
        select.empty();
        select.append('<option value="">Select Restaurant</option>');
        
        this.restaurants.forEach(restaurant => {
            select.append(`<option value="${restaurant.name}">${restaurant.restaurant_name}</option>`);
        });
    }

    getStatusClass(status) {
        const statusClasses = {
            'Pending': 'bg-warning',
            'Completed': 'bg-success',
            'Overdue': 'bg-danger',
            'Cancelled': 'bg-secondary'
        };
        return statusClasses[status] || 'bg-secondary';
    }

    getActionButtons(visit) {
        if (visit.status === 'Completed') {
            return '<span class="text-muted">Completed</span>';
        }

        return `
            <div class="btn-group btn-group-sm">
                <button class="btn btn-success complete-visit-btn" data-visit-id="${visit.name}">
                    <i class="fa fa-check"></i> Complete
                </button>
                <button class="btn btn-outline-primary reschedule-btn" data-visit-id="${visit.name}">
                    <i class="fa fa-calendar"></i> Reschedule
                </button>
                <button class="btn btn-outline-danger cancel-visit-btn" data-visit-id="${visit.name}">
                    <i class="fa fa-times"></i> Cancel
                </button>
            </div>
        `;
    }
}

// Initialize the audit controller when the page loads
$(document).ready(() => {
    window.auditController = new AuditUIController();
});

// Export for use in other files
window.AuditAPI = AuditAPI;
window.AuditUIController = AuditUIController;