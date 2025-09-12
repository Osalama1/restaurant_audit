# Copyright (c) 2025, Restaurant Audit App and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days, nowdate
from datetime import datetime, timedelta

def get_week_start_for_employee(employee_id, reference_date=None):
    """
    Get the week start date for an employee based on their start_week_day preference
    """
    if not reference_date:
        reference_date = getdate()
    
    # Get employee's start_week_day from Restaurant Employee table
    employee_week_start = frappe.db.get_value("Restaurant Employee", 
        {"employee": employee_id, "is_active": 1}, 
        "start_week_day"
    )
    
    if not employee_week_start:
        # Default to Monday if not set
        employee_week_start = "Monday"
    
    # Map day names to weekday numbers (Monday=0, Sunday=6)
    day_mapping = {
        "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
        "Friday": 4, "Saturday": 5, "Sunday": 6
    }
    
    target_weekday = day_mapping.get(employee_week_start, 0)
    current_weekday = reference_date.weekday()
    
    # Calculate days to subtract to get to the start of the week
    days_to_subtract = (current_weekday - target_weekday) % 7
    
    return add_days(reference_date, -days_to_subtract)

def get_week_end_for_employee(employee_id, week_start):
    """
    Get the week end date for an employee (6 days after week start)
    """
    return add_days(week_start, 6)

def check_weekly_audits():
    """
    Weekly scheduled job to check for restaurants without completed audits
    and send notifications to auditors and restaurant managers
    """
    try:
        today = getdate()
        
        # Get all active restaurants with their assigned employees
        restaurants = frappe.get_all("Restaurant", 
            filters={"disabled": 0}, 
            fields=["name", "restaurant_name", "restaurant_manager"]
        )
        
        for restaurant in restaurants:
            # Get all active employees for this restaurant
            assigned_employees = frappe.get_all("Restaurant Employee",
                filters={
                    "parent": restaurant.name,
                    "is_active": 1
                },
                fields=["employee", "start_week_day"]
            )
            
            if not assigned_employees:
                continue
                
            # Group employees by their week start day
            employees_by_week_start = {}
            for emp in assigned_employees:
                week_start_day = emp.start_week_day or "Monday"
                if week_start_day not in employees_by_week_start:
                    employees_by_week_start[week_start_day] = []
                employees_by_week_start[week_start_day].append(emp.employee)
            
            # Check each week start day group
            for week_start_day, employee_list in employees_by_week_start.items():
                # Calculate week start and end for this group
                week_start = get_week_start_for_employee(employee_list[0], today)
                week_end = get_week_end_for_employee(employee_list[0], week_start)
                
                # Check if any employee has completed audit for this week
                completed_audits = frappe.get_all("Scheduled Audit Visit",
                    filters={
                        "restaurant": restaurant.name,
                        "status": "Completed",
                        "week_start_date": week_start,
                        "week_end_date": week_end
                    }
                )
                
                if not completed_audits:
                    # No completed audit found, send alerts to this group
                    send_audit_alerts_for_employees(restaurant, employee_list, week_start, week_end)
                    
                    # Mark pending audits as overdue for this group
                    mark_pending_audits_overdue(restaurant.name, week_start, week_end)
                
    except Exception as e:
        frappe.log_error(f"Error in check_weekly_audits: {str(e)}", "Weekly Audit Check")

def send_audit_alerts_for_employees(restaurant, employee_list, week_start, week_end):
    """Send alerts to specific employees and restaurant manager for missing audits"""
    try:
        auditor_emails = []
        for employee_id in employee_list:
            employee_doc = frappe.get_doc("Employee", employee_id)
            if employee_doc.user_id:
                user_doc = frappe.get_doc("User", employee_doc.user_id)
                if user_doc.email:
                    auditor_emails.append(user_doc.email)
        
        # Get restaurant manager email
        manager_email = None
        if restaurant.restaurant_manager:
            manager_doc = frappe.get_doc("Employee", restaurant.restaurant_manager)
            if manager_doc.user_id:
                manager_user = frappe.get_doc("User", manager_doc.user_id)
                if manager_user.email:
                    manager_email = manager_user.email
        
        # Prepare email content
        subject = f"Weekly Audit Alert: {restaurant.restaurant_name}"
        message = f"""
        <h3>Weekly Audit Alert</h3>
        <p>Restaurant <strong>{restaurant.restaurant_name}</strong> has not had a completed audit for the week of {week_start} to {week_end}.</p>
        <p>Please schedule and complete an audit as soon as possible.</p>
        <p>This is an automated notification from the Restaurant Audit System.</p>
        """
        
        # Send emails to auditors
        for email in auditor_emails:
            try:
                frappe.sendmail(
                    recipients=[email],
                    subject=subject,
                    message=message,
                    header=[subject, "red"]
                )
                
                # Create in-app notification
                frappe.get_doc({
                    "doctype": "Notification Log",
                    "subject": subject,
                    "email_content": message,
                    "for_user": frappe.db.get_value("User", {"email": email}, "name"),
                    "type": "Alert"
                }).insert(ignore_permissions=True)
                
            except Exception as e:
                frappe.log_error(f"Error sending email to auditor {email}: {str(e)}", "Audit Alert Email")
        
        # Send email to restaurant manager
        if manager_email:
            try:
                frappe.sendmail(
                    recipients=[manager_email],
                    subject=subject,
                    message=message,
                    header=[subject, "red"]
                )
                
                # Create in-app notification
                frappe.get_doc({
                    "doctype": "Notification Log",
                    "subject": subject,
                    "email_content": message,
                    "for_user": frappe.db.get_value("User", {"email": manager_email}, "name"),
                    "type": "Alert"
                }).insert(ignore_permissions=True)
                
            except Exception as e:
                frappe.log_error(f"Error sending email to manager {manager_email}: {str(e)}", "Audit Alert Email")
                
    except Exception as e:
        frappe.log_error(f"Error in send_audit_alerts_for_employees: {str(e)}", "Audit Alert System")

