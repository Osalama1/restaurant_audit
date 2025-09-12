# Copyright (c) 2025, Ontime Solutions and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Restaurant(Document):
	def validate(self):
		"""Validate restaurant data"""
		pass
	
	def on_update(self):
		"""Called when restaurant is updated"""
		# Check if any employees were removed
		self.check_for_removed_employees()
	
	def check_for_removed_employees(self):
		"""Check if any employees were removed and clean up their data"""
		try:
			# Get current assigned employees
			current_employees = set()
			for emp in self.assigned_employees:
				if emp.is_active:
					current_employees.add(emp.employee)
			
			# Get previous assigned employees from database
			previous_employees = set()
			if not self.is_new():
				previous_data = frappe.get_doc("Restaurant", self.name, for_update=False)
				for emp in previous_data.assigned_employees:
					if emp.is_active:
						previous_employees.add(emp.employee)
			
			# Find removed employees
			removed_employees = previous_employees - current_employees
			
			# Clean up data for removed employees
			for employee_id in removed_employees:
				try:
					from restaurant_audit.tasks import cleanup_employee_on_removal
					cleanup_employee_on_removal(self.name, employee_id)
					frappe.msgprint(f"Cleaned up data for removed employee: {employee_id}")
				except Exception as e:
					frappe.log_error(f"Error cleaning up employee {employee_id}: {str(e)}", "Restaurant Employee Cleanup")
					
		except Exception as e:
			frappe.log_error(f"Error in check_for_removed_employees: {str(e)}", "Restaurant Employee Cleanup")
