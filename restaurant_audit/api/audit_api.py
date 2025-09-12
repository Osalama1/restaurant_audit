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

# Replace get_restaurants method in audit_api.py with this enhanced version

@frappe.whitelist()
def get_restaurants():
    """Get restaurants assigned to current user - with status checking"""
    try:
        current_user = frappe.session.user
        
        # Check if User is enabled in ERPNext
        user_enabled = frappe.db.get_value("User", current_user, "enabled")
        if not user_enabled:
            return {
                "success": True,
                "restaurants": [],
                "message": "User account is disabled"
            }
        
        # Get employee record for current user
        employee = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
        
        if not employee:
            return {
                "success": True,
                "restaurants": [],
                "message": "No employee record found for current user"
            }
        
        # Check if Employee is active in ERPNext
        employee_status = frappe.db.get_value("Employee", employee, "status")
        if employee_status != "Active":
            return {
                "success": True,
                "restaurants": [],
                "message": f"Employee status is {employee_status}"
            }
        
        # Get restaurants assigned to this employee
        assigned_restaurants = frappe.get_all("Restaurant Employee",
            filters={"employee": employee},
            fields=["parent", "is_active", "employee_status"]
        )
        
        if not assigned_restaurants:
            return {
                "success": True,
                "restaurants": [],
                "message": "No restaurants assigned to this employee"
            }
        
        # Filter only active assignments
        active_restaurant_ids = [
            r.parent for r in assigned_restaurants 
            if r.is_active and r.employee_status == "Active"
        ]
        
        if not active_restaurant_ids:
            return {
                "success": True,
                "restaurants": [],
                "message": "No active restaurant assignments found"
            }
        
        # Get restaurant details
        restaurants = frappe.get_all("Restaurant",
            filters={"name": ["in", active_restaurant_ids]},
            fields=[
                "name", "restaurant_name", "address", "latitude", "longitude",
                "location_radius", "restaurant_manager"
            ]
        )
        
        # Add additional data for each restaurant
        for restaurant in restaurants:
            # Get employee details
            employee_doc = frappe.get_doc("Employee", employee)
            restaurant.employee_name = employee_doc.employee_name
            restaurant.designation = employee_doc.designation
            
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

# Add this method to check user can start audit
@frappe.whitelist()
def can_start_audit(restaurant_id):
    """Check if user can start audit - simple version"""
    try:
        current_user = frappe.session.user
        
        # Check User enabled
        user_enabled = frappe.db.get_value("User", current_user, "enabled")
        if not user_enabled:
            return {
                "success": False,
                "message": "Your user account is disabled"
            }
        
        # Check Employee active
        employee = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
        if employee:
            employee_status = frappe.db.get_value("Employee", employee, "status")
            if employee_status != "Active":
                return {
                    "success": False,
                    "message": f"Your employee status is {employee_status}"
                }
        
        # Check restaurant assignment status
        restaurant_assignment = frappe.db.get_value("Restaurant Employee", {
            "parent": restaurant_id,
            "employee": employee
        }, ["is_active", "employee_status"], as_dict=True)
        
        if not restaurant_assignment:
            return {
                "success": False,
                "message": "You are not assigned to this restaurant"
            }
        
        if not restaurant_assignment.is_active or restaurant_assignment.employee_status != "Active":
            return {
                "success": False,
                "message": f"Your assignment status is {restaurant_assignment.employee_status}"
            }
        
        # Check week completion
        week_status = check_restaurant_week_status(restaurant_id)
        if not week_status["success"]:
            return week_status
        
        if not week_status["can_access_audit"]:
            return {
                "success": False,
                "message": week_status["message"],
                "reason": "week_completed"
            }
        
        return {
            "success": True,
            "message": "You can start the audit for this restaurant."
        }
        
    except Exception as e:
        frappe.log_error(f"Error checking audit access: {str(e)}", "Audit Access Check")
        return {
            "success": False,
            "message": f"Error checking audit access: {str(e)}"
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

# Add these methods to your existing audit_api.py file

@frappe.whitelist()
def get_daily_audit_questions(template_name):
    """Get daily audit questions from Daily Audit Template's question_template"""
    try:
        # Get the template
        template = frappe.get_doc("Daily Audit Template", template_name)
        
        if not template.is_currently_open():
            return {
                "success": False,
                "message": "Template is currently closed",
                "questions": []
            }
        
        # Get the linked question template (Checklist Category)
        if not template.question_template:
            return {
                "success": False,
                "message": "No question template linked to this daily audit template",
                "questions": []
            }
        
        # Get the category document
        category_doc = frappe.get_doc("Checklist Category", template.question_template)
        
        # Verify it's a daily audit category
        if not category_doc.is_daily_audit:
            return {
                "success": False,
                "message": "Linked template is not configured for daily audit",
                "questions": []
            }
        
        # Get questions from the category
        category_questions = []
        if hasattr(category_doc, 'questions') and category_doc.questions:
            for question_row in category_doc.questions:
                category_questions.append({
                    "name": question_row.name,
                    "question_text": question_row.question_text,
                    "answer_type": question_row.answer_type,
                    "options": question_row.options.split(',') if question_row.options else [],
                    "allow_image_upload": question_row.allow_image_upload,
                    "is_mandatory": question_row.is_mandatory,
                    "question_comment": question_row.question_comment or ""
                })
        
        # Format as expected by frontend (same structure as regular audit)
        questions_data = [{
            "category": {
                "name": category_doc.name,
                "category_name": category_doc.category_name,
                "restaurant": category_doc.restaurant,
                "overall_category_comment": category_doc.overall_category_comment
            },
            "questions": category_questions
        }]
        
        return {
            "success": True,
            "template": {
                "name": template.name,
                "template_name": template.template_name,
                "description": template.description,
                "estimated_duration": template.estimated_duration
            },
            "questions_data": questions_data,
            "total_questions": len(category_questions)
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting daily audit questions: {str(e)}", "Get Daily Audit Questions")
        return {
            "success": False,
            "message": f"Error loading questions: {str(e)}",
            "questions": []
        }

# Fixed version - replace the start_daily_audit method in audit_api.py

@frappe.whitelist()
def start_daily_audit(template_name):
    """Start a daily audit session"""
    try:
        current_user = frappe.session.user
        
        # Get template first to determine restaurant
        template = frappe.get_doc("Daily Audit Template", template_name)
        
        if not template.is_currently_open():
            return {
                "success": False,
                "message": "Template is currently closed"
            }
        
        # Determine which restaurant to use
        restaurant = None
        
        if template.applies_to_all_restaurants:
            # If applies to all, get user's first assigned restaurant
            user_restaurants = get_restaurants()
            if user_restaurants["success"] and user_restaurants["restaurants"]:
                restaurant = user_restaurants["restaurants"][0]["name"]
        elif template.restaurant:
            # If template has specific restaurant, use that
            restaurant = template.restaurant
        else:
            # Fallback: get user's first assigned restaurant
            user_restaurants = get_restaurants()
            if user_restaurants["success"] and user_restaurants["restaurants"]:
                restaurant = user_restaurants["restaurants"][0]["name"]
        
        if not restaurant:
            return {
                "success": False,
                "message": "No restaurant available for daily audit"
            }
        
        # Get template and questions
        questions_response = get_daily_audit_questions(template_name)
        
        if not questions_response["success"]:
            return questions_response
        
        # Get employee record
        employee = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
        
        # Create audit progress record
        progress = frappe.get_doc({
            "doctype": "Audit Progress",
            "restaurant": restaurant,
            "auditor": current_user,
            "employee": employee,
            "start_time": frappe.utils.now(),
            "last_updated": frappe.utils.now(),
            "is_completed": 0,
            "total_questions": questions_response["total_questions"],
            "answered_questions": 0,
            "completion_percentage": 0,
            "overall_comment": "",
            "answers_json": "{}",
            "category_progress": "{}"
        })
        
        progress.insert(ignore_permissions=True)
        
        # Update template last used date
        try:
            template.update_last_used()
        except:
            # If update_last_used method doesn't exist, just continue
            pass
        
        return {
            "success": True,
            "message": "Daily audit started successfully",
            "progress_id": progress.name,
            "questions_data": questions_response["questions_data"],
            "template": questions_response["template"],
            "restaurant": restaurant
        }
        
    except Exception as e:
        frappe.log_error(f"Error starting daily audit: {str(e)}", "Start Daily Audit")
        return {
            "success": False,
            "message": f"Error starting audit: {str(e)}"
        }
        # ONLY fix the API - don't change any doctypes
# This works with your existing Audit Question child table structure

@frappe.whitelist()
def get_checklist_template(restaurant_id):
    """Get checklist template for a restaurant"""
    try:
        # Get checklist categories for this restaurant
        categories = frappe.get_all("Checklist Category",
            filters={"restaurant": restaurant_id},
            fields=["name", "category_name", "restaurant", "template", "overall_category_comment"]
        )
        
        if not categories:
            return {
                "success": False,
                "message": "No checklist categories found for this restaurant"
            }
        
        # Group categories by template
        templates = {}
        for category in categories:
            template_name = category.template or "Default Template"
            
            if template_name not in templates:
                # Get template details
                template_doc = None
                if category.template:
                    try:
                        template_doc = frappe.get_doc("Checklist Template", category.template)
                    except:
                        pass
                
                templates[template_name] = {
                    "id": category.template or "default",
                    "name": template_doc.template_name if template_doc else "Default Template",
                    "description": template_doc.description if template_doc else "Default checklist template",
                    "categories": []
                }
            
            # Get questions for this category - FIXED TO WORK WITH YOUR EXISTING STRUCTURE
            category_doc = frappe.get_doc("Checklist Category", category.name)
            questions = []
            
            # Your existing Audit Question is a child table with direct fields
            if hasattr(category_doc, 'questions') and category_doc.questions:
                for question_row in category_doc.questions:
                    questions.append({
                        "id": question_row.name,  # Use the child table row name as ID
                        "text": question_row.question_text,
                        "answer_type": question_row.answer_type,
                        "options": question_row.options.split(',') if question_row.options else [],
                        "is_mandatory": question_row.is_mandatory,
                        "allow_image_upload": question_row.allow_image_upload,
                        "comment": question_row.question_comment or ""
                    })
            
            templates[template_name]["categories"].append({
                "id": category.name,
                "name": category.category_name,
                "questions": questions
            })
        
        return {
            "success": True,
            "templates": list(templates.values())
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting checklist template: {str(e)}", "Get Checklist Template")
        return {
            "success": False,
            "message": f"Error loading checklist: {str(e)}"
        }


@frappe.whitelist() 
def validate_location(restaurant_id, user_latitude, user_longitude):
    """Validate user location against restaurant location"""
    try:
        # Get restaurant location details
        restaurant = frappe.get_doc("Restaurant", restaurant_id)
        
        if not restaurant.latitude or not restaurant.longitude:
            return {
                "success": True,  # Skip validation if restaurant doesn't have coordinates
                "is_within_range": True,
                "message": "Location validation skipped - restaurant coordinates not set",
                "allowed_radius": restaurant.location_radius or 100
            }
        
        # Calculate distance using Haversine formula
        from math import radians, cos, sin, asin, sqrt
        
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, [
            float(user_latitude), 
            float(user_longitude),
            float(restaurant.latitude), 
            float(restaurant.longitude)
        ])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in meters
        r = 6371000
        distance = c * r
        
        allowed_radius = restaurant.location_radius or 100
        is_within_range = distance <= allowed_radius
        
        # Log location check
        try:
            frappe.get_doc({
                "doctype": "Location Check Log",
                "restaurant": restaurant_id,
                "user": frappe.session.user,
                "check_time": frappe.utils.now(),
                "user_latitude": user_latitude,
                "user_longitude": user_longitude,
                "calculated_distance": distance,
                "is_within_range": is_within_range,
                "restaurant_latitude": restaurant.latitude,
                "restaurant_longitude": restaurant.longitude,
                "allowed_radius": allowed_radius
            }).insert(ignore_permissions=True)
        except Exception as log_error:
            # Don't fail location validation if logging fails
            frappe.log_error(f"Failed to log location check: {str(log_error)}", "Location Check Logging")
        
        return {
            "success": True,
            "is_within_range": is_within_range,
            "distance": round(distance, 2),
            "allowed_radius": allowed_radius,
            "message": f"You are {round(distance, 2)}m from the restaurant" if is_within_range else f"You are {round(distance, 2)}m away. Must be within {allowed_radius}m"
        }
        
    except Exception as e:
        frappe.log_error(f"Error validating location: {str(e)}", "Location Validation")
        return {
            "success": False,
            "message": f"Location validation failed: {str(e)}"
        }


@frappe.whitelist()
def submit_audit(restaurant_id, answers, overall_comment=""):
    """Submit completed audit"""
    try:
        import json
        current_user = frappe.session.user
        
        # Parse answers JSON
        answers_data = json.loads(answers) if isinstance(answers, str) else answers
        
        # Get employee record
        employee = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
        
        # Create audit submission
        audit_submission = frappe.get_doc({
            "doctype": "Audit Submission",
            "restaurant": restaurant_id,
            "auditor": current_user,
            "employee": employee,
            "audit_date": frappe.utils.getdate(),
            "audit_time": frappe.utils.nowtime(),
            "submission_time": frappe.utils.now(),
            "overall_comment": overall_comment,
            "answers": []
        })
        
        total_score = 0
        max_possible_score = 0
        questions_with_images = 0
        questions_with_comments = 0
        
        # Process each answer
        for answer_data in answers_data:
            # Find the question in the checklist categories
            question_text = ""
            answer_type = "Text"
            category_name = answer_data.get("category", "")
            
            try:
                # Try to get question details from Audit Question child table
                # Since answer_data["question_id"] is the child table row name
                question_row = frappe.db.get_value("Audit Question", answer_data["question_id"], 
                    ["question_text", "answer_type"], as_dict=True)
                if question_row:
                    question_text = question_row.question_text
                    answer_type = question_row.answer_type
            except:
                question_text = f"Question {answer_data['question_id']}"
            
            # Calculate score
            score = 0
            if answer_data["answer_value"] == "Yes" or answer_data["answer_value"] == "True":
                score = 5
            elif answer_data["answer_value"] == "No" or answer_data["answer_value"] == "False":
                score = 1
            elif str(answer_data.get("answer_value", "")).isdigit():
                score = int(answer_data["answer_value"])
            
            total_score += score
            max_possible_score += 5
            
            if answer_data.get("image_data"):
                questions_with_images += 1
            if answer_data.get("answer_comment"):
                questions_with_comments += 1
            
            # Add answer to submission
            audit_submission.append("answers", {
                "question": answer_data["question_id"],
                "question_text": question_text,
                "category": category_name,
                "answer_type": answer_type,
                "answer_value": str(answer_data["answer_value"]),
                "numeric_score": score,
                "selected_options": json.dumps(answer_data.get("selected_options", [])),
                "answer_comment": answer_data.get("answer_comment", ""),
                "image_attachment": "", # Handle file upload separately
                "is_critical": score <= 2,
                "requires_action": score <= 2,
                "follow_up_required": bool(answer_data.get("answer_comment"))
            })
        
        # Calculate final scores
        audit_submission.total_score = total_score
        audit_submission.max_possible_score = max_possible_score
        audit_submission.average_score = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0
        audit_submission.total_questions = len(answers_data)
        audit_submission.questions_with_images = questions_with_images
        audit_submission.questions_with_comments = questions_with_comments
        
        # Generate audit summary
        audit_submission.audit_summary = f"Audit completed with {audit_submission.average_score:.1f}% score"
        audit_submission.recommendations = "Review areas with low scores and implement improvements"
        
        # Save submission
        audit_submission.insert(ignore_permissions=True)
        
        # Update any scheduled visits to completed
        scheduled_visits = frappe.get_all("Scheduled Audit Visit",
            filters={
                "restaurant": restaurant_id,
                "auditor": current_user,
                "status": "Pending",
                "visit_date": frappe.utils.getdate()
            }
        )
        
        for visit in scheduled_visits:
            visit_doc = frappe.get_doc("Scheduled Audit Visit", visit.name)
            visit_doc.status = "Completed"
            visit_doc.save(ignore_permissions=True)
        
        return {
            "success": True,
            "message": "Audit submitted successfully",
            "submission_id": audit_submission.name,
            "average_score": audit_submission.average_score
        }
        
    except Exception as e:
        frappe.log_error(f"Error submitting audit: {str(e)}", "Submit Audit")
        return {
            "success": False,
            "message": f"Error submitting audit: {str(e)}"
        }
# Add these methods to audit_api.py

@frappe.whitelist()
def get_weekly_scheduled_audits():
    """Get scheduled audits for current week and next week only"""
    try:
        from frappe.utils import getdate, add_days
        
        current_user = frappe.session.user
        today = getdate()
        
        # Calculate weeks
        days_since_monday = today.weekday()
        current_week_start = add_days(today, -days_since_monday)
        current_week_end = add_days(current_week_start, 6)
        next_week_start = add_days(current_week_start, 7)
        next_week_end = add_days(next_week_start, 6)
        
        # Get scheduled audits for current and next week only
        scheduled_audits = frappe.get_all("Scheduled Audit Visit",
            filters={
                "auditor": current_user,
                "visit_date": ["between", [current_week_start, next_week_end]]
            },
            fields=[
                "name", "restaurant", "restaurant_name", "visit_date", 
                "status", "week_start_date", "week_end_date"
            ],
            order_by="visit_date asc"
        )
        
        # Separate by week
        current_week_audits = [
            a for a in scheduled_audits 
            if current_week_start <= getdate(a.visit_date) <= current_week_end
        ]
        
        next_week_audits = [
            a for a in scheduled_audits 
            if next_week_start <= getdate(a.visit_date) <= next_week_end
        ]
        
        return {
            "success": True,
            "current_week": {
                "start": current_week_start,
                "end": current_week_end,
                "scheduled_audits": current_week_audits
            },
            "next_week": {
                "start": next_week_start,
                "end": next_week_end,
                "scheduled_audits": next_week_audits
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting weekly scheduled audits: {str(e)}", "Weekly Scheduled Audits")
        return {
            "success": False,
            "message": f"Error loading weekly scheduled audits: {str(e)}"
        }

@frappe.whitelist()
def get_my_weekly_visits():
    """Get current user's scheduled visits for current and next week only"""
    try:
        from frappe.utils import getdate, add_days
        
        current_user = frappe.session.user
        today = getdate()
        
        # Calculate weeks
        days_since_monday = today.weekday()
        current_week_start = add_days(today, -days_since_monday)
        current_week_end = add_days(current_week_start, 6)
        next_week_start = add_days(current_week_start, 7)
        next_week_end = add_days(next_week_start, 6)
        
        # Get visits for current and next week only
        visits = frappe.get_all("Scheduled Audit Visit",
            filters={
                "auditor": current_user,
                "visit_date": ["between", [current_week_start, next_week_end]]
            },
            fields=[
                "name", "restaurant_name", "visit_date", "status"
            ],
            order_by="visit_date asc"
        )
        
        # Separate by week
        current_week_visits = [
            v for v in visits 
            if current_week_start <= getdate(v.visit_date) <= current_week_end
        ]
        
        next_week_visits = [
            v for v in visits 
            if next_week_start <= getdate(v.visit_date) <= next_week_end
        ]
        
        return {
            "success": True,
            "current_week": {
                "start": current_week_start,
                "end": current_week_end,
                "visits": current_week_visits
            },
            "next_week": {
                "start": next_week_start,
                "end": next_week_end,
                "visits": next_week_visits
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting my weekly visits: {str(e)}", "My Weekly Visits")
        return {
            "success": False,
            "message": f"Error loading my weekly visits: {str(e)}"
        }

@frappe.whitelist()
def process_last_week_status():
    """Mark last week's pending audits as Overdue"""
    try:
        from frappe.utils import getdate, add_days
        
        today = getdate()
        days_since_monday = today.weekday()
        current_week_start = add_days(today, -days_since_monday)
        
        # Calculate last week
        last_week_start = add_days(current_week_start, -7)
        last_week_end = add_days(last_week_start, 6)
        
        # Find pending scheduled audits from last week
        pending_audits = frappe.get_all("Scheduled Audit Visit",
            filters={
                "visit_date": ["between", [last_week_start, last_week_end]],
                "status": "Pending"
            },
            fields=["name", "restaurant_name", "auditor", "visit_date"]
        )
        
        updates_made = 0
        
        # Update status to Overdue
        for audit in pending_audits:
            try:
                audit_doc = frappe.get_doc("Scheduled Audit Visit", audit.name)
                audit_doc.status = "Overdue"
                audit_doc.overdue_notified = 1
                audit_doc.save(ignore_permissions=True)
                updates_made += 1
            except Exception as e:
                frappe.log_error(f"Error updating audit {audit.name}: {str(e)}", "Update Audit Status")
        
        # Also check for incomplete daily audits from last week
        incomplete_daily = frappe.get_all("Audit Progress",
            filters={
                "start_time": ["between", [
                    f"{last_week_start} 00:00:00", 
                    f"{last_week_end} 23:59:59"
                ]],
                "is_completed": 0
            }
        )
        
        return {
            "success": True,
            "updates_made": updates_made,
            "overdue_scheduled": updates_made,
            "incomplete_daily": len(incomplete_daily),
            "last_week_start": last_week_start,
            "last_week_end": last_week_end
        }
        
    except Exception as e:
        frappe.log_error(f"Error processing last week status: {str(e)}", "Process Last Week")
        return {
            "success": False,
            "message": f"Error processing last week: {str(e)}"
        }

@frappe.whitelist()
def get_weekly_audit_summary():
    """Get summary of audits for current and next week"""
    try:
        from frappe.utils import getdate, add_days
        
        current_user = frappe.session.user
        today = getdate()
        
        # Calculate weeks
        days_since_monday = today.weekday()
        current_week_start = add_days(today, -days_since_monday)
        current_week_end = add_days(current_week_start, 6)
        next_week_start = add_days(current_week_start, 7)
        next_week_end = add_days(next_week_start, 6)
        
        # Current week summary
        current_scheduled = frappe.db.count("Scheduled Audit Visit", {
            "auditor": current_user,
            "visit_date": ["between", [current_week_start, current_week_end]]
        })
        
        current_completed = frappe.db.count("Scheduled Audit Visit", {
            "auditor": current_user,
            "visit_date": ["between", [current_week_start, current_week_end]],
            "status": "Completed"
        })
        
        current_daily = frappe.db.count("Audit Progress", {
            "auditor": current_user,
            "start_time": ["between", [
                f"{current_week_start} 00:00:00", 
                f"{current_week_end} 23:59:59"
            ]]
        })
        
        current_daily_completed = frappe.db.count("Audit Progress", {
            "auditor": current_user,
            "start_time": ["between", [
                f"{current_week_start} 00:00:00", 
                f"{current_week_end} 23:59:59"
            ]],
            "is_completed": 1
        })
        
        # Next week summary
        next_scheduled = frappe.db.count("Scheduled Audit Visit", {
            "auditor": current_user,
            "visit_date": ["between", [next_week_start, next_week_end]]
        })
        
        return {
            "success": True,
            "current_week": {
                "start": current_week_start,
                "end": current_week_end,
                "scheduled_audits": current_scheduled,
                "completed_audits": current_completed,
                "pending_audits": current_scheduled - current_completed,
                "daily_audits": current_daily,
                "daily_completed": current_daily_completed,
                "daily_pending": current_daily - current_daily_completed
            },
            "next_week": {
                "start": next_week_start,
                "end": next_week_end,
                "scheduled_audits": next_scheduled,
                "needs_scheduling": next_scheduled == 0
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting weekly summary: {str(e)}", "Weekly Summary")
        return {
            "success": False,
            "message": f"Error getting weekly summary: {str(e)}"
        }
# Add these validations to audit_api.py

@frappe.whitelist()
def schedule_audit_visit(restaurant, visit_date):
    """Create a new scheduled audit visit with validations"""
    try:
        from frappe.utils import getdate, add_days
        
        current_user = frappe.session.user
        today = getdate()
        visit_date_obj = getdate(visit_date)
        
        # Validation 1: Cannot schedule in the past
        if visit_date_obj < today:
            return {
                "success": False,
                "message": "Cannot schedule audit for past dates. Please select today or a future date."
            }
        
        # Validation 2: Cannot schedule more than 3 weeks in advance
        max_future_date = add_days(today, 21)  # 3 weeks = 21 days
        if visit_date_obj > max_future_date:
            return {
                "success": False,
                "message": f"Cannot schedule audit more than 3 weeks in advance. Maximum date allowed: {max_future_date}"
            }
        
        # Validation 3: Check for conflicts between daily and regular audits
        conflict_check = check_audit_conflicts(restaurant, visit_date, current_user)
        if not conflict_check["success"]:
            return conflict_check
        
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

def check_audit_conflicts(restaurant, visit_date, auditor):
    """Check for conflicts between daily and regular audits"""
    try:
        from frappe.utils import getdate
        
        visit_date_obj = getdate(visit_date)
        
        # Check if there's a daily audit for this date
        daily_audit_exists = frappe.db.exists("Audit Progress", {
            "restaurant": restaurant,
            "auditor": auditor,
            "start_time": ["between", [
                f"{visit_date_obj} 00:00:00",
                f"{visit_date_obj} 23:59:59"
            ]]
        })
        
        if daily_audit_exists:
            return {
                "success": False,
                "message": "Cannot schedule regular audit on the same day as a daily audit. Please choose a different date."
            }
        
        # Check if there's already a regular audit scheduled
        regular_audit_exists = frappe.db.exists("Scheduled Audit Visit", {
            "restaurant": restaurant,
            "auditor": auditor,
            "visit_date": visit_date_obj,
            "status": ["!=", "Cancelled"]
        })
        
        if regular_audit_exists:
            return {
                "success": False,
                "message": "Regular audit already scheduled for this date."
            }
        
        return {"success": True}
        
    except Exception as e:
        frappe.log_error(f"Error checking audit conflicts: {str(e)}", "Audit Conflict Check")
        return {
            "success": False,
            "message": "Error checking for scheduling conflicts"
        }

@frappe.whitelist()
def can_start_daily_audit(template_name):
    """Check if daily audit can be started (not already completed today)"""
    try:
        from frappe.utils import getdate
        
        current_user = frappe.session.user
        today = getdate()
        
        # Get user's restaurants
        user_restaurants = get_restaurants()
        if not user_restaurants["success"] or not user_restaurants["restaurants"]:
            return {
                "success": False,
                "message": "No restaurants assigned to user"
            }
        
        restaurant = user_restaurants["restaurants"][0]["name"]
        
        # Check if daily audit already completed today
        completed_today = frappe.db.exists("Audit Progress", {
            "restaurant": restaurant,
            "auditor": current_user,
            "start_time": ["between", [
                f"{today} 00:00:00",
                f"{today} 23:59:59"
            ]],
            "is_completed": 1
        })
        
        if completed_today:
            return {
                "success": False,
                "message": "Daily audit already completed for today. You cannot start another daily audit."
            }
        
        # Check if there's a pending daily audit
        pending_today = frappe.db.get_value("Audit Progress", {
            "restaurant": restaurant,
            "auditor": current_user,
            "start_time": ["between", [
                f"{today} 00:00:00",
                f"{today} 23:59:59"
            ]],
            "is_completed": 0
        }, "name")
        
        if pending_today:
            return {
                "success": False,
                "message": "You have a pending daily audit from earlier today. Please complete it first.",
                "pending_audit_id": pending_today
            }
        
        # Check if there's a regular audit scheduled for today
        regular_today = frappe.db.exists("Scheduled Audit Visit", {
            "restaurant": restaurant,
            "auditor": current_user,
            "visit_date": today,
            "status": ["!=", "Completed"]
        })
        
        if regular_today:
            return {
                "success": False,
                "message": "Cannot start daily audit. You have a regular audit scheduled for today."
            }
        
        return {"success": True}
        
    except Exception as e:
        frappe.log_error(f"Error checking daily audit availability: {str(e)}", "Daily Audit Check")
        return {
            "success": False,
            "message": "Error checking daily audit availability"
        }

# Add these methods to audit_api.py

@frappe.whitelist()
def check_restaurant_week_status(restaurant_id):
    """Check if restaurant has completed audits for current week"""
    try:
        from frappe.utils import getdate, add_days
        
        current_user = frappe.session.user
        today = getdate()
        
        # Calculate current week (Monday to Sunday)
        days_since_monday = today.weekday()
        current_week_start = add_days(today, -days_since_monday)
        current_week_end = add_days(current_week_start, 6)
        
        # Check if ANY auditor has completed audit for this restaurant this week
        completed_audits = frappe.get_all("Audit Submission",
            filters={
                "restaurant": restaurant_id,
                "audit_date": ["between", [current_week_start, current_week_end]]
            },
            fields=["name", "auditor", "audit_date", "average_score"]
        )
        
        # Check if current user has completed audit this week
        user_completed_this_week = any(
            audit.auditor == current_user for audit in completed_audits
        )
        
        # Check completed scheduled visits for current week
        completed_scheduled = frappe.get_all("Scheduled Audit Visit",
            filters={
                "restaurant": restaurant_id,
                "auditor": current_user,
                "visit_date": ["between", [current_week_start, current_week_end]],
                "status": "Completed"
            }
        )
        
        user_has_completed_scheduled = len(completed_scheduled) > 0
        
        # Restaurant week status
        restaurant_week_complete = len(completed_audits) > 0
        user_week_complete = user_completed_this_week or user_has_completed_scheduled
        
        return {
            "success": True,
            "restaurant_week_complete": restaurant_week_complete,
            "user_week_complete": user_week_complete,
            "can_access_audit": not user_week_complete,  # Only allow if user hasn't completed
            "completed_audits_count": len(completed_audits),
            "week_start": current_week_start,
            "week_end": current_week_end,
            "message": get_week_status_message(restaurant_week_complete, user_week_complete),
            "next_access_date": add_days(current_week_end, 1)  # Next Monday
        }
        
    except Exception as e:
        frappe.log_error(f"Error checking restaurant week status: {str(e)}", "Restaurant Week Status")
        return {
            "success": False,
            "message": f"Error checking week status: {str(e)}"
        }

def get_week_status_message(restaurant_complete, user_complete):
    """Get appropriate message based on week status"""
    if user_complete:
        return "✅ You have completed your audit for this week. Restaurant will reopen next Monday."
    elif restaurant_complete:
        return "✅ This restaurant has been audited this week by another team member."
    else:
        return "📝 Restaurant is available for audit this week."

@frappe.whitelist()
def get_restaurants_with_week_status():
    """Get restaurants with week completion status"""
    try:
        # Get basic restaurants list
        restaurants_response = get_restaurants()
        
        if not restaurants_response["success"]:
            return restaurants_response
        
        restaurants = restaurants_response["restaurants"]
        
        # Add week status to each restaurant
        for restaurant in restaurants:
            week_status = check_restaurant_week_status(restaurant["name"])
            if week_status["success"]:
                restaurant.update({
                    "week_complete": week_status["user_week_complete"],
                    "can_access": week_status["can_access_audit"],
                    "week_message": week_status["message"],
                    "next_access": week_status.get("next_access_date")
                })
            else:
                restaurant.update({
                    "week_complete": False,
                    "can_access": True,
                    "week_message": "Status unknown",
                    "next_access": None
                })
        
        return {
            "success": True,
            "restaurants": restaurants
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting restaurants with week status: {str(e)}", "Restaurants Week Status")
        return {
            "success": False,
            "message": f"Error loading restaurants: {str(e)}",
            "restaurants": []
        }

@frappe.whitelist()
def check_employee_removals():
    """Check for recently removed employees and return cleanup information"""
    try:
        # This is a placeholder function - in a real implementation,
        # you might want to track employee removals in a separate table
        # or use a different mechanism to detect removals
        
        # For now, we'll return an empty list
        # In a production system, you might:
        # 1. Check a "recent_removals" table
        # 2. Use webhooks or real-time notifications
        # 3. Check for employees with "Removed" status
        
        removed_employees = []
        
        # Check for employees with "Removed" status in the last hour
        recent_removals = frappe.get_all("Restaurant Employee",
            filters={
                "employee_status": "Removed",
                "modified": [">=", frappe.utils.add_to_date(nowdate(), hours=-1)]
            },
            fields=["employee", "parent as restaurant_id"]
        )
        
        for removal in recent_removals:
            removed_employees.append({
                "employee_id": removal.employee,
                "restaurant_id": removal.restaurant_id
            })
        
        return {
            "success": True,
            "removed_employees": removed_employees
        }
        
    except Exception as e:
        frappe.log_error(f"Error checking employee removals: {str(e)}", "Employee Removal Check")
        return {
            "success": False,
            "message": f"Error checking employee removals: {str(e)}",
            "removed_employees": []
        }