def send_audit_alerts(restaurant, week_start, week_end):
    """Legacy function - kept for backward compatibility"""
    # Get all active employees for this restaurant
    assigned_employees = frappe.get_all("Restaurant Employee",
        filters={
            "parent": restaurant.name,
            "is_active": 1
        },
        fields=["employee"]
    )
    
    employee_list = [emp.employee for emp in assigned_employees]
    send_audit_alerts_for_employees(restaurant, employee_list, week_start, week_end)

def mark_pending_audits_overdue(restaurant_name, week_start, week_end):
    """Mark pending scheduled audits as overdue for the current week"""
    try:
        pending_audits = frappe.get_all("Scheduled Audit Visit",
            filters={
                "restaurant": restaurant_name,
                "status": "Pending",
                "week_start_date": week_start,
                "week_end_date": week_end
            }
        )
        
        for audit in pending_audits:
            audit_doc = frappe.get_doc("Scheduled Audit Visit", audit.name)
            audit_doc.status = "Overdue"
            audit_doc.overdue_notified = 1
            audit_doc.save(ignore_permissions=True)
            
    except Exception as e:
        frappe.log_error(f"Error marking audits overdue: {str(e)}", "Mark Audits Overdue")

def cleanup_employee_data(employee_id, restaurant_id):
    """
    Clean up all data related to an employee when they are removed from a restaurant
    """
    try:
        # Get employee's user ID
        employee_doc = frappe.get_doc("Employee", employee_id)
        user_id = employee_doc.user_id if employee_doc.user_id else None
        
        # 1. Cancel/Delete pending scheduled audit visits for this employee and restaurant
        pending_visits = frappe.get_all("Scheduled Audit Visit",
            filters={
                "restaurant": restaurant_id,
                "auditor": user_id,
                "status": ["in", ["Pending", "Overdue"]]
            }
        )
        
        for visit in pending_visits:
            try:
                visit_doc = frappe.get_doc("Scheduled Audit Visit", visit.name)
                visit_doc.status = "Cancelled"
                visit_doc.add_comment("Comment", f"Automatically cancelled due to employee removal from restaurant")
                visit_doc.save(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Error cancelling visit {visit.name}: {str(e)}", "Employee Cleanup")
        
        # 2. Delete incomplete audit submissions for this employee and restaurant
        incomplete_submissions = frappe.get_all("Audit Submission",
            filters={
                "restaurant": restaurant_id,
                "auditor": user_id,
                "docstatus": 0  # Draft status
            }
        )
        
        for submission in incomplete_submissions:
            try:
                frappe.delete_doc("Audit Submission", submission.name, ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Error deleting submission {submission.name}: {str(e)}", "Employee Cleanup")
        
        # 3. Clean up notification logs related to this employee and restaurant
        notification_logs = frappe.get_all("Notification Log",
            filters={
                "for_user": user_id,
                "subject": ["like", f"%{restaurant_id}%"]
            }
        )
        
        for notification in notification_logs:
            try:
                frappe.delete_doc("Notification Log", notification.name, ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Error deleting notification {notification.name}: {str(e)}", "Employee Cleanup")
        
        # 4. Clean up any audit progress data in localStorage (this would need to be handled on frontend)
        # We'll add a note to the employee record for frontend cleanup
        
        # 5. Log the cleanup action
        frappe.get_doc({
            "doctype": "Comment",
            "reference_doctype": "Restaurant",
            "reference_name": restaurant_id,
            "content": f"Employee {employee_id} removed from restaurant. All related data has been cleaned up.",
            "comment_type": "Info"
        }).insert(ignore_permissions=True)
        
        frappe.msgprint(f"Successfully cleaned up all data for employee {employee_id} from restaurant {restaurant_id}")
        
    except Exception as e:
        frappe.log_error(f"Error in cleanup_employee_data: {str(e)}", "Employee Cleanup")
        frappe.throw(f"Error cleaning up employee data: {str(e)}")

def cleanup_employee_on_removal(restaurant_name, employee_id):
    """
    Wrapper function to be called when an employee is removed from a restaurant
    """
    try:
        cleanup_employee_data(employee_id, restaurant_name)
    except Exception as e:
        frappe.log_error(f"Error in cleanup_employee_on_removal: {str(e)}", "Employee Removal Cleanup")