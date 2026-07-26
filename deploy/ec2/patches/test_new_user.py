import random

import frappe


def run():
    frappe.set_user("Administrator")
    email = f"demo.user.{random.randint(1000, 9999)}@example.com"
    u = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": "Demo",
            "last_name": "User",
            "enabled": 1,
            "user_type": "System User",
            "send_welcome_email": 0,
        }
    )
    u.insert(ignore_permissions=True)
    frappe.db.commit()
    u.reload()
    roles = frappe.get_roles(email)
    profiles = [r.role_profile for r in (u.role_profiles or [])]
    result = {
        "profiles": profiles,
        "user_type": u.user_type,
        "role_count": len(roles),
        "has_sales_user": "Sales User" in roles,
        "ok": (
            "Prime Ledger User" in profiles
            and "Sales User" in roles
            and u.user_type == "System User"
        ),
    }
    frappe.delete_doc("User", email, force=1, ignore_permissions=True)
    frappe.db.commit()
    return result
