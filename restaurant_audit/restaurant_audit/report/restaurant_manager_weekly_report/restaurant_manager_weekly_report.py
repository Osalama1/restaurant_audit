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
            "fieldname": "manager",
            "label": _("Manager"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 150
        },
        {
            "fieldname": "week_range",
            "label": _("Week Period"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "scheduled_audits",
            "label": _("Scheduled Audits"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "completed_audits",
            "label": _("Completed"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "overdue_audits",
            "label": _("Overdue"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "daily_expected",
            "label": _("Daily Expected"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "daily_completed",
            "label": _("Daily Done"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "daily_missed",
            "label": _("Daily Missed"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "overall_score",
            "label": _("Avg Score"),
            "fieldtype": "Float",
            "precision": 1,
            "width": 100
        },
        {
            "fieldname": "compliance_rate",
            "label": _("Compliance %"),
            "fieldtype": "Percent",
            "width": 120
        },
        {
            "fieldname": "status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "action_required",
            "label": _("Action Required"),
            "fieldtype": "Data",
            "width": 200
        }
    ]

def get_data(filters):
    data = []
    
    # Get date range
    if filters.get("from_date") and filters.get("to_date"):
        from_date = getdate(filters.get("from_date"))
        to_date = getdate(filters.get("to_date"))
    else:
        # Default to current week
        today = getdate(nowdate())  # convert string → date
        days_since_monday = today.weekday()
        from_date = add_days(today, -days_since_monday)
        to_date = add_days(from_date, 6)

    
    week_range = f"{formatdate(from_date, 'MMM dd')} - {formatdate(to_date, 'MMM dd, yyyy')}"
    
    # Filter by restaurant manager if specified
    restaurant_filters=None
    if filters.get("restaurant_manager"):
        restaurant_filters["restaurant_manager"] = filters.get("restaurant_manager")
    
    # Get all restaurants
    restaurants = frappe.get_all("Restaurant",
        filters=restaurant_filters,
        fields=["name", "restaurant_name", "restaurant_manager"]
    )
    
    for restaurant in restaurants:
        # Get manager details
        manager_name = None
        if restaurant.restaurant_manager:
            manager_name = frappe.get_value("Employee", restaurant.restaurant_manager, "employee_name")
        
        # Get assigned auditors for this restaurant
        assigned_employees = frappe.get_all("Restaurant Employee",
            filters={"parent": restaurant.name, "is_active": 1},
            fields=["employee"]
        )
        
        if not assigned_employees:
            # No auditors assigned
            data.append({
                "restaurant": restaurant.name,
                "restaurant_name": restaurant.restaurant_name,
                "manager": restaurant.restaurant_manager,
                "week_range": week_range,
                "scheduled_audits": 0,
                "completed_audits": 0,
                "overdue_audits": 0,
                "daily_expected": 0,
                "daily_completed": 0,
                "daily_missed": 0,
                "overall_score": 0,
                "compliance_rate": 0,
                "status": "🚫 No Auditors",
                "action_required": "❗ Assign auditors to this restaurant"
            })
            continue
        
        # Collect all auditors for this restaurant
        auditors = []
        for emp in assigned_employees:
            user_id = frappe.get_value("Employee", emp.employee, "user_id")
            if user_id:
                auditors.append(user_id)
        
        if not auditors:
            continue
        
        # Get scheduled audits for this week
        scheduled_audits = frappe.get_all("Scheduled Audit Visit",
            filters={
                "restaurant": restaurant.name,
                "auditor": ["in", auditors],
                "visit_date": ["between", [from_date, to_date]]
            },
            fields=["status", "auditor", "visit_date"]
        )
        
        # Get daily audits for this week
        daily_audits = frappe.get_all("Audit Progress",
            filters={
                "restaurant": restaurant.name,
                "auditor": ["in", auditors],
                "start_time": ["between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]]
            },
            fields=["is_completed", "auditor", "start_time"]
        )
        
        # Get audit submissions for scoring
        audit_submissions = frappe.get_all("Audit Submission",
            filters={
                "restaurant": restaurant.name,
                "auditor": ["in", auditors],
                "audit_date": ["between", [from_date, to_date]]
            },
            fields=["average_score"]
        )
        
        # Calculate metrics
        scheduled_count = len(scheduled_audits)
        completed_count = len([a for a in scheduled_audits if a.status == "Completed"])
        overdue_count = len([a for a in scheduled_audits if a.status == "Overdue"])
        
        # Daily audit metrics
        daily_completed_count = len([a for a in daily_audits if a.is_completed])
        daily_expected = 7 * len(auditors)  # Each auditor should do daily audit each day
        daily_missed = daily_expected - daily_completed_count
        
        # Calculate average score
        if audit_submissions:
            overall_score = sum([a.average_score for a in audit_submissions if a.average_score]) / len(audit_submissions)
        else:
            overall_score = 0
        
        # Calculate compliance rate
        total_expected = scheduled_count + daily_expected
        total_completed = completed_count + daily_completed_count
        compliance_rate = (total_completed / total_expected * 100) if total_expected > 0 else 0
        
        # Determine status and action required
        if overdue_count > 0:
            status = "🔴 Critical"
            action_required = f"❗ {overdue_count} overdue audits need immediate attention"
        elif daily_missed > (daily_expected * 0.3):  # More than 30% daily audits missed
            status = "🟠 Needs Attention"
            action_required = f"⚠️ {daily_missed} daily audits missed this week"
        elif compliance_rate >= 80:
            status = "🟢 Good"
            action_required = "✅ Keep up the good work"
        else:
            status = "🟡 Monitor"
            action_required = "📈 Improve audit completion rate"
        
        data.append({
            "restaurant": restaurant.name,
            "restaurant_name": restaurant.restaurant_name,
            "manager": restaurant.restaurant_manager,
            "week_range": week_range,
            "scheduled_audits": scheduled_count,
            "completed_audits": completed_count,
            "overdue_audits": overdue_count,
            "daily_expected": daily_expected,
            "daily_completed": daily_completed_count,
            "daily_missed": daily_missed,
            "overall_score": round(overall_score, 1),
            "compliance_rate": round(compliance_rate, 1),
            "status": status,
            "action_required": action_required
        })
    
    # Sort by compliance rate (worst first)
    data.sort(key=lambda x: x["compliance_rate"])
    return data

def get_summary(data):
    if not data:
        return []
    
    total_restaurants = len(data)
    critical_restaurants = len([d for d in data if "🔴" in d["status"]])
    good_restaurants = len([d for d in data if "🟢" in d["status"]])
    
    total_overdue = sum([d["overdue_audits"] for d in data])
    total_missed_daily = sum([d["daily_missed"] for d in data])
    
    avg_compliance = sum([d["compliance_rate"] for d in data]) / total_restaurants if total_restaurants > 0 else 0
    
    summary = [
        {
            "label": _("Total Restaurants"),
            "value": total_restaurants,
            "indicator": "blue"
        },
        {
            "label": _("Critical Status"),
            "value": critical_restaurants,
            "indicator": "red"
        },
        {
            "label": _("Good Status"),
            "value": good_restaurants,
            "indicator": "green"
        },
        {
            "label": _("Total Overdue Audits"),
            "value": total_overdue,
            "indicator": "red"
        },
        {
            "label": _("Total Missed Daily"),
            "value": total_missed_daily,
            "indicator": "orange"
        },
        {
            "label": _("Average Compliance Rate"),
            "value": f"{round(avg_compliance, 1)}%",
            "indicator": "green" if avg_compliance >= 80 else "orange" if avg_compliance >= 60 else "red"
        }
    ]
    
    return summary

def get_charts(data):
    if not data:
        return []
    
    # Compliance rate by restaurant
    restaurant_names = [d["restaurant_name"][:15] + "..." if len(d["restaurant_name"]) > 15 else d["restaurant_name"] for d in data]
    compliance_rates = [d["compliance_rate"] for d in data]
    overdue_counts = [d["overdue_audits"] for d in data]
    
    # Status distribution
    status_counts = {}
    for d in data:
        status_key = d["status"].split()[1] if len(d["status"].split()) > 1 else d["status"]
        status_counts[status_key] = status_counts.get(status_key, 0) + 1
    
    charts = [
        {
            "name": "Compliance Rate by Restaurant",
            "chart_name": _("Compliance Rate by Restaurant"),
            "chart_type": "bar",
            "data": {
                "labels": restaurant_names,
                "datasets": [
                    {
                        "name": "Compliance %",
                        "values": compliance_rates
                    }
                ]
            }
        },
        {
            "name": "Overdue Audits by Restaurant",
            "chart_name": _("Overdue Audits by Restaurant"),
            "chart_type": "bar",
            "data": {
                "labels": restaurant_names,
                "datasets": [
                    {
                        "name": "Overdue Count",
                        "values": overdue_counts
                    }
                ]
            }
        },
        {
            "name": "Restaurant Status Distribution",
            "chart_name": _("Restaurant Status Distribution"),
            "chart_type": "donut",
            "data": {
                "labels": list(status_counts.keys()),
                "datasets": [
                    {
                        "name": "Restaurant Count",
                        "values": list(status_counts.values())
                    }
                ]
            }
        }
    ]
    
    return charts