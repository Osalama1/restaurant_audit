import frappe
from frappe import _
from frappe.utils import now_datetime, now, getdate
import json
import math
import base64
from datetime import datetime, timedelta
from frappe.utils import getdate, add_to_date, add_days

@frappe.whitelist(allow_guest=True)
def authenticate_user(email, password):
    """Enhanced authentication with role validation and session management"""
    try:
        if not frappe.db.exists("User", email):
            return {
                "success": False,
                "message": "User not found"
            }

        # Check if user is active
        user_doc = frappe.get_doc("User", email)
        if user_doc.enabled == 0:
            return {
                "success": False,
                "message": "User account is disabled"
            }

        # Validate credentials and create session
        from frappe.auth import LoginManager
        login_manager = LoginManager()
        login_manager.authenticate(email, password)
        login_manager.post_login()

        # Check roles
        user_roles = [role.role for role in user_doc.roles]
        required_roles = ["Employee", "System Manager", "Auditor", "Restaurant Manager"]
        
        if not any(role in required_roles for role in user_roles):
            return {
                "success": False,
                "message": "User does not have required permissions for audit system"
            }

        # Get employee details if available
        employee = frappe.db.get_value("Employee", {"user_id": email}, 
                                     ["name", "employee_name", "department"], as_dict=True)

        return {
            "success": True,
            "user": email,
            "employee": employee,
            "roles": user_roles,
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
    """Enhanced restaurant retrieval with role check, filtering, and dynamic audit fields"""
    try:
        current_user = frappe.session.user
        today = getdate()
        roles = frappe.get_roles(current_user)

        # System Manager -> see all
        if "System Manager" in roles:
            restaurants = frappe.get_all("Restaurant",
                fields=["name", "restaurant_name", "address", "latitude", "longitude", "location_radius"])
        
        else:
            # Only auditors allowed
            if "Auditor" not in roles:
                return {"success": False, "message": "Access denied. Auditor role required."}

            employee = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
            if not employee:
                return {"success": False, "message": "Employee record not found"}

            # Get only restaurants where this employee is assigned
            assignments = frappe.get_all("Restaurant Employee",
                filters={
                    "employee": employee,
                    "is_active": 1
                 
                },
                fields=["parent", "employee", "audit_frequency", "last_audit_date"]
            )

            restaurants = []
            for a in assignments:
                r = frappe.db.get_value("Restaurant",
                    {"name": a.parent},
                    ["name", "restaurant_name", "address", "latitude", "longitude", "location_radius"],
                    as_dict=True
                )
                if r:
                    # Calculate next audit date dynamically
                    next_audit = calculate_next_audit_date(
                        a.last_audit_date or today,
                        a.audit_frequency or "Weekly"
                    )

                    # Merge assignment data into restaurant
                    r.update({
                        "audit_frequency": a.audit_frequency,
                        "last_audit_date": a.last_audit_date,
                        "next_audit_date": next_audit
                    })

                    # Determine audit status
                    r["audit_status"] = determine_audit_status(r, today)

                    restaurants.append(r)

        # Enhance with statistics and computed fields
        for idx, restaurant in enumerate(restaurants):
            restaurants[idx] = enhance_restaurant_data(restaurant, current_user)

        return {"success": True, "restaurants": restaurants}

    except Exception as e:
        frappe.log_error(f"Error in get_restaurants: {str(e)}")
        return {"success": False, "message": str(e)}


def enhance_restaurant_data(restaurant, current_user):
    """Enhance restaurant data with audit status and statistics"""
    try:
        today = getdate()
        restaurant_id = restaurant['name']
        
        # Get audit statistics
        audit_stats = frappe.db.sql("""
            SELECT 
                COUNT(DISTINCT s.name) as total_audits,
                COUNT(DISTINCT CASE WHEN s.auditor = %s THEN s.name END) as my_audits,
                MAX(s.audit_date) as last_audit_date,
                AVG(s.average_score) as avg_score
            FROM `tabAudit Submission` s
            WHERE s.restaurant = %s
        """, (current_user, restaurant_id), as_dict=True)[0]
        
        # Calculate days since last audit
        restaurant['last_audit_days'] = None
        if audit_stats.get('last_audit_date'):
            days_ago = (today - audit_stats['last_audit_date']).days
            restaurant['last_audit_days'] = days_ago
        
        # Set audit statistics
        restaurant['total_audits'] = audit_stats.get('total_audits', 0)
        restaurant['my_audits'] = audit_stats.get('my_audits', 0)
        restaurant['avg_score'] = round(audit_stats.get('avg_score', 0), 1) if audit_stats.get('avg_score') else 0
        
        # Determine audit status
        restaurant['audit_status'] = determine_audit_status(restaurant, today)
        
        # Check for pending progress
        has_progress = frappe.db.exists("Audit Progress", {
            "restaurant": restaurant_id,
            "auditor": current_user,
            "is_completed": 0
        })
        restaurant['has_progress'] = bool(has_progress)
        
        # Calculate next audit date if not set
        if not restaurant.get('next_audit_date') and restaurant.get('audit_frequency'):
            restaurant['next_audit_date'] = calculate_next_audit_date(
                restaurant.get('last_audit_date') or today,
                restaurant.get('audit_frequency', 'Weekly')
            )
        
        return restaurant
        
    except Exception as e:
        frappe.log_error(f"Error enhancing restaurant data: {str(e)}")
        return restaurant


def determine_audit_status(restaurant, today):
    """Determine the current audit status of a restaurant"""
    try:
        next_audit_date = restaurant.get('next_audit_date')
        last_audit_date = restaurant.get('last_audit_date')
        
        # Check for in-progress audit
        if restaurant.get('has_progress'):
            return 'In Progress'
        
        # If no next audit date set, default to pending
        if not next_audit_date:
            return 'Pending'
        
        # Convert to date if string
        if isinstance(next_audit_date, str):
            next_audit_date = getdate(next_audit_date)
        
        # Check if overdue
        if next_audit_date < today:
            return 'Overdue'
        
        # Check if due today or within 3 days
        days_until_audit = (next_audit_date - today).days
        if days_until_audit <= 3:
            return 'Due Soon'
        
        # Check if completed recently (within frequency period)
        if last_audit_date:
            if isinstance(last_audit_date, str):
                last_audit_date = getdate(last_audit_date)
            
            days_since_last = (today - last_audit_date).days
            frequency = restaurant.get('audit_frequency', 'Weekly')
            
            frequency_days = {
                'Weekly': 7,
                'Bi-Weekly': 14,
                'Monthly': 30,
                'Quarterly': 90
            }.get(frequency, 7)
            
            if days_since_last < frequency_days:
                return 'Completed'
        
        return 'Pending'
        
    except Exception as e:
        frappe.log_error(f"Error determining audit status: {str(e)}")
        return 'Pending'


def calculate_next_audit_date(last_date, frequency):
    """Calculate the next audit date based on frequency"""
    try:
        if isinstance(last_date, str):
            last_date = getdate(last_date)
        
        frequency_mapping = {
            'Weekly': {'days': 7},
            'Bi-Weekly': {'days': 14},
            'Monthly': {'months': 1},
            'Quarterly': {'months': 3}
        }
        
        if frequency in frequency_mapping:
            return add_to_date(last_date, **frequency_mapping[frequency])
        
        # Default to weekly
        return add_days(last_date, 7)
        
    except Exception as e:
        frappe.log_error(f"Error calculating next audit date: {str(e)}")
        return add_days(getdate(), 7)




def get_audit_frequency(restaurant_id):
    """Get recommended audit frequency for a restaurant"""
    # This could be based on restaurant type, size, history, etc.
    # For now, return a default
    return "weekly"

@frappe.whitelist()
def get_checklist_template(restaurant_id):
    try:
        templates = frappe.get_all("Checklist Template",
            filters={"applies_to_restaurant": restaurant_id},
            fields=["name", "template_name", "description"]
        )

        if not templates:
            return {"message": {"success": True, "templates": []}}

        all_templates = []
        for template in templates:
            categories = frappe.get_list("Checklist Category",
                filters={"template": template.name, "restaurant": restaurant_id},
                fields=["name", "category_name", "overall_category_comment"], 
                order_by="idx asc, name asc"
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
                        "options": [opt.strip() for opt in question.options.split(",")] if question.options else [],
                        "allow_image_upload": bool(question.allow_image_upload),
                        "is_mandatory": bool(question.is_mandatory),
                        "comment": question.question_comment or "",
                        "weight": getattr(question, 'weight', 1)
                    })
                
                categories_data.append({
                    "id": category.name,
                    "name": category.category_name,
                    "description": category.overall_category_comment or "",
                    "questions": questions_data,
                    "question_count": len(questions_data)
                })
            
            all_templates.append({
                "id": template.name,
                "name": template.template_name,
                "description": template.description or "",
                "categories": categories_data,
                "total_questions": sum(cat["question_count"] for cat in categories_data)
            })

        return {"success": True, "templates": all_templates}


    except Exception as e:
        frappe.log_error(f"Checklist Load Error: {str(e)}")
        return {"message": {"success": False, "message": str(e)}}

