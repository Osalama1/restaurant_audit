# Copyright (c) 2025, Restaurant Audit App and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days, nowdate
from datetime import datetime, timedelta

def check_weekly_audits():
    """
    Weekly scheduled job to check for restaurants without completed audits
    and send notifications to auditors and restaurant managers
    """
    try:
        # Get current week start (Monday) and end (Sunday)
        today = getdate()
        days_since_monday = today.weekday()
        week_start = add_days(today, -days_since_monday)
        week_end = add_days(week_start, 6)
        
        # Get all active restaurants
        restaurants = frappe.get_all("Restaurant", 
            filters={"disabled": 0}, 
            fields=["name", "restaurant_name", "restaurant_manager"]
        )
        
        for restaurant in restaurants:
            # Check if restaurant has completed audit for current week
            completed_audits = frappe.get_all("Scheduled Audit Visit",
                filters={
                    "restaurant": restaurant.name,
                    "status": "Completed",
                    "week_start_date": week_start,
                    "week_end_date": week_end
                }
            )
            
            if not completed_audits:
                # No completed audit found, send alerts
                send_audit_alerts(restaurant, week_start, week_end)
                
                # Mark pending audits as overdue
                mark_pending_audits_overdue(restaurant.name, week_start, week_end)
                
    except Exception as e:
        frappe.log_error(f"Error in check_weekly_audits: {str(e)}", "Weekly Audit Check")

def send_audit_alerts(restaurant, week_start, week_end):
    """Send alerts to auditors and restaurant manager for missing audits"""
    try:
        # Get assigned auditors for this restaurant
        assigned_employees = frappe.get_all("Restaurant Employee",
            filters={
                "parent": restaurant.name,
                "is_active": 1
            },
            fields=["employee"]
        )
        
        auditor_emails = []
        for emp in assigned_employees:
            employee_doc = frappe.get_doc("Employee", emp.employee)
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
        frappe.log_error(f"Error in send_audit_alerts: {str(e)}", "Audit Alert System")

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