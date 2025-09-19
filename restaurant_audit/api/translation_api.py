import frappe
from frappe import _
import csv
import os

@frappe.whitelist(allow_guest=True)
def get_translations(lang='en'):
    """Get translations for the specified language"""
    try:
        translations = {}
        
        # Get translation file path
        app_path = frappe.get_app_path('restaurant_audit')
        translation_file = os.path.join(app_path, 'translations', f'{lang}.csv')
        
        if os.path.exists(translation_file):
            with open(translation_file, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                for row in reader:
                    if len(row) >= 2 and not row[0].startswith('#'):
                        translations[row[0]] = row[1]
        
        return {
            "success": True,
            "message": translations
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting translations: {str(e)}", "Translation API")
        return {
            "success": False,
            "message": str(e)
        }

@frappe.whitelist()
def get_user_language():
    """Get current user's preferred language"""
    user = frappe.session.user
    if user and user != 'Guest':
        user_doc = frappe.get_doc("User", user)
        return user_doc.language or 'en'
    return 'en'

@frappe.whitelist()
def set_user_language(language):
    """Set user's preferred language"""
    user = frappe.session.user
    if user and user != 'Guest':
        frappe.db.set_value("User", user, "language", language)
        frappe.db.commit()
        return {"success": True}
    return {"success": False, "message": "User not logged in"}