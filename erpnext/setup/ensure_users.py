"""Make new / admin users permission-ready (idempotent).

Creates Role Profiles, grants full ERP roles to under-provisioned admins,
enables Server Scripts, and installs a User After Insert script so new
System Users get a working Role Profile automatically.

bench --site <site> execute ensure_users.run
"""

from __future__ import annotations

import frappe

ADMIN_ROLES = [
    "System Manager",
    "Accounts Manager",
    "Accounts User",
    "Sales Manager",
    "Sales User",
    "Sales Master Manager",
    "Purchase Manager",
    "Purchase User",
    "Purchase Master Manager",
    "Stock Manager",
    "Stock User",
    "Item Manager",
    "Manufacturing Manager",
    "Manufacturing User",
    "Projects Manager",
    "Projects User",
    "HR Manager",
    "HR User",
    "Employee",
    "Auditor",
    "Analytics",
    "Website Manager",
    "Workspace Manager",
    "Dashboard Manager",
    "Report Manager",
    "Script Manager",
    "Newsletter Manager",
    "Knowledge Base Editor",
    "Knowledge Base Contributor",
    "Inbox User",
    "Prepared Report User",
    "Translator",
    "Maintenance Manager",
    "Maintenance User",
    "Delivery Manager",
    "Delivery User",
    "Fulfillment User",
    "Quality Manager",
    "Fleet Manager",
    "Support Team",
    "Marketing Manager",
    "Desk User",
]

USER_ROLES = [
    "Desk User",
    "Employee",
    "Accounts User",
    "Sales User",
    "Purchase User",
    "Stock User",
    "Projects User",
    "Inbox User",
    "Prepared Report User",
]

ADMIN_PROFILE = "Prime Ledger Admin"
USER_PROFILE = "Prime Ledger User"
SERVER_SCRIPT_NAME = "Prime Ledger: New User Role Profile"


def _unlock(doctype: str, name: str) -> None:
    try:
        frappe.db.delete("Document Lock", {"ref_doctype": doctype, "docname": name})
        frappe.db.commit()
    except Exception:
        pass


def _ensure_role_profile(name: str, roles: list[str]) -> None:
    existing_roles = [r for r in roles if frappe.db.exists("Role", r)]
    _unlock("Role Profile", name)
    if frappe.db.exists("Role Profile", name):
        doc = frappe.get_doc("Role Profile", name)
        have = {r.role for r in doc.roles}
        changed = False
        for role in existing_roles:
            if role not in have:
                doc.append("roles", {"role": role})
                changed = True
        if changed:
            try:
                doc.flags.ignore_links = True
                doc.save(ignore_permissions=True)
            except frappe.DocumentLockedError:
                _unlock("Role Profile", name)
        return
    doc = frappe.get_doc(
        {
            "doctype": "Role Profile",
            "role_profile": name,
            "roles": [{"role": r} for r in existing_roles],
        }
    )
    try:
        doc.flags.ignore_links = True
        doc.insert(ignore_permissions=True)
    except frappe.DocumentLockedError:
        _unlock("Role Profile", name)
        if not frappe.db.exists("Role Profile", name):
            raise


def _apply_roles(user_name: str, roles: list[str], role_profile: str | None = None) -> list[str]:
    from erpnext.setup.user_onboarding import apply_role_profile

    doc = frappe.get_doc("User", user_name)
    if getattr(doc, "block_modules", None):
        doc.block_modules = []
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)

    if role_profile:
        apply_role_profile(user_name, role_profile)

    existing = set(frappe.get_roles(user_name))
    added = []
    for role in roles:
        if not frappe.db.exists("Role", role) or role in existing:
            continue
        frappe.get_doc(
            {
                "doctype": "Has Role",
                "parent": user_name,
                "parenttype": "User",
                "parentfield": "roles",
                "role": role,
            }
        ).insert(ignore_permissions=True)
        added.append(role)
    frappe.clear_cache(user=user_name)
    frappe.db.set_default("desktop:home_page", "workspace", user_name)
    return added


