# Copyright (c) 2025, Restaurant Audit App and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days, nowdate, get_weekday
from datetime import datetime, timedelta

@frappe.whitelist()
def schedule_audit_visit(restaurant, visit_date):
    """Create a new scheduled audit visit"""
    try:
        # Get current user
        current_user = frappe.session.user
        
        # Validate inputs
        if not restaurant or not visit_date:
            return {
                "success": False,
                "message": "Restaurant and visit date are required"
            }
        
        # Check if restaurant exists
        if not frappe.db.exists("Restaurant", restaurant):
            return {
                "success": False,
                "message": "Restaurant not found"
            }
        
        # Check if visit already scheduled for this date
        existing_visit = frappe.db.exists("Scheduled Audit Visit", {
            "restaurant": restaurant,
            "auditor": current_user,
            "visit_date": visit_date
        })
        
        if existing_visit:
            return {
                "success": False,
                "message": "Visit already scheduled for this date"
            }
        
        # Create new scheduled visit
        scheduled_visit = frappe.get_doc({
            "doctype": "Scheduled Audit Visit",
            "restaurant": restaurant,
            "auditor": current_user,
            "visit_date": visit_date,
            "status": "Pending"
        })
        
        scheduled_visit.insert(ignore_permissions=True)
        
        return {
            "success": True,
            "message": "Audit visit scheduled successfully",
            "visit_id": scheduled_visit.name
        }
        
    except Exception as e:
        frappe.log_error(f"Error scheduling audit visit: {str(e)}", "Schedule Audit Visit")
        return {
            "success": False,
            "message": f"Error scheduling visit: {str(e)}"
        }

