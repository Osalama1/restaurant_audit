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
        restaurant_exists = frappe.db.get_value("Restaurant", restaurant, "name")
        if not restaurant_exists:
            return {
                "success": False,
                "message": "Restaurant not found"
            }
        
        # Check if visit already scheduled for this date
        existing_visit = frappe.db.get_value("Scheduled Audit Visit", {
            "restaurant": restaurant,
            "auditor": current_user,
            "visit_date": visit_date
        }, "name")
        
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
            restaurant.has_progress = frappe.db.get_value("Audit Progress", {
                "restaurant": restaurant.name,
                "auditor": current_user,
                "is_completed": 0
            }, "name") is not None
        
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

@frappe.whitelist()
def get_daily_audit_questions(template_name, restaurant=None):
    """Get daily audit questions from Checklist Category with is_daily_audit = 1"""
    try:
        # Get the template
        template = frappe.get_doc("Daily Audit Template", template_name)
        
        if not template.is_currently_open():
            return {
                "success": False,
                "message": "Template is currently closed",
                "questions": []
            }
        
        # Get checklist categories with is_daily_audit = 1
        filters = {"is_daily_audit": 1}
        if restaurant and not template.applies_to_all_restaurants:
            filters["restaurant"] = restaurant
        
        categories = frappe.get_all("Checklist Category",
            filters=filters,
            fields=["name", "category_name", "restaurant", "template", "overall_category_comment"]
        )
        
        questions_data = []
        for category in categories:
            # Get questions for this category
            category_doc = frappe.get_doc("Checklist Category", category.name)
            
            category_questions = []
            for question_row in category_doc.questions:
                question_doc = frappe.get_doc("Audit Question", question_row.question)
                category_questions.append({
                    "name": question_doc.name,
                    "question_text": question_doc.question_text,
                    "answer_type": question_doc.answer_type,
                    "options": question_doc.options,
                    "allow_image_upload": question_doc.allow_image_upload,
                    "is_mandatory": question_doc.is_mandatory,
                    "question_comment": question_doc.question_comment
                })
            
            questions_data.append({
                "category": category,
                "questions": category_questions
            })
        
        return {
            "success": True,
            "template": {
                "name": template.name,
                "template_name": template.template_name,
                "description": template.description,
                "estimated_duration": template.estimated_duration
            },
            "questions_data": questions_data,
            "total_questions": sum(len(cat["questions"]) for cat in questions_data)
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting daily audit questions: {str(e)}", "Get Daily Audit Questions")
        return {
            "success": False,
            "message": f"Error loading questions: {str(e)}",
            "questions": []
        }

@frappe.whitelist()
def start_daily_audit(template_name, restaurant):
    """Start a daily audit session"""
    try:
        current_user = frappe.session.user
        
        # Get template and questions
        questions_response = get_daily_audit_questions(template_name, restaurant)
        
        if not questions_response["success"]:
            return questions_response
        
        # Create audit progress record
        progress = frappe.get_doc({
            "doctype": "Audit Progress",
            "restaurant": restaurant,
            "auditor": current_user,
            "start_time": frappe.utils.now(),
            "total_questions": questions_response["total_questions"],
            "answered_questions": 0,
            "completion_percentage": 0,
            "is_completed": 0,
            "answers_json": "{}",
            "category_progress": "{}"
        })
        
        progress.insert(ignore_permissions=True)
        
        # Update template last used date
        template = frappe.get_doc("Daily Audit Template", template_name)
        template.update_last_used()
        
        return {
            "success": True,
            "message": "Daily audit started successfully",
            "progress_id": progress.name,
            "questions_data": questions_response["questions_data"],
            "template": questions_response["template"]
        }
        
    except Exception as e:
        frappe.log_error(f"Error starting daily audit: {str(e)}", "Start Daily Audit")
        return {
            "success": False,
            "message": f"Error starting audit: {str(e)}"
        }