@frappe.whitelist()
def validate_location(restaurant_id, user_latitude, user_longitude):
    """Enhanced location validation with detailed reporting"""
    try:
        # Get restaurant location data
        restaurant = frappe.get_doc("Restaurant", restaurant_id)
        
        if not restaurant.latitude or not restaurant.longitude:
            return {
                "success": False,
                "message": "Restaurant location not configured. Please contact administrator."
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
        
        # Log location check
        frappe.get_doc({
            "doctype": "Location Check Log",
            "restaurant": restaurant_id,
            "user": frappe.session.user,
            "check_time": now_datetime(),
            "user_latitude": float(user_latitude),
            "user_longitude": float(user_longitude),
            "calculated_distance": distance,
            "is_within_range": is_within_range
        }).insert(ignore_permissions=True)
        
        return {
            "success": True,
            "is_within_range": is_within_range,
            "distance": round(distance, 2),
            "allowed_radius": restaurant.location_radius,
            "restaurant_location": {
                "latitude": restaurant.latitude,
                "longitude": restaurant.longitude
            },
            "message": "Location verified successfully" if is_within_range 
                      else f"You are {round(distance, 2)}m away from the restaurant. You must be within {restaurant.location_radius}m to perform an audit."
        }
        
    except Exception as e:
        frappe.log_error(f"Location validation error: {str(e)}")
        return {
            "success": False,
            "message": f"Location validation failed: {str(e)}"
        }


@frappe.whitelist()
def save_audit_progress(restaurant_id, answers, overall_comment="", category_progress=None):
    """Save audit progress for later completion"""
    try:
        current_user = frappe.session.user
        answers = json.loads(answers) if isinstance(answers, str) else answers
        
        # Check for existing progress
        existing_progress = frappe.db.exists("Audit Progress", {
            "restaurant": restaurant_id,
            "auditor": current_user,
            "is_completed": 0
        })
        
        if existing_progress:
            progress_doc = frappe.get_doc("Audit Progress", existing_progress)
        else:
            progress_doc = frappe.new_doc("Audit Progress")
            progress_doc.restaurant = restaurant_id
            progress_doc.auditor = current_user
            progress_doc.start_time = now_datetime()
        
        progress_doc.last_updated = now_datetime()
        progress_doc.overall_comment = overall_comment
        progress_doc.answers_json = json.dumps(answers)
        progress_doc.total_questions = len(answers)
        
        if category_progress:
            progress_doc.category_progress = json.dumps(category_progress)
        
        if existing_progress:
            progress_doc.save(ignore_permissions=True)
        else:
            progress_doc.insert(ignore_permissions=True)
        
        frappe.db.commit()
        
        return {
            "success": True,
            "progress_id": progress_doc.name,
            "message": "Progress saved successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error saving progress: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to save progress: {str(e)}"
        }


@frappe.whitelist()
def get_audit_progress(restaurant_id):
    """Retrieve saved audit progress"""
    try:
        current_user = frappe.session.user
        
        progress = frappe.db.get_value("Audit Progress", {
            "restaurant": restaurant_id,
            "auditor": current_user,
            "is_completed": 0
        }, ["name", "answers_json", "overall_comment", "category_progress", "last_updated", "start_time"], as_dict=True)
        
        if not progress:
            return {"success": True, "has_progress": False}
        
        answers = json.loads(progress.answers_json) if progress.answers_json else {}
        category_progress = json.loads(progress.category_progress) if progress.category_progress else {}
        
        return {
            "success": True,
            "has_progress": True,
            "progress_id": progress.name,
            "answers": answers,
            "overall_comment": progress.overall_comment or "",
            "category_progress": category_progress,
            "last_updated": progress.last_updated,
            "start_time": progress.start_time
        }
        
    except Exception as e:
        frappe.log_error(f"Error loading progress: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to load progress: {str(e)}"
        }


@frappe.whitelist()
def submit_audit(restaurant_id, answers, overall_comment="", progress_id=None):
    """Enhanced audit submission with better error handling and validation"""
    try:
        current_user = frappe.session.user
        answers = json.loads(answers) if isinstance(answers, str) else answers

        # Validate submission
        if not answers:
            return {"success": False, "message": "No answers provided"}

        # Create audit submission
        audit_submission = frappe.new_doc("Audit Submission")
        audit_submission.restaurant = restaurant_id
        audit_submission.auditor = current_user
        audit_submission.audit_date = now_datetime().date()
        audit_submission.audit_time = now_datetime().time()
        audit_submission.overall_comment = overall_comment
        
        # Calculate audit score
        total_score = 0
        scored_questions = 0
        
        # Insert submission first to get name for file attachments
        audit_submission.insert(ignore_permissions=True)
        
        # Process answers
        for answer_data in answers:
            answer_row = audit_submission.append("answers", {})
            question_id = answer_data.get("question_id")
            
            # Get question details
            question_doc = frappe.get_doc("Audit Question", question_id)
            
            answer_row.question = question_id
            answer_row.question_text = question_doc.question_text
            answer_row.answer_value = answer_data.get("answer_value")
            answer_row.answer_comment = answer_data.get("answer_comment", "")
            answer_row.category = answer_data.get("category")
            
            # Handle selected options
            selected_options = answer_data.get("selected_options", [])
            if selected_options:
                answer_row.selected_options = json.dumps(selected_options)
            
            # Calculate score for rating questions
            if question_doc.answer_type == "Rating" and answer_data.get("answer_value"):
                try:
                    score = int(answer_data.get("answer_value", 0))
                    total_score += score
                    scored_questions += 1
                except (ValueError, TypeError):
                    pass
            
            # Handle image attachments
            if answer_data.get("image_data"):
                try:
                    image_base64 = answer_data["image_data"]
                    if "," in image_base64:
                        image_content = base64.b64decode(image_base64.split(",")[1])
                        filename = f"audit_{audit_submission.name}_{question_id}_{frappe.generate_hash(length=6)}.png"
                        
                        _file = frappe.get_doc({
                            "doctype": "File",
                            "file_name": filename,
                            "content": image_content,
                            "attached_to_doctype": "Audit Submission",
                            "attached_to_name": audit_submission.name,
                            "attached_to_field": "answers",
                            "is_private": 0
                        })
                        _file.save(ignore_permissions=True)
                        
                        answer_row.image_attachment = _file.file_url
                except Exception as img_err:
                    frappe.log_error(f"Error saving image for question {question_id}: {str(img_err)}")
        
        # Calculate final score
        if scored_questions > 0:
            audit_submission.average_score = round(total_score / scored_questions, 2)
            audit_submission.total_score = total_score
            audit_submission.max_possible_score = scored_questions * 5
        
        # Add metadata
        audit_submission.submission_time = now_datetime()
        audit_submission.total_questions = len(answers)
        audit_submission.questions_with_images = len([a for a in answers if a.get("image_data")])
        audit_submission.questions_with_comments = len([a for a in answers if a.get("answer_comment")])
        
        # Save final submission
        audit_submission.save(ignore_permissions=True)
        
        # Mark progress as completed if it exists
        if progress_id:
            try:
                progress_doc = frappe.get_doc("Audit Progress", progress_id)
                progress_doc.is_completed = 1
                progress_doc.completed_time = now_datetime()
                progress_doc.audit_submission = audit_submission.name
                progress_doc.save(ignore_permissions=True)
            except Exception:
                pass  # Progress document might not exist
        
        frappe.db.commit()

        # Generate audit summary
        summary = generate_audit_summary(audit_submission)
        
        return {
            "success": True,
            "submission_id": audit_submission.name,
            "average_score": audit_submission.average_score,
            "total_questions": audit_submission.total_questions,
            "summary": summary,
            "message": "Audit submitted successfully"
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Submit audit error: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to submit audit: {str(e)}"
        }


def generate_audit_summary(audit_submission):
    """Generate a summary of the audit results"""
    try:
        summary = {
            "restaurant_name": frappe.db.get_value("Restaurant", audit_submission.restaurant, "restaurant_name"),
            "audit_date": audit_submission.audit_date,
            "auditor": audit_submission.auditor,
            "total_questions": audit_submission.total_questions,
            "average_score": audit_submission.average_score,
            "categories": {}
        }
        
        # Group answers by category
        for answer in audit_submission.answers:
            if answer.category not in summary["categories"]:
                summary["categories"][answer.category] = {
                    "questions": 0,
                    "total_score": 0,
                    "scored_questions": 0
                }
            
            summary["categories"][answer.category]["questions"] += 1
            
            # Add score if it's a rating question
            try:
                if answer.answer_value and answer.answer_value.isdigit():
                    score = int(answer.answer_value)
                    if 1 <= score <= 5:
                        summary["categories"][answer.category]["total_score"] += score
                        summary["categories"][answer.category]["scored_questions"] += 1
            except (ValueError, AttributeError):
                pass
        
        # Calculate category averages
        for category in summary["categories"]:
            cat_data = summary["categories"][category]
            if cat_data["scored_questions"] > 0:
                cat_data["average_score"] = round(cat_data["total_score"] / cat_data["scored_questions"], 2)
            else:
                cat_data["average_score"] = 0
        
        return summary
        
    except Exception as e:
        frappe.log_error(f"Error generating audit summary: {str(e)}")
        return {}


@frappe.whitelist()
def get_audit_history(restaurant_id=None, limit=20, offset=0):
    """Enhanced audit history with filtering and pagination"""
    try:
        current_user = frappe.session.user
        conditions = []
        params = []
        
        # Filter by restaurant if specified
        if restaurant_id:
            conditions.append("s.restaurant = %s")
            params.append(restaurant_id)
        
        # Filter by user access (non-System Manager users see only their restaurants)
        if "System Manager" not in frappe.get_roles():
            employee = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
            if employee:
                conditions.append("""
                    s.restaurant IN (
                        SELECT r.name FROM `tabRestaurant` r
                        JOIN `tabRestaurant Employee` re ON re.parent = r.name
                        WHERE re.employee = %s
                    )
                """)
                params.append(employee)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Get audit submissions with enhanced data
        submissions = frappe.db.sql(f"""
            SELECT 
                s.name,
                s.restaurant,
                r.restaurant_name,
                s.auditor,
                u.full_name as auditor_name,
                s.audit_date,
                s.audit_time,
                s.overall_comment,
                s.average_score,
                s.total_questions,
                s.questions_with_images,
                s.questions_with_comments,
                s.submission_time,
                COUNT(a.name) as total_answers
            FROM `tabAudit Submission` s
            LEFT JOIN `tabRestaurant` r ON r.name = s.restaurant
            LEFT JOIN `tabUser` u ON u.name = s.auditor
            LEFT JOIN `tabAudit Answer` a ON a.parent = s.name
            {where_clause}
            GROUP BY s.name
            ORDER BY s.audit_date DESC, s.audit_time DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset], as_dict=True)
        
        # Get total count for pagination
        count_query = f"""
            SELECT COUNT(DISTINCT s.name) as total
            FROM `tabAudit Submission` s
            LEFT JOIN `tabRestaurant` r ON r.name = s.restaurant
            {where_clause}
        """
        
        total_count = frappe.db.sql(count_query, params, as_dict=True)[0].total if params else frappe.db.sql(count_query, as_dict=True)[0].total
        
        # Enhance submissions with category breakdown
        for submission in submissions:
            # Get category-wise scores
            category_scores = frappe.db.sql("""
                SELECT 
                    a.category,
                    cc.category_name,
                    COUNT(*) as question_count,
                    AVG(CASE 
                        WHEN a.answer_value REGEXP '^[1-5]
     
                        THEN CAST(a.answer_value AS UNSIGNED) 
                        ELSE NULL 
                    END) as avg_score
                FROM `tabAudit Answer` a
                LEFT JOIN `tabChecklist Category` cc ON cc.name = a.category
                WHERE a.parent = %s AND a.category IS NOT NULL
                GROUP BY a.category
            """, (submission.name,), as_dict=True)
            
            submission.category_breakdown = category_scores
            
            # Format dates for display
            submission.audit_datetime = f"{submission.audit_date} {submission.audit_time}"
            submission.days_ago = (frappe.utils.getdate() - submission.audit_date).days
        
        return {
            "success": True,
            "submissions": submissions,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_next": (offset + limit) < total_count,
                "has_prev": offset > 0
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting audit history: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to load audit history: {str(e)}"
        }


@frappe.whitelist()
def get_audit_analytics(restaurant_id=None, date_range=30):
    """Get audit analytics and trends"""
    try:
        current_user = frappe.session.user
        conditions = []
        params = []
        
        # Date range filter
        from_date = frappe.utils.add_days(frappe.utils.getdate(), -int(date_range))
        conditions.append("s.audit_date >= %s")
        params.append(from_date)
        
        # Restaurant filter
        if restaurant_id:
            conditions.append("s.restaurant = %s")
            params.append(restaurant_id)
        
        # User access filter
        if "System Manager" not in frappe.get_roles():
            employee = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
            if employee:
                conditions.append("""
                    s.restaurant IN (
                        SELECT r.name FROM `tabRestaurant` r
                        JOIN `tabRestaurant Employee` re ON re.parent = r.name
                        WHERE re.employee = %s
                    )
                """)
                params.append(employee)
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        # Get trend data
        trends = frappe.db.sql(f"""
            SELECT 
                DATE(s.audit_date) as audit_date,
                COUNT(*) as audit_count,
                AVG(s.average_score) as avg_score,
                MIN(s.average_score) as min_score,
                MAX(s.average_score) as max_score
            FROM `tabAudit Submission` s
            {where_clause}
            GROUP BY DATE(s.audit_date)
            ORDER BY audit_date
        """, params, as_dict=True)
        
        # Get category performance
        category_performance = frappe.db.sql(f"""
            SELECT 
                cc.category_name,
                COUNT(*) as question_count,
                AVG(CASE 
                    WHEN a.answer_value REGEXP '^[1-5]
     
                    THEN CAST(a.answer_value AS UNSIGNED) 
                    ELSE NULL 
                END) as avg_score
            FROM `tabAudit Submission` s
            JOIN `tabAudit Answer` a ON a.parent = s.name
            LEFT JOIN `tabChecklist Category` cc ON cc.name = a.category
            {where_clause} AND a.category IS NOT NULL
            GROUP BY a.category
            ORDER BY avg_score DESC
        """, params, as_dict=True)
        
        # Get restaurant performance (if not filtering by specific restaurant)
        restaurant_performance = []
        if not restaurant_id:
            restaurant_performance = frappe.db.sql(f"""
                SELECT 
                    r.restaurant_name,
                    COUNT(DISTINCT s.name) as audit_count,
                    AVG(s.average_score) as avg_score,
                    MAX(s.audit_date) as last_audit_date
                FROM `tabAudit Submission` s
                JOIN `tabRestaurant` r ON r.name = s.restaurant
                {where_clause}
                GROUP BY s.restaurant
                ORDER BY avg_score DESC
            """, params, as_dict=True)
        
        # Calculate summary statistics
        summary_stats = frappe.db.sql(f"""
            SELECT 
                COUNT(DISTINCT s.name) as total_audits,
                COUNT(DISTINCT s.restaurant) as restaurants_audited,
                COUNT(DISTINCT s.auditor) as active_auditors,
                AVG(s.average_score) as overall_avg_score,
                SUM(s.total_questions) as total_questions_answered
            FROM `tabAudit Submission` s
            {where_clause}
        """, params, as_dict=True)[0]
        
        return {
            "success": True,
            "analytics": {
                "summary": summary_stats,
                "trends": trends,
                "category_performance": category_performance,
                "restaurant_performance": restaurant_performance,
                "date_range": {
                    "from": from_date,
                    "to": frappe.utils.getdate(),
                    "days": date_range
                }
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting audit analytics: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to load analytics: {str(e)}"
        }


@frappe.whitelist()
def get_restaurant_score_trends(restaurant_id, months=6):
    """Get score trends for a specific restaurant"""
    try:
        from_date = frappe.utils.add_months(frappe.utils.getdate(), -int(months))
        
        trends = frappe.db.sql("""
            SELECT 
                YEAR(audit_date) as year,
                MONTH(audit_date) as month,
                COUNT(*) as audit_count,
                AVG(average_score) as avg_score,
                MIN(average_score) as min_score,
                MAX(average_score) as max_score
            FROM `tabAudit Submission`
            WHERE restaurant = %s AND audit_date >= %s
            GROUP BY YEAR(audit_date), MONTH(audit_date)
            ORDER BY year, month
        """, (restaurant_id, from_date), as_dict=True)
        
        # Format month names
        import calendar
        for trend in trends:
            trend.month_name = calendar.month_name[trend.month]
            trend.period = f"{trend.month_name} {trend.year}"
        
        return {
            "success": True,
            "restaurant": frappe.db.get_value("Restaurant", restaurant_id, "restaurant_name"),
            "trends": trends,
            "period": f"Last {months} months"
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting restaurant trends: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to load trends: {str(e)}"
        }


@frappe.whitelist()
def delete_audit_progress(progress_id):
    """Delete saved audit progress"""
    try:
        current_user = frappe.session.user
        
        # Verify ownership
        progress_doc = frappe.get_doc("Audit Progress", progress_id)
        if progress_doc.auditor != current_user:
            return {
                "success": False,
                "message": "You can only delete your own progress"
            }
        
        frappe.delete_doc("Audit Progress", progress_id)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": "Progress deleted successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error deleting progress: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to delete progress: {str(e)}"
        }


@frappe.whitelist()
def get_user_dashboard():
    """Get dashboard data for current user"""
    try:
        current_user = frappe.session.user
        
        # Get user's restaurant assignments
        employee = frappe.db.get_value("Employee", {"user_id": current_user}, "name")
        
        if not employee and "System Manager" not in frappe.get_roles():
            return {
                "success": False,
                "message": "Employee record not found"
            }
        
        # Get recent audits
        recent_audits = frappe.db.sql("""
            SELECT 
                s.name,
                r.restaurant_name,
                s.audit_date,
                s.average_score,
                s.total_questions
            FROM `tabAudit Submission` s
            JOIN `tabRestaurant` r ON r.name = s.restaurant
            WHERE s.auditor = %s
            ORDER BY s.audit_date DESC, s.audit_time DESC
            LIMIT 5
        """, (current_user,), as_dict=True)
        
        # Get pending progress
        pending_progress = frappe.db.sql("""
            SELECT 
                p.name,
                r.restaurant_name,
                p.last_updated,
                p.total_questions
            FROM `tabAudit Progress` p
            JOIN `tabRestaurant` r ON r.name = p.restaurant
            WHERE p.auditor = %s AND p.is_completed = 0
            ORDER BY p.last_updated DESC
        """, (current_user,), as_dict=True)
        
        # Get user statistics
        user_stats = frappe.db.sql("""
            SELECT 
                COUNT(DISTINCT s.name) as total_audits,
                COUNT(DISTINCT s.restaurant) as restaurants_audited,
                AVG(s.average_score) as avg_score,
                MAX(s.audit_date) as last_audit_date
            FROM `tabAudit Submission` s
            WHERE s.auditor = %s
        """, (current_user,), as_dict=True)[0]
        
        return {
            "success": True,
            "dashboard": {
                "user": {
                    "name": current_user,
                    "full_name": frappe.db.get_value("User", current_user, "full_name"),
                    "employee": employee
                },
                "stats": user_stats,
                "recent_audits": recent_audits,
                "pending_progress": pending_progress
            }
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting user dashboard: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to load dashboard: {str(e)}"
        }