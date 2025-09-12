// Copyright (c) 2025, Restaurant Audit App and contributors
// For license information, please see license.txt

frappe.ui.form.on('Daily Audit Template', {
    refresh: function(frm) {
        // Add custom buttons and functionality
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__('Check Status'), function() {
                frappe.call({
                    method: 'restaurant_audit.restaurant_audit.doctype.daily_audit_template.daily_audit_template.get_template_status',
                    args: {
                        template_name: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            frappe.msgprint({
                                title: __('Template Status'),
                                message: `
                                    <p><strong>Status:</strong> ${r.message.status}</p>
                                    <p><strong>Currently Open:</strong> ${r.message.is_open ? 'Yes' : 'No'}</p>
                                    <p><strong>Open Time:</strong> ${r.message.open_time}</p>
                                    <p><strong>Close Time:</strong> ${r.message.close_time}</p>
                                    <p><strong>Cashier Opening:</strong> ${r.message.cashier_opening_time}</p>
                                `,
                                indicator: r.message.is_open ? 'green' : 'red'
                            });
                        }
                    }
                });
            });
        }
        
        // Set default values for new templates
        if (frm.doc.__islocal) {
            frm.set_value('created_by', frappe.session.user);
            frm.set_value('open_time', '06:00:00');
            frm.set_value('close_time', '08:30:00');
            frm.set_value('cashier_opening_time', '09:00:00');
        }
    },
    
    applies_to_all_restaurants: function(frm) {
        // Clear restaurant field if applies to all restaurants
        if (frm.doc.applies_to_all_restaurants) {
            frm.set_value('restaurant', '');
        }
    },
    
    restaurant: function(frm) {
        // Uncheck applies to all if specific restaurant is selected
        if (frm.doc.restaurant) {
            frm.set_value('applies_to_all_restaurants', 0);
        }
    },
    
    close_time: function(frm) {
        // Validate that close time is before cashier opening time
        if (frm.doc.close_time && frm.doc.cashier_opening_time) {
            if (frm.doc.close_time > frm.doc.cashier_opening_time) {
                frappe.msgprint(__('Template close time should be before cashier opening time'));
            }
        }
    },
    
    open_time: function(frm) {
        // Validate that open time is before close time
        if (frm.doc.open_time && frm.doc.close_time) {
            if (frm.doc.open_time >= frm.doc.close_time) {
                frappe.msgprint(__('Template open time should be before close time'));
            }
        }
    }
});