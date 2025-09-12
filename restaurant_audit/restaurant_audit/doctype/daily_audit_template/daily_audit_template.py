# Copyright (c) 2025, Restaurant Audit App and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, time

class DailyAuditTemplate(Document):
    def before_save(self):
        """Validate template settings before saving"""
        self.validate_time_settings()
        self.set_created_by()
        self.set_last_modified_by()
    
    def validate_time_settings(self):
        """Validate that time settings are logical"""
        if self.open_time and self.close_time:
            open_time = datetime.strptime(str(self.open_time), "%H:%M:%S").time()
            close_time = datetime.strptime(str(self.close_time), "%H:%M:%S").time()
            
            if open_time >= close_time:
                frappe.throw("Template close time must be after open time")
        
        if self.close_time and self.cashier_opening_time:
            close_time = datetime.strptime(str(self.close_time), "%H:%M:%S").time()
            cashier_time = datetime.strptime(str(self.cashier_opening_time), "%H:%M:%S").time()
            
            if close_time > cashier_time:
                frappe.throw("Template must close before cashier opening time")
    
    def set_created_by(self):
        """Set created_by field if not already set"""
        if not self.created_by:
            self.created_by = frappe.session.user
    
    def set_last_modified_by(self):
        """Set last_modified_by field"""
        self.last_modified_by = frappe.session.user
    
    def is_currently_open(self):
        """Check if template is currently open based on time settings"""
        if not self.is_active:
            return False
        
        now = datetime.now().time()
        open_time = datetime.strptime(str(self.open_time), "%H:%M:%S").time()
        close_time = datetime.strptime(str(self.close_time), "%H:%M:%S").time()
        
        return open_time <= now <= close_time
    
    def get_status(self):
        """Get current status of the template"""
        if not self.is_active:
            return "Inactive"
        
        if self.is_currently_open():
            return "Open"
        else:
            return "Closed"
    
    def update_last_used(self):
        """Update last used date when template is used"""
        self.last_used_date = frappe.utils.now()
        self.save(ignore_permissions=True)

@frappe.whitelist()
def get_active_templates(restaurant=None):
    """Get active daily audit templates"""
    filters = {"is_active": 1}
    
    if restaurant:
        # Get templates for specific restaurant or global templates
        filters = {
            "is_active": 1,
            "$or": [
                {"restaurant": restaurant},
                {"applies_to_all_restaurants": 1}
            ]
        }
    
    templates = frappe.get_all("Daily Audit Template",
        filters=filters,
        fields=[
            "name", "template_name", "description", "restaurant", "restaurant_name",
            "open_time", "close_time", "cashier_opening_time", "questions_count",
            "estimated_duration", "priority", "applies_to_all_restaurants"
        ]
    )
    
    # Add current status for each template
    for template in templates:
        template_doc = frappe.get_doc("Daily Audit Template", template.name)
        template["current_status"] = template_doc.get_status()
        template["is_currently_open"] = template_doc.is_currently_open()
    
    return templates

@frappe.whitelist()
def get_template_status(template_name):
    """Get current status of a specific template"""
    template = frappe.get_doc("Daily Audit Template", template_name)
    return {
        "status": template.get_status(),
        "is_open": template.is_currently_open(),
        "open_time": template.open_time,
        "close_time": template.close_time,
        "cashier_opening_time": template.cashier_opening_time
    }