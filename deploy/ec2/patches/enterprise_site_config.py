"""Apply production site hardening. Invoked via: bench --site <site> execute enterprise_site_config.apply"""

import frappe


def apply():
    frappe.db.set_single_value("System Settings", "app_name", "Prime Ledger")
    frappe.db.set_single_value("Website Settings", "app_name", "Prime Ledger")

    frappe.db.set_single_value("System Settings", "enable_password_policy", 1)
    frappe.db.set_single_value("System Settings", "minimum_password_score", 3)
    frappe.db.set_single_value("System Settings", "allow_login_using_user_name", 1)
    frappe.db.set_single_value("System Settings", "login_with_email_link", 0)
    frappe.db.set_single_value("System Settings", "disable_user_pass_login", 0)
    frappe.db.set_single_value("System Settings", "session_expiry", "06:00")
    frappe.db.set_single_value("System Settings", "session_expiry_mobile", "06:00")
    frappe.db.set_single_value("System Settings", "backup_limit", 14)

    # Stock Frappe signup dumps users into the shared site — disabled.
    # New organizations use /start → Pending PL Tenant (private site later).
    frappe.db.set_single_value("Website Settings", "disable_signup", 1)
    frappe.db.set_single_value("Website Settings", "hide_footer_signup", 1)
    frappe.db.set_single_value("Website Settings", "show_footer_on_login", 0)

    try:
        frappe.utils.scheduler.enable_scheduler()
    except Exception as e:
        print("scheduler_enable:", e)

    frappe.db.commit()
    frappe.clear_cache()
    return {
        "ok": True,
        "disable_signup": frappe.db.get_single_value("Website Settings", "disable_signup"),
        "password_policy": frappe.db.get_single_value("System Settings", "enable_password_policy"),
        "backup_limit": frappe.db.get_single_value("System Settings", "backup_limit"),
    }