@frappe.whitelist()
def get_scheduled_audits():
    """Get all scheduled audits for current user"""
    try:
        current_user = frappe.session.user
        
        # Get scheduled audits for current user
        scheduled_audits = frappe.get_all("Scheduled Audit Visit",
            filters={"auditor": current_user},
            fields=[
                "name", "restaurant", "restaurant_name", "visit_date", 
                "status", "week_start_date", "week_end_date"
            ],
            order_by="visit_date asc"
        )
        
        return {
            "success": True,
            "scheduled_audits": scheduled_audits
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting scheduled audits: {str(e)}", "Get Scheduled Audits")
        return {
            "success": False,
            "message": f"Error loading scheduled audits: {str(e)}",
            "scheduled_audits": []
        }

@frappe.whitelist()
def get_my_scheduled_visits():
    """Get current user's scheduled visits for the current week"""
    try:
        current_user = frappe.session.user
        
        # Get current week start and end
        today = getdate()
        days_since_monday = today.weekday()
        week_start = add_days(today, -days_since_monday)
        week_end = add_days(week_start, 6)
        
        # Get scheduled visits for current week
        visits = frappe.get_all("Scheduled Audit Visit",
            filters={
                "auditor": current_user,
                "week_start_date": week_start,
                "week_end_date": week_end
            },
            fields=[
                "name", "restaurant_name", "visit_date", "status"
            ],
            order_by="visit_date asc"
        )
        
        return {
            "success": True,
            "visits": visits,
            "week_start": week_start,
            "week_end": week_end
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting my scheduled visits: {str(e)}", "Get My Scheduled Visits")
        return {
            "success": False,
            "message": f"Error loading visits: {str(e)}",
            "visits": []
        }

@frappe.whitelist()
def get_scheduled_visits_by_week(week_start=None):
    """Get scheduled visits for a specific week"""
    try:
        current_user = frappe.session.user
        
        # If no week_start provided, use current week
        if not week_start:
            today = getdate()
            days_since_monday = today.weekday()
            week_start = add_days(today, -days_since_monday)
        else:
            week_start = getdate(week_start)
        
        week_end = add_days(week_start, 6)
        
        # Get scheduled visits for the specified week
        visits = frappe.get_all("Scheduled Audit Visit",
            filters={
                "auditor": current_user,
                "visit_date": ["between", [week_start, week_end]]
            },
            fields=[
                "name", "restaurant", "restaurant_name", "visit_date", 
                "status", "week_start_date", "week_end_date"
            ],
            order_by="visit_date asc"
        )
        
        return {
            "success": True,
            "visits": visits,
            "week_start": week_start,
            "week_end": week_end,
            "week_label": f"{week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}"
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting visits by week: {str(e)}", "Get Visits By Week")
        return {
            "success": False,
            "message": f"Error loading visits: {str(e)}",
            "visits": []
        }

@frappe.whitelist()
def get_restaurants():
    """Get restaurants assigned to current user"""
    try:
        current_user = frappe.session.user
        
        # Get employee record for current user
        employee = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
        
        if not employee:
            return {
                "success": True,
                "restaurants": [],
                "message": "No employee record found for current user"
            }
        
        # Get restaurants assigned to this employee
        assigned_restaurants = frappe.get_all("Restaurant Employee",
            filters={"employee": employee, "is_active": 1},
            fields=["parent"]
        )
        
        if not assigned_restaurants:
            return {
                "success": True,
                "restaurants": [],
                "message": "No restaurants assigned to this employee"
            }
        
        restaurant_ids = [r.parent for r in assigned_restaurants]
        
        # Get restaurant details
        restaurants = frappe.get_all("Restaurant",
            filters={"name": ["in", restaurant_ids]},
            fields=[
                "name", "restaurant_name", "address", "latitude", "longitude",
                "location_radius", "restaurant_manager"
            ]
        )
        
        # Add additional data for each restaurant
        for restaurant in restaurants:
            # Get last audit date
            last_audit = frappe.db.get_value("Audit Submission",
                filters={"restaurant": restaurant.name},
                fieldname="audit_date",
                order_by="audit_date desc"
            )
            
            restaurant.last_audit_date = last_audit
            
            # Get total audits count
            restaurant.total_audits = frappe.db.count("Audit Submission",
                filters={"restaurant": restaurant.name}
            )
            
            # Get my audits count
            restaurant.my_audits = frappe.db.count("Audit Submission",
                filters={"restaurant": restaurant.name, "auditor": current_user}
            )
            
            # Check for pending progress
            restaurant.has_progress = frappe.db.exists("Audit Progress",
                filters={
                    "restaurant": restaurant.name,
                    "auditor": current_user,
                    "is_completed": 0
                }
            )
        
        return {
            "success": True,
            "restaurants": restaurants
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting restaurants: {str(e)}", "Get Restaurants")
        return {
            "success": False,
            "message": f"Error loading restaurants: {str(e)}",
            "restaurants": []
        }

@frappe.whitelist()
def get_daily_templates(restaurant=None):
    """Get daily audit templates for a restaurant or all templates"""
    try:
        # Import the function from the DocType
        from restaurant_audit.restaurant_audit.doctype.daily_audit_template.daily_audit_template import get_active_templates
        
        templates = get_active_templates(restaurant)
        
        return {
            "success": True,
            "templates": templates
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting daily templates: {str(e)}", "Get Daily Templates")
        return {
            "success": False,
            "message": f"Error loading templates: {str(e)}",
            "templates": []
        }

@frappe.whitelist()
def get_template_status(template_name):
    """Get current status of a daily audit template"""
    try:
        from restaurant_audit.restaurant_audit.doctype.daily_audit_template.daily_audit_template import get_template_status
        
        status = get_template_status(template_name)
        
        return {
            "success": True,
            "status": status
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting template status: {str(e)}", "Get Template Status")
        return {
            "success": False,
            "message": f"Error getting template status: {str(e)}"
        }

@frappe.whitelist()
def get_user_dashboard():
    """Get dashboard data for current user"""
    try:
        current_user = frappe.session.user
        
        # Get user details
        user_doc = frappe.get_doc("User", current_user)
        
        # Get employee record
        employee = frappe.db.get_value("Employee", {"user_id": current_user}, 
            ["name", "employee_name", "designation"], as_dict=True)
        
        # Get audit statistics
        total_audits = frappe.db.count("Audit Submission", {"auditor": current_user})
        
        # Get average score
        avg_score_result = frappe.db.sql("""
            SELECT AVG(average_score) as avg_score 
            FROM `tabAudit Submission` 
            WHERE auditor = %s AND average_score IS NOT NULL
        """, (current_user,))
        
        avg_score = avg_score_result[0][0] if avg_score_result and avg_score_result[0][0] else 0
        
        # Get pending progress
        pending_progress = frappe.get_all("Audit Progress",
            filters={"auditor": current_user, "is_completed": 0},
            fields=["name", "restaurant", "completion_percentage"]
        )
        
        return {
            "success": True,
            "dashboard": {
                "user": {
                    "name": current_user,
                    "full_name": user_doc.full_name,
                    "email": user_doc.email
                },
                "employee": employee,
                "stats": {
                    "total_audits": total_audits,
                    "avg_score": round(avg_score, 1) if avg_score else 0
                },
                "pending_progress": pending_progress
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting user dashboard: {str(e)}", "Get User Dashboard")
        return {
            "success": False,
            "message": f"Error loading dashboard: {str(e)}"
        }