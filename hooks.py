# Copyright (c) 2025, Restaurant Audit App and contributors
# For license information, please see license.txt

from . import __version__ as app_version

app_name = "restaurant_audit"
app_title = "Restaurant Audit"
app_publisher = "Restaurant Audit App"
app_description = "Restaurant Audit Management System"
app_email = "admin@restaurantaudit.com"
app_license = "MIT"

# Scheduled Jobs
scheduler_events = {
    "weekly": [
        "restaurant_audit.tasks.check_weekly_audits"
    ]
}

# Website Route Rules
website_route_rules = [
    {"from_route": "/audit-login", "to_route": "audit-login"},
    {"from_route": "/audit-restaurants", "to_route": "audit-restaurants"},
    {"from_route": "/audit-form", "to_route": "audit-form"}
]

# Include js, css files in header of desk.html
# app_include_css = "/assets/restaurant_audit/css/restaurant_audit.css"
# app_include_js = "/assets/restaurant_audit/js/restaurant_audit.js"

# Include js, css files in header of web template
# web_include_css = "/assets/restaurant_audit/css/restaurant_audit.css"
# web_include_js = "/assets/restaurant_audit/js/restaurant_audit.js"

# Home Pages
# home_page = "login"

# Application logo
# app_logo_url = "/assets/restaurant_audit/images/logo.png"

# Application Name (overrides `app_name`)
# app_title = "Restaurant Audit"

# Application Description
# app_description = "Restaurant Audit Management System"

# Application colour
# app_color = "#000"

# Application Email
# app_email = "admin@restaurantaudit.com"

# Modules
# modules_path = "restaurant_audit.modules"

# Generators
# generators = []

# Each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#     "Task": "restaurant_audit.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# doc_events = {
#     "*": {
#         "on_update": "method",
#         "on_cancel": "method",
#         "on_trash": "method"
#     }
# }

# User Data Protection
# user_data_fields = [
#     {
#         "doctype": "{doctype_1}",
#         "filter_by": "{filter_by}",
#         "redact_fields": ["{field_1}", "{field_2}"],
#         "partial": 1,
#     },
#     {
#         "doctype": "{doctype_2}",
#         "filter_by": "{filter_by}",
#         "partial": 1,
#     },
#     {
#         "doctype": "{doctype_3}",
#         "strict": False,
#     },
#     {
#         "doctype": "{doctype_4}"
#     }
# ]

# Authentication and authorization
# auth_hooks = [
#     "restaurant_audit.auth.validate_auth"
# ]