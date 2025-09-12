# Copyright (c) 2025, Ontime Solutions and contributors
# For license information, please see license.txt

# import frappe


# Copyright (c) 2025, Restaurant Audit App and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days, formatdate, nowdate, date_diff

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
            "fieldname": "auditor",
            "label": _("Auditor"),
            "fieldtype": "Link",
            "options": "User",
            "width": 150
        },
        {
            "fieldname": "auditor_name",
            "label": _("Auditor Name"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "visit_date",
            "label": _("Scheduled Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "days_overdue",
            "label": _("Days Overdue"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "week_range",
            "label": _("Week"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "priority",
            "label": _("Priority"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "manager",
            "label": _("Restaurant Manager"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 150
        },
        {
            "fieldname": "last_audit_date",
            "label": _("Last Audit"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "overdue_notified",
            "label": _("Notified"),
            "fieldtype": "Check",
            "width": 80
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
    
    # Get all overdue scheduled audits
    overdue_filters = {"status": "Overdue"}
    
    # Apply additional filters
    if filters.get("restaurant"):
        overdue_filters["restaurant"] = filters.get("restaurant")
    
    if filters.get("auditor"):
        overdue_filters["auditor"] = filters.get("auditor")
    
    if filters.get("from_date") and filters.get("to_date"):
        overdue_filters["visit_date"] = ["between", [filters.get("from_date"), filters.get("to_date")]]
    
    overdue_audits = frappe.get_all("Scheduled Audit Visit",
        filters=overdue_filters,
        fields=[
            "name", "restaurant", "restaurant_name", "auditor", "visit_date",
            "status", "overdue_notified", "week_start_date", "week_end_date"
        ],
        order_by="visit_date asc"
    )
    
    today = getdate(nowdate())
    
    for audit in overdue_audits:
        # Calculate days overdue
        visit_date = getdate(audit.visit_date)
        days_overdue = date_diff(today, visit_date)
        
        # Get auditor name
        auditor_name = frappe.get_value("User", audit.auditor, "full_name") or audit.auditor
        
        # Get restaurant manager
        restaurant_manager = frappe.get_value("Restaurant", audit.restaurant, "restaurant_manager")
        
        # Get last completed audit for this restaurant
        last_audit = frappe.get_value("Audit Submission",
            filters={"restaurant": audit.restaurant},
            fieldname="audit_date",
            order_by="audit_date desc"
        )
        
        # Determine priority based on days overdue
        if days_overdue >= 7:
            priority = "🔴 Critical"
        elif days_overdue >= 3:
            priority = "🟠 High"
        else:
            priority = "🟡 Medium"
        
        # Calculate week range
        if audit.week_start_date and audit.week_end_date:
            week_range = f"{formatdate(audit.week_start_date, 'MMM dd')} - {formatdate(audit.week_end_date, 'MMM dd')}"
        else:
            # Calculate week from visit date
            visit_date_obj = getdate(audit.visit_date)
            days_since_monday = visit_date_obj.weekday()
            week_start = add_days(visit_date_obj, -days_since_monday)
            week_end = add_days(week_start, 6)
            week_range = f"{formatdate(week_start, 'MMM dd')} - {formatdate(week_end, 'MMM dd')}"
        
        # Determine action required
        if days_overdue >= 14:
            action_required = "🚨 Escalate to management immediately"
        elif days_overdue >= 7:
            action_required = "📞 Contact auditor and manager urgently"
        elif days_overdue >= 3:
            action_required = "📧 Send reminder notification"
        else:
            action_required = "👀 Monitor closely"
        
        data.append({
            "restaurant": audit.restaurant,
            "restaurant_name": audit.restaurant_name,
            "auditor": audit.auditor,
            "auditor_name": auditor_name,
            "visit_date": audit.visit_date,
            "days_overdue": days_overdue,
            "week_range": week_range,
            "priority": priority,
            "manager": restaurant_manager,
            "last_audit_date": last_audit,
            "overdue_notified": audit.overdue_notified,
            "action_required": action_required
        })
    
    # Sort by days overdue (most overdue first)
    data.sort(key=lambda x: x["days_overdue"], reverse=True)
    return data

def get_summary(data):
    if not data:
        return []
    
    total_overdue = len(data)
    critical_overdue = len([d for d in data if "🔴" in d["priority"]])
    high_overdue = len([d for d in data if "🟠" in d["priority"]])
    
    # Most overdue audit
    most_overdue = max(data, key=lambda x: x["days_overdue"]) if data else None
    
    # Restaurant with most overdue audits
    restaurant_counts = {}
    for d in data:
        restaurant = d["restaurant_name"]
        restaurant_counts[restaurant] = restaurant_counts.get(restaurant, 0) + 1
    
    most_problematic_restaurant = max(restaurant_counts.items(), key=lambda x: x[1]) if restaurant_counts else ("None", 0)
    
    # Average days overdue
    avg_days_overdue = sum([d["days_overdue"] for d in data]) / len(data) if data else 0
    
    # Notification status
    notified_count = len([d for d in data if d["overdue_notified"]])
    not_notified_count = total_overdue - notified_count
    
    summary = [
        {
            "label": _("Total Overdue Audits"),
            "value": total_overdue,
            "indicator": "red"
        },
        {
            "label": _("Critical (7+ days)"),
            "value": critical_overdue,
            "indicator": "red"
        },
        {
            "label": _("High Priority (3+ days)"),
            "value": high_overdue,
            "indicator": "orange"
        },
        {
            "label": _("Average Days Overdue"),
            "value": f"{round(avg_days_overdue, 1)} days",
            "indicator": "blue"
        },
        {
            "label": _("Most Overdue"),
            "value": f"{most_overdue['days_overdue']} days ({most_overdue['restaurant_name']})" if most_overdue else "None",
            "indicator": "red"
        },
        {
            "label": _("Most Problematic Restaurant"),
            "value": f"{most_problematic_restaurant[0]} ({most_problematic_restaurant[1]} overdue)",
            "indicator": "orange"
        },
        {
            "label": _("Pending Notifications"),
            "value": not_notified_count,
            "indicator": "yellow"
        }
    ]
    
    return summary

def get_charts(data):
    if not data:
        return []
    
    # Overdue by restaurant
    restaurant_counts = {}
    for d in data:
        restaurant = d["restaurant_name"][:15] + "..." if len(d["restaurant_name"]) > 15 else d["restaurant_name"]
        restaurant_counts[restaurant] = restaurant_counts.get(restaurant, 0) + 1
    
    restaurant_labels = list(restaurant_counts.keys())
    restaurant_values = list(restaurant_counts.values())
    
    # Priority distribution
    priority_counts = {}
    for d in data:
        priority_key = d["priority"].split()[1] if len(d["priority"].split()) > 1 else d["priority"]
        priority_counts[priority_key] = priority_counts.get(priority_key, 0) + 1
    
    # Days overdue distribution
    days_ranges = {"1-2 days": 0, "3-6 days": 0, "7-13 days": 0, "14+ days": 0}
    for d in data:
        days = d["days_overdue"]
        if days <= 2:
            days_ranges["1-2 days"] += 1
        elif days <= 6:
            days_ranges["3-6 days"] += 1
        elif days <= 13:
            days_ranges["7-13 days"] += 1
        else:
            days_ranges["14+ days"] += 1
    
    # Trend over time (by week)
    week_counts = {}
    for d in data:
        week = d["week_range"]
        week_counts[week] = week_counts.get(week, 0) + 1
    
    charts = [
        {
            "name": "Overdue by Restaurant",
            "chart_name": _("Overdue Audits by Restaurant"),
            "chart_type": "bar",
            "data": {
                "labels": restaurant_labels,
                "datasets": [
                    {
                        "name": "Overdue Count",
                        "values": restaurant_values
                    }
                ]
            }
        },
        {
            "name": "Priority Distribution",
            "chart_name": _("Overdue Audits by Priority"),
            "chart_type": "donut",
            "data": {
                "labels": list(priority_counts.keys()),
                "datasets": [
                    {
                        "name": "Count",
                        "values": list(priority_counts.values())
                    }
                ]
            }
        },
        {
            "name": "Days Overdue Distribution",
            "chart_name": _("Distribution by Days Overdue"),
            "chart_type": "bar",
            "data": {
                "labels": list(days_ranges.keys()),
                "datasets": [
                    {
                        "name": "Audit Count",
                        "values": list(days_ranges.values())
                    }
                ]
            }
        },
        {
            "name": "Overdue by Week",
            "chart_name": _("Overdue Audits by Week"),
            "chart_type": "line",
            "data": {
                "labels": list(week_counts.keys()),
                "datasets": [
                    {
                        "name": "Overdue Count",
                        "values": list(week_counts.values())
                    }
                ]
            }
        }
    ]
    
    return charts