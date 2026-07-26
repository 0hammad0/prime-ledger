"""Apply Prime Ledger white-label site settings. Run inside bench console via exec()."""
from __future__ import annotations

import os

import frappe
from frappe.utils.password import update_password

logo = "/assets/erpnext/images/prime-ledger-logo.svg"
favicon = "/assets/erpnext/images/prime-ledger-favicon.svg"
css_link = '<link rel="stylesheet" href="/assets/erpnext/css/prime_ledger_brand.css">'

frappe.db.set_single_value("System Settings", "app_name", "Prime Ledger")
frappe.db.set_single_value("Website Settings", "app_name", "Prime Ledger")

for field, value in (
	("splash_image", logo),
	("banner_image", logo),
	("favicon", favicon),
	("footer_powered", "Prime Ledger"),
	("copyright", "Prime Ledger"),
):
	try:
		frappe.db.set_single_value("Website Settings", field, value)
	except Exception as e:
		print(f"skip Website Settings.{field}: {e}")

try:
	head = frappe.db.get_single_value("Website Settings", "head_html") or ""
	if "prime_ledger_brand.css" not in head:
		frappe.db.set_single_value("Website Settings", "head_html", (css_link + "\n" + head).strip())
except Exception as e:
	print(f"skip head_html: {e}")

try:
	nav = frappe.get_single("Navbar Settings")
	blocked_labels = {
		"Documentation",
		"User Forum",
		"Frappe School",
		"Report an Issue",
		"About",
	}
	blocked_hosts = (
		"docs.erpnext.com",
		"erpnext.com",
		"discuss.frappe.io",
		"frappe.io",
		"github.com/frappe/erpnext",
	)
	kept = []
	for item in list(nav.help_dropdown or []):
		label = (getattr(item, "item_label", None) or "").strip()
		item_route = (getattr(item, "route", None) or "").strip()
		if label in blocked_labels:
			continue
		# Avoid genexp inside exec() — can raise NameError for locals
		blocked = False
		for host in blocked_hosts:
			if host in item_route:
				blocked = True
				break
		if blocked:
			continue
		kept.append(
			{
				"item_label": item.item_label,
				"item_type": item.item_type,
				"route": item.route,
				"action": item.action,
				"is_standard": item.is_standard,
				"hidden": item.hidden,
			}
		)
	nav.set("help_dropdown", [])
	for row in kept:
		nav.append("help_dropdown", row)
	nav.save(ignore_permissions=True)
except Exception as e:
	print(f"skip navbar: {e}")

if frappe.db.exists("Desktop Icon", "Prime Ledger"):
	frappe.db.set_value("Desktop Icon", "Prime Ledger", "logo_url", logo)
if frappe.db.exists("Desktop Icon", "ERPNext"):
	frappe.db.set_value("Desktop Icon", "ERPNext", "label", "Prime Ledger")
	frappe.db.set_value("Desktop Icon", "ERPNext", "logo_url", logo)

admin_pw = os.environ.get("ADMIN_PASSWORD", "")
if admin_pw:
	update_password("Administrator", admin_pw)
	email = "admin@primeledger.local"
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
	else:
		user = frappe.new_doc("User")
		user.email = email
		user.first_name = "Admin"
		user.enabled = 1
		user.user_type = "System User"
		user.send_welcome_email = 0
		user.append("roles", {"role": "System Manager"})
		user.insert(ignore_permissions=True)
	user.username = "admin"
	user.enabled = 1
	user.user_type = "System User"
	if frappe.db.exists("Role Profile", "Prime Ledger Admin"):
		user.role_profile_name = "Prime Ledger Admin"
	user.save(ignore_permissions=True)
	update_password(user.name, admin_pw)
	# Full ERP roles — System Manager alone causes permission errors on every click
	try:
		from erpnext.setup.ensure_users import ensure_admin_roles

		ensure_admin_roles(email)
	except Exception as e:
		print(f"admin_roles_skip: {e}")

frappe.db.commit()
frappe.clear_cache()
print("branding_ok")