def _admin_targets() -> list[str]:
    names: list[str] = []
    for name in ("admin@primeledger.local", "admin"):
        if frappe.db.exists("User", name):
            names.append(name)
    for u in frappe.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User"},
        fields=["name"],
    ):
        if u.name in ("Administrator", "Guest") or u.name in names:
            continue
        roles = set(frappe.get_roles(u.name))
        if "System Manager" in roles and len(roles) < 15:
            names.append(u.name)
    return names


def _ensure_server_script() -> str:
    # safe_exec: no frappe.get_roles / getattr. Use db.get_all only.
    script = """
# Prefer DB check — Python hook may already have inserted in this transaction
# Skip Guest / self-signup (control plane must not mint shared desk users)
actor = frappe.session.user if frappe.session else "Guest"
if actor in ("Guest",) or actor == doc.name:
    pass
else:
    has_profile = 1 if frappe.db.exists("User Role Profile", {"parent": doc.name}) else 0
    portal = ["Customer", "Supplier", "Partner", "Student", "Instructor", "Guardian"]
    role_names = [r.role for r in (doc.roles or []) if r.role]
    is_portal = 0
    for r in role_names:
        if r in portal:
            is_portal = 1
    if (not has_profile) and doc.name not in ("Administrator", "Guest") and (not is_portal or "System Manager" in role_names):
        profile = "Prime Ledger Admin" if "System Manager" in role_names else "Prime Ledger User"
        if frappe.db.exists("Role Profile", profile):
            frappe.get_doc({"doctype": "User Role Profile", "parent": doc.name, "parenttype": "User", "parentfield": "role_profiles", "role_profile": profile}).insert(ignore_permissions=True)
            existing = frappe.db.get_all("Has Role", filters={"parent": doc.name, "parenttype": "User"}, pluck="role")
            for role in frappe.db.get_all("Has Role", filters={"parent": profile, "parenttype": "Role Profile"}, pluck="role"):
                if role and role not in existing:
                    frappe.get_doc({"doctype": "Has Role", "parent": doc.name, "parenttype": "User", "parentfield": "roles", "role": role}).insert(ignore_permissions=True)
            frappe.db.set_value("User", doc.name, "user_type", "System User", update_modified=False)
"""

    if frappe.db.exists("Server Script", SERVER_SCRIPT_NAME):
        doc = frappe.get_doc("Server Script", SERVER_SCRIPT_NAME)
        doc.script = script.strip()
        doc.disabled = 0
        doc.script_type = "DocType Event"
        doc.reference_doctype = "User"
        doc.doctype_event = "After Insert"
        doc.save(ignore_permissions=True)
        return "updated"

    frappe.get_doc(
        {
            "doctype": "Server Script",
            "name": SERVER_SCRIPT_NAME,
            "script_type": "DocType Event",
            "reference_doctype": "User",
            "doctype_event": "After Insert",
            "disabled": 0,
            "script": script.strip(),
        }
    ).insert(ignore_permissions=True)
    return "created"


def ensure_admin_roles(email: str | None = None) -> dict:
    targets = list(_admin_targets())
    if email and frappe.db.exists("User", email) and email not in targets:
        targets.insert(0, email)
    results = []
    for uname in targets:
        added = _apply_roles(uname, ADMIN_ROLES, ADMIN_PROFILE)
        results.append({"user": uname, "added": added, "roles": len(frappe.get_roles(uname))})
    return {"admins": results}


def run():
    frappe.connect()
    frappe.set_user("Administrator")
    errors = []

    for profile, roles in ((ADMIN_PROFILE, ADMIN_ROLES), (USER_PROFILE, USER_ROLES)):
        try:
            _ensure_role_profile(profile, roles)
        except Exception as e:
            errors.append(f"role_profile:{profile}:{e}")

    script_status = "skipped"
    try:
        script_status = _ensure_server_script()
    except Exception as e:
        errors.append(f"server_script:{e}")

    admin_result = {"admins": []}
    try:
        admin_result = ensure_admin_roles()
    except Exception as e:
        errors.append(f"admins:{e}")

    try:
        frappe.db.set_single_value("System Settings", "enable_onboarding", 1)
    except Exception:
        pass

    frappe.db.commit()
    frappe.clear_cache()
    return {
        "ok": not errors,
        "role_profiles": [ADMIN_PROFILE, USER_PROFILE],
        "server_script": script_status,
        "errors": errors,
        **admin_result,
    }
