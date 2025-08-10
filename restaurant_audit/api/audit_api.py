import frappe
from frappe import _
from frappe.utils import now_datetime
import json
import math
import base64


@frappe.whitelist(allow_guest=True)
def authenticate_user(email, password):
    """Authenticate user for restaurant audit system"""
    try:
        if not frappe.db.exists("User", email):
            return {
                "success": False,
                "message": "User not found"
            }

        # Validate credentials and create session
        from frappe.auth import LoginManager
        login_manager = LoginManager()
        login_manager.authenticate(email, password)
        login_manager.post_login()

        # Check roles
        user_doc = frappe.get_doc("User", email)
        user_roles = [role.role for role in user_doc.roles]

        if not any(role in ["Employee", "System Manager", "Auditor"] for role in user_roles):
            return {
                "success": False,
                "message": "User does not have required permissions"
            }

        return {
            "success": True,
            "user": email,
            "message": "Authentication successful"
        }

    except frappe.AuthenticationError as e:
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
    try:
        current_user = frappe.session.user

        employee = frappe.db.get_value("Employee", {"user_id": current_user}, "name")

        if not employee:
            return {"success": False, "message": "Employee not found"}

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
        frappe.log_error(f"Error in get_restaurants: {str(e)}")
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_checklist_template(restaurant_id):
    try:
        templates = frappe.get_all("Checklist Template",
            filters={"applies_to_restaurant": restaurant_id},
            fields=["name", "template_name", "description"]
        )

        if not templates:
            return {
                "success": True,
                "templates": []
            }

        all_templates = []

        for template in templates:
            categories = frappe.get_list("Checklist Category",
                filters={
                    "template": template.name,
                    "restaurant": restaurant_id
                },
                fields=["name", "category_name"],
                order_by="name asc"
            )

            categories_data = []
            for category in categories:
                category_doc = frappe.get_doc("Checklist Category", category.name)
                questions_data = []
                for question in category_doc.questions:
                    questions_data.append({
                        "id": question.name,
                        "text": question.question_text,
                        "answer_type": question.answer_type,
                        "options": question.options.split(",") if question.options else [],
                        "allow_image_upload": bool(question.allow_image_upload),
                        "is_mandatory": bool(question.is_mandatory)
                    })
                categories_data.append({
                    "id": category.name,
                    "name": category.category_name,
                    "questions": questions_data
                })

            all_templates.append({
                "id": template.name,
                "name": template.template_name,
                "description": template.description,
                "categories": categories_data
            })

        return {
            "success": True,
            "templates": all_templates
        }

    except Exception as e:
        frappe.log_error(f"Checklist Load Error: {str(e)}")
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
            question_id = answer_data.get("question_id")
            answer_row.question = question_id

            # Load question text from the Question child table
            question_text = frappe.db.get_value("Audit Question", question_id, "question_text")
            answer_row.question_text = question_text or ""
            answer_row.answer_value = answer_data.get("answer_value")
            answer_row.answer_comment = answer_data.get("answer_comment", "")
            answer_row.category = answer_data.get("category")

            # Handle image attachment if provided
            if answer_data.get("image_data"):
                try:
                    import base64

                    # Decode base64 image
                    image_base64 = answer_data["image_data"]
                    image_content = base64.b64decode(image_base64.split(",")[-1])  # remove data:image/png;base64, etc

                    # Generate unique file name
                    filename = f"{frappe.generate_hash(length=10)}.jpg"

                    # Save file using frappe's file API
                    _file = frappe.get_doc({
                        "doctype": "File",
                        "file_name": filename,
                        "content": image_content,
                        "attached_to_doctype": "Audit Submission",
                        "attached_to_name": audit_submission.name,
                        "is_private": 0
                    })
                    _file.save(ignore_permissions=True)

                    # Store file URL in the answer row
                    answer_row.image_attachment = _file.file_url

                except Exception as img_err:
                    frappe.log_error(f"Error saving image: {str(img_err)}")

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

# In get_audit_history()
def get_audit_history(restaurant_id=None):
    # ...
    submissions = frappe.get_list("Audit Submission",
        filters=filters,
        fields=[
            "name", 
            "restaurant", 
            "audit_date", 
            "audit_time", 
            "overall_comment",
            "restaurant_name" # Use this instead of the loop
        ],
        order_by="audit_date desc, audit_time desc"
    )
    # The loop to get restaurant_name is no longer needed.
    return {
        "success": True,
        "submissions": submissions
    }
