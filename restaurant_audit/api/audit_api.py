import frappe
from frappe import _
from frappe.utils import now_datetime
import json
import math

@frappe.whitelist(allow_guest=True)
def authenticate_user(email, password):
    """Authenticate user for restaurant audit system"""
    try:
        # Check if user exists
        if not frappe.db.exists("User", email):
            return {
                "success": False,
                "message": "User not found"
            }
        
        # Check password
        from frappe.auth import check_password
        if check_password(email, password):
            # Check if user has appropriate role (Employee or System Manager)
            user_doc = frappe.get_doc("User", email)
            user_roles = [role.role for role in user_doc.roles]
            
            if any(role in ["Employee", "System Manager", "Auditor"] for role in user_roles):
                # Login the user
                frappe.local.login_manager.login_as(email)
                
                return {
                    "success": True,
                    "user": email,
                    "message": "Authentication successful"
                }
            else:
                return {
                    "success": False,
                    "message": "User does not have required permissions"
                }
        else:
            return {
                "success": False,
                "message": "Invalid credentials"
            }
    except Exception as e:
        frappe.log_error(f"Authentication error: {str(e)}")
        return {
            "success": False,
            "message": "Authentication failed"
        }

@frappe.whitelist()
def get_restaurants():
    """Get list of restaurants assigned to current user"""
    try:
        current_user = frappe.session.user
        
        # Get employee record for current user
        employee = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
        
        if not employee:
            return {
                "success": False,
                "message": "No employee record found for current user"
            }
        
        # Get restaurants assigned to this employee
        restaurants = frappe.db.sql("""
            SELECT r.name, r.restaurant_name, r.address, 
                   r.latitude, r.longitude, r.location_radius
            FROM `tabRestaurant` r
            JOIN `tabRestaurant Employee` re ON re.parent = r.name
            WHERE re.employee = %s
        """, (employee,), as_dict=True)
        
        return {
            "success": True,
            "restaurants": restaurants
        }
    except Exception as e:
        frappe.log_error(f"Get restaurants error: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def get_checklist_template(restaurant_id):
    """Get checklist template for a specific restaurant"""
    try:
        # Get the checklist template for the restaurant
        template = frappe.db.get_value("Checklist Template", 
                                       {"applies_to_restaurant": restaurant_id}, 
                                       ["name", "template_name", "description"])
        
        if not template:
            return {
                "success": False,
                "message": "No checklist template found for this restaurant"
            }

        template_name = template[0] if isinstance(template, tuple) else template
        template_doc = frappe.get_doc("Checklist Template", template_name)

        # Get categories for this template, linked to the restaurant
        categories = frappe.get_list("Checklist Category", 
                                     filters={
                                         "template": template_name,
                                         "restaurant": restaurant_id
                                     },
                                     fields=["name", "category_name"],
                                     order_by="name asc")

        # Structure the template data
        categories_data = []
        for category in categories:
            # Load the parent Checklist Category doc
            category_doc = frappe.get_doc("Checklist Category", category.name)

            # Access child table field (usually named 'questions')
            questions_data = []
            for question in category_doc.questions:
                question_data = {
                    "id": question.name,
                    "text": question.question_text,
                    "answer_type": question.answer_type,
                    "options": question.options.split(",") if question.options else [],
                    "allow_image_upload": bool(question.allow_image_upload),
                    "is_mandatory": bool(question.is_mandatory)
                }
                questions_data.append(question_data)

            category_data = {
                "id": category.name,
                "name": category.category_name,
                "questions": questions_data
            }
            categories_data.append(category_data)

        return {
            "success": True,
            "template": {
                "id": template_doc.name,
                "name": template_doc.template_name,
                "description": template_doc.description,
                "categories": categories_data
            }
        }

    except Exception as e:
        frappe.log_error(f"Get checklist template error: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def validate_location(restaurant_id, user_latitude, user_longitude):
    """Validate if user is within allowed radius of restaurant"""
    try:
        # Get restaurant location data
        restaurant = frappe.get_doc("Restaurant", restaurant_id)
        
        if not restaurant.latitude or not restaurant.longitude:
            return {
                "success": False,
                "message": "Restaurant location not configured"
            }
        
        # Calculate distance using Haversine formula
        def calculate_distance(lat1, lon1, lat2, lon2):
            R = 6371000  # Earth's radius in meters
            
            lat1_rad = math.radians(float(lat1))
            lat2_rad = math.radians(float(lat2))
            delta_lat = math.radians(float(lat2) - float(lat1))
            delta_lon = math.radians(float(lon2) - float(lon1))
            
            a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
                 math.cos(lat1_rad) * math.cos(lat2_rad) *
                 math.sin(delta_lon / 2) * math.sin(delta_lon / 2))
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            
            return R * c
        
        distance = calculate_distance(
            user_latitude, user_longitude,
            restaurant.latitude, restaurant.longitude
        )
        
        is_within_range = distance <= restaurant.location_radius
        
        return {
            "success": True,
            "is_within_range": is_within_range,
            "distance": round(distance, 2),
            "allowed_radius": restaurant.location_radius,
            "message": "Location validated successfully" if is_within_range 
                      else f"You are {round(distance, 2)}m away from the restaurant. You must be within {restaurant.location_radius}m to perform an audit."
        }
    except Exception as e:
        frappe.log_error(f"Location validation error: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def submit_audit(restaurant_id, answers, overall_comment=""):
    """Submit completed audit results"""
    try:
        current_user = frappe.session.user
        
        # Parse answers if it's a string
        if isinstance(answers, str):
            answers = json.loads(answers)
        
        # Create new Audit Submission
        audit_submission = frappe.new_doc("Audit Submission")
        audit_submission.restaurant = restaurant_id
        audit_submission.auditor = current_user
        audit_submission.audit_date = now_datetime().date()
        audit_submission.audit_time = now_datetime().time()
        audit_submission.overall_comment = overall_comment
        
        # Add answers to the submission
        for answer_data in answers:
            answer_row = audit_submission.append("answers", {})
            answer_row.question = answer_data.get("question_id")
            answer_row.answer_value = answer_data.get("answer_value")
            answer_row.answer_comment = answer_data.get("answer_comment", "")
            answer_row.category = answer_data.get("category") 
            
            # Handle image attachment if provided
            if answer_data.get("image_data"):
                # TODO: Process and save image attachment
                # This would involve saving the base64 image data as a file
                pass
        
        # Save the audit submission
        audit_submission.insert()
        frappe.db.commit()
        
        return {
            "success": True,
            "submission_id": audit_submission.name,
            "message": "Audit submitted successfully"
        }
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Submit audit error: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def get_audit_history(restaurant_id=None):
    """Get audit history for restaurants"""
    try:
        current_user = frappe.session.user
        
        # Get employee record for current user
        employee = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
        
        filters = {"auditor": current_user}
        if restaurant_id:
            filters["restaurant"] = restaurant_id
        
        # Get audit submissions
        submissions = frappe.get_list("Audit Submission",
                                    filters=filters,
                                    fields=["name", "restaurant", "audit_date", "audit_time", "overall_comment"],
                                    order_by="audit_date desc, audit_time desc")
        
        # Get restaurant names
        for submission in submissions:
            restaurant_name = frappe.db.get_value("Restaurant", submission.restaurant, "restaurant_name")
            submission["restaurant_name"] = restaurant_name
        
        return {
            "success": True,
            "submissions": submissions
        }
    except Exception as e:
        frappe.log_error(f"Get audit history error: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }

