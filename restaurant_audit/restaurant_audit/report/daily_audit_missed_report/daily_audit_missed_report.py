# Copyright (c) 2025, Ontime Solutions and contributors
# For license information, please see license.txt

# import frappe

# Copyright (c) 2025, Restaurant Audit App and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days, formatdate, nowdate

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    summary = get_summary(data)
    charts = get_charts(data)
    return columns, data, summary, charts

def get_columns():
    return [
        {
            "fieldname": "date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "restaurant",
            "label": _("Restaurant"),
            "fieldtype": "Link",
            "options": "Restaurant",
            "width": 180
        },
        {
            "fieldname": "restaurant_name",
            "label": _("Restaurant Name"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "auditor",
            "label": _("Auditor"),
            "fieldtype": "Link",
            "options": "User",
            "width": 150
        },
        {
            "fieldname": "template_name",
            "label": _("Template"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "progress_status",
            "label": _("Progress Status"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "completion_percentage",
            "label": _("Completion %"),
            "fieldtype": "Percent",
            "width": 120
        },
        {
            "fieldname": "start_time",
            "label": _("Started At"),
            "fieldtype": "Datetime",
            "width": 140
        },
        {
            "fieldname": "days_overdue",
            "label": _("Days Overdue"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "status_indicator",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 100
        }
    ]

def get_data(filters):
    data = []
    
    # Get date range
    if filters.get("from_date") and filters.get("to_date"):
        from_date = getdate(filters.get("from_date"))
        to_date = getdate(filters.get("to_date"))
    else:

        # Default to last 7 days
        today = getdate(nowdate())   # <-- FIX
        from_date = add_days(today, -7)
        to_date = today
        from_date = getdate(from_date)  # ensure date
        to_date = getdate(to_date)      # ensure date
       	
    
    # Get all daily audit templates
    templates = frappe.get_all("Daily Audit Template",
        filters={"is_active": 1},
        fields=["name", "template_name", "restaurant", "applies_to_all_restaurants"]
    )
    
    # Get all restaurants
    restaurants = frappe.get_all("Restaurant",
      
        fields=["name", "restaurant_name"]
    )
    
    current_date = from_date
    while current_date <= to_date:
        current_date = getdate(current_date)
		
        for template in templates:
            # Determine which restaurants this template applies to
            target_restaurants = []
            if template.applies_to_all_restaurants:
                target_restaurants = restaurants
            elif template.restaurant:
                restaurant_doc = frappe.get_value("Restaurant", template.restaurant, 
                    ["name", "restaurant_name"], as_dict=True)
                if restaurant_doc:
                    target_restaurants = [restaurant_doc]
            
            for restaurant in target_restaurants:
                # Get all employees assigned to this restaurant
                assigned_employees = frappe.get_all("Restaurant Employee",
                    filters={"parent": restaurant.name, "is_active": 1},
                    fields=["employee"]
                )
                
                for emp in assigned_employees:
                    # Get user_id
                    employee_doc = frappe.get_value("Employee", emp.employee, "user_id")
                    if not employee_doc:
                        continue
                    
                    # Check if daily audit was done for this date
                    audit_progress = frappe.get_all("Audit Progress",
                        filters={
                            "restaurant": restaurant.name,
                            "auditor": employee_doc,
                            "start_time": ["between", [f"{current_date} 00:00:00", f"{current_date} 23:59:59"]]
                        },
                        fields=["name", "is_completed", "completion_percentage", "start_time", "total_questions", "answered_questions"]
                    )
                    
                    if not audit_progress:

                        # No daily audit attempted - MISSED
                        days_overdue = (to_date - current_date).days
                        data.append({
                            "date": current_date,
                            "restaurant": restaurant.name,
                            "restaurant_name": restaurant.restaurant_name,
                            "auditor": employee_doc,
                            "template_name": template.template_name,
                            "progress_status": "❌ Not Started",
                            "completion_percentage": 0,
                            "start_time": None,
                            "days_overdue": days_overdue,
                            "status_indicator": "🚫 MISSED"
                        })
                    else:
                        # Daily audit was attempted
                        progress = audit_progress[0]
                        if not progress.is_completed:
                            # Started but not completed - INCOMPLETE
                            days_overdue = (to_date - current_date).days
                            data.append({
                                "date": current_date,
                                "restaurant": restaurant.name,
                                "restaurant_name": restaurant.restaurant_name,
                                "auditor": employee_doc,
                                "template_name": template.template_name,
                                "progress_status": f"⏳ Incomplete ({progress.answered_questions or 0}/{progress.total_questions or 0})",
                                "completion_percentage": progress.completion_percentage or 0,
                                "start_time": progress.start_time,
                                "days_overdue": days_overdue,
                                "status_indicator": "⚠️ INCOMPLETE"
                            })
        
        current_date = add_days(current_date, 1)
    
    # Sort by days overdue (most overdue first)
    data.sort(key=lambda x: x["days_overdue"], reverse=True)
    return data

def get_summary(data):
    if not data:
        return []
    
    total_missed = len([d for d in data if d["status_indicator"] == "🚫 MISSED"])
    total_incomplete = len([d for d in data if d["status_indicator"] == "⚠️ INCOMPLETE"])
    total_issues = len(data)
    
    # Group by restaurant
    restaurant_issues = {}
    for row in data:
        restaurant = row["restaurant_name"]
        if restaurant not in restaurant_issues:
            restaurant_issues[restaurant] = 0
        restaurant_issues[restaurant] += 1
    
    # Find most problematic restaurant
    most_issues_restaurant = max(restaurant_issues.items(), key=lambda x: x[1]) if restaurant_issues else ("None", 0)
    
    summary = [
        {
            "label": _("Total Daily Audit Issues"),
            "value": total_issues,
            "indicator": "red" if total_issues > 0 else "green"
        },
        {
            "label": _("Completely Missed"),
            "value": total_missed,
            "indicator": "red"
        },
        {
            "label": _("Started but Incomplete"),
            "value": total_incomplete,
            "indicator": "orange"
        },
        {
            "label": _("Most Issues (Restaurant)"),
            "value": f"{most_issues_restaurant[0]} ({most_issues_restaurant[1]})",
            "indicator": "blue"
        }
    ]
    
    return summary

def get_charts(data):
    if not data:
        return []
    
    # Issues by restaurant
    restaurant_issues = {}
    for row in data:
        restaurant = row["restaurant_name"]
        if restaurant not in restaurant_issues:
            restaurant_issues[restaurant] = {"missed": 0, "incomplete": 0}
        
        if row["status_indicator"] == "🚫 MISSED":
            restaurant_issues[restaurant]["missed"] += 1
        else:
            restaurant_issues[restaurant]["incomplete"] += 1
    
    restaurant_labels = list(restaurant_issues.keys())
    missed_counts = [restaurant_issues[r]["missed"] for r in restaurant_labels]
    incomplete_counts = [restaurant_issues[r]["incomplete"] for r in restaurant_labels]
    
    # Issues by day
    daily_issues = {}
    for row in data:
        date_str = formatdate(row["date"], "MMM dd")
        if date_str not in daily_issues:
            daily_issues[date_str] = 0
        daily_issues[date_str] += 1
    
    daily_labels = list(daily_issues.keys())
    daily_counts = list(daily_issues.values())
    
    charts = [
        {
            "name": "Issues by Restaurant",
            "chart_name": _("Daily Audit Issues by Restaurant"),
            "chart_type": "bar",
            "data": {
                "labels": restaurant_labels,
                "datasets": [
                    {
                        "name": "Missed",
                        "values": missed_counts
                    },
                    {
                        "name": "Incomplete",
                        "values": incomplete_counts
                    }
                ]
            }
        },
        {
            "name": "Issues by Day",
            "chart_name": _("Daily Audit Issues Over Time"),
            "chart_type": "line",
            "data": {
                "labels": daily_labels,
                "datasets": [
                    {
                        "name": "Total Issues",
                        "values": daily_counts
                    }
                ]
            }
        }
    ]
    
    return charts