# Copyright (c) 2025, Ontime Solutions and contributors
# For license information, please see license.txt

# Copyright (c) 2025, Restaurant Audit App and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days, formatdate

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    charts = get_charts(data)
    return columns, data, None, charts

def get_columns():
    return [
        {
            "fieldname": "week_range",
            "label": _("Week Range"),
            "fieldtype": "Data",
            "width": 200
        },
        {
            "fieldname": "restaurant",
            "label": _("Restaurant"),
            "fieldtype": "Link",
            "options": "Restaurant",
            "width": 180
        },
        {
            "fieldname": "auditor",
            "label": _("Auditor"),
            "fieldtype": "Link",
            "options": "User",
            "width": 150
        },
        {
            "fieldname": "scheduled_count",
            "label": _("Scheduled"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "completed_count",
            "label": _("Completed"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "overdue_count",
            "label": _("Overdue"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "pending_count",
            "label": _("Pending"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "completion_rate",
            "label": _("Completion %"),
            "fieldtype": "Percent",
            "width": 120
        },
        {
            "fieldname": "daily_audits",
            "label": _("Daily Audits"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "daily_completed",
            "label": _("Daily Completed"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "status",
            "label": _("Week Status"),
            "fieldtype": "Data",
            "width": 120
        }
    ]

def get_data(filters):
    data = []
    
    # Calculate date ranges
    if filters.get("from_date") and filters.get("to_date"):
        from_date = getdate(filters.get("from_date"))
        to_date = getdate(filters.get("to_date"))
    else:
        # Default to last 4 weeks
        today = getdate()
        days_since_monday = today.weekday()
        current_week_start = add_days(today, -days_since_monday)
        from_date = add_days(current_week_start, -21)  # 3 weeks back
        to_date = add_days(current_week_start, 6)  # End of current week
    
    # Get all restaurants
    restaurants = frappe.get_all("Restaurant", 
       
        fields=["name", "restaurant_name"]
    )
    
    # Process week by week
    current_date = from_date
    while current_date <= to_date:
        # Calculate week start (Monday) and end (Sunday)
        days_since_monday = current_date.weekday()
        week_start = add_days(current_date, -days_since_monday)
        week_end = add_days(week_start, 6)
        
        if week_start > to_date:
            break
            
        week_range = f"{formatdate(week_start, 'MMM dd')} - {formatdate(week_end, 'MMM dd, yyyy')}"
        
        for restaurant in restaurants:
            # Get all auditors for this restaurant
            auditors = frappe.get_all("Restaurant Employee",
                filters={"parent": restaurant.name, "is_active": 1},
                fields=["employee"]
            )
            
            for auditor_emp in auditors:
                # Get user_id for this employee
                employee_doc = frappe.get_value("Employee", auditor_emp.employee, "user_id")
                if not employee_doc:
                    continue
                    
                # Get scheduled audits for this week
                scheduled_audits = frappe.get_all("Scheduled Audit Visit",
                    filters={
                        "restaurant": restaurant.name,
                        "auditor": employee_doc,
                        "visit_date": ["between", [week_start, week_end]]
                    },
                    fields=["status"]
                )
                
                # Get daily audits for this week
                daily_audits = frappe.get_all("Audit Progress",
                    filters={
                        "restaurant": restaurant.name,
                        "auditor": employee_doc,
                        "start_time": ["between", [f"{week_start} 00:00:00", f"{week_end} 23:59:59"]]
                    },
                    fields=["is_completed"]
                )
                
                if not scheduled_audits and not daily_audits:
                    continue
                
                # Calculate metrics
                scheduled_count = len(scheduled_audits)
                completed_count = len([a for a in scheduled_audits if a.status == "Completed"])
                overdue_count = len([a for a in scheduled_audits if a.status == "Overdue"])
                pending_count = len([a for a in scheduled_audits if a.status == "Pending"])
                
                daily_count = len(daily_audits)
                daily_completed_count = len([a for a in daily_audits if a.is_completed])
                
                completion_rate = (completed_count / scheduled_count * 100) if scheduled_count > 0 else 0
                
                # Determine week status
                if overdue_count > 0:
                    status = "⚠️ Has Overdue"
                elif pending_count > 0:
                    status = "⏳ In Progress"
                elif completed_count == scheduled_count and scheduled_count > 0:
                    status = "✅ Complete"
                else:
                    status = "📝 No Audits"
                
                data.append({
                    "week_range": week_range,
                    "restaurant": restaurant.name,
                    "auditor": employee_doc,
                    "scheduled_count": scheduled_count,
                    "completed_count": completed_count,
                    "overdue_count": overdue_count,
                    "pending_count": pending_count,
                    "completion_rate": completion_rate,
                    "daily_audits": daily_count,
                    "daily_completed": daily_completed_count,
                    "status": status
                })
        
        # Move to next week
        current_date = add_days(week_end, 1)
    
    return data

def get_charts(data):
    if not data:
        return []
    
    # Completion rate chart
    week_labels = []
    completion_rates = []
    overdue_counts = []
    
    # Group by week
    week_data = {}
    for row in data:
        week = row["week_range"]
        if week not in week_data:
            week_data[week] = {"completion_rates": [], "overdue_count": 0}
        
        if row["scheduled_count"] > 0:
            week_data[week]["completion_rates"].append(row["completion_rate"])
        week_data[week]["overdue_count"] += row["overdue_count"]
    
    for week, metrics in week_data.items():
        week_labels.append(week)
        avg_completion = sum(metrics["completion_rates"]) / len(metrics["completion_rates"]) if metrics["completion_rates"] else 0
        completion_rates.append(avg_completion)
        overdue_counts.append(metrics["overdue_count"])
    
    charts = [
        {
            "name": "Weekly Completion Rates",
            "chart_name": _("Weekly Completion Rates"),
            "chart_type": "line",
            "data": {
                "labels": week_labels,
                "datasets": [
                    {
                        "name": "Completion Rate %",
                        "values": completion_rates
                    }
                ]
            }
        },
        {
            "name": "Overdue Audits by Week",
            "chart_name": _("Overdue Audits by Week"),
            "chart_type": "bar",
            "data": {
                "labels": week_labels,
                "datasets": [
                    {
                        "name": "Overdue Count",
                        "values": overdue_counts
                    }
                ]
            }
        }
    ]
    
    return charts