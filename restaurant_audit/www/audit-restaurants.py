import frappe

def get_context(context):
    # This script runs before the page is loaded.
    # If the user is a "Guest" (not logged in), redirect them to your custom login page.
    if frappe.session.user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/audit-login"
        raise frappe.Redirect