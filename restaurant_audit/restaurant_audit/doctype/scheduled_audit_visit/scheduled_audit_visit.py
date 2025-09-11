# Copyright (c) 2025, Restaurant Audit App and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta

class ScheduledAuditVisit(Document):
    def before_save(self):
        """Calculate week start and end dates based on visit_date"""
        if self.visit_date:
            visit_date = frappe.utils.getdate(self.visit_date)
            
            # Calculate week start (Monday) and end (Sunday)
            days_since_monday = visit_date.weekday()
            week_start = visit_date - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)
            
            self.week_start_date = week_start
            self.week_end_date = week_end
    
    def autoname(self):
        """Generate unique name based on restaurant and visit date"""
        if self.restaurant and self.visit_date:
            restaurant_name = frappe.db.get_value("Restaurant", self.restaurant, "restaurant_name")
            visit_date_str = frappe.utils.formatdate(self.visit_date, "yyyy-mm-dd")
            self.name = f"SAV-{restaurant_name}-{visit_date_str}"
        else:
            self.name = frappe.generate_hash(length=10)