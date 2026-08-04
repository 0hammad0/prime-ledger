"""Apply Prime Ledger white-label site settings. Run inside bench console via exec()."""
from __future__ import annotations

import os

import frappe
from frappe.utils.password import update_password

logo = "/assets/erpnext/images/prime-ledger-logo.svg"
favicon = "/assets/erpnext/images/prime-ledger-favicon.svg"
# Also keep legacy filename path used by login templates
legacy_logo = "/assets/erpnext/images/erpnext-logo.svg"
css_link = '<link rel="stylesheet" href="/assets/erpnext/css/prime_ledger_brand.css">'

frappe.db.set_single_value("System Settings", "app_name", "Prime Ledger")
frappe.db.set_single_value("Website Settings", "app_name", "Prime Ledger")

for field, value in (
	("splash_image", logo),
	("banner_image", logo),
	("favicon", favicon),
	("footer_powered", "Prime Ledger"),
	("copyright", "Prime Ledger"),
	("title_prefix", "Prime Ledger"),
):
	try:
		frappe.db.set_single_value("Website Settings", field, value)
	except Exception as e:
		print(f"skip Website Settings.{field}: {e}")

try:
	head = frappe.db.get_single_value("Website Settings", "head_html") or ""
	# Drop generator / third-party product mentions from custom head if present
	for junk in ("ERPNext", "erpnext.com", "Built on Frappe"):
		head = head.replace(junk, "Prime Ledger" if junk != "erpnext.com" else "")
	if "prime_ledger_brand.css" not in head:
		head = (css_link + "\n" + head).strip()
	frappe.db.set_single_value("Website Settings", "head_html", head)
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
		blocked = False
		for host in blocked_hosts:
			if host in item_route:
				blocked = True
				break
		if blocked:
			continue
		# Relabel any ERPNext wording in remaining items
		item_label = item.item_label or ""
		if "ERPNext" in item_label:
			item_label = item_label.replace("ERPNext", "Prime Ledger")
		kept.append(
			{
				"item_label": item_label,
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

# Desktop icons — rename any ERPNext* labels
try:
	for row in frappe.get_all("Desktop Icon", fields=["name", "label", "logo_url"]):
		label = row.label or ""
		new_label = label
		if "ERPNext" in label:
			new_label = label.replace("ERPNext", "Prime Ledger")
		elif label.strip() == "ERPNext":
			new_label = "Prime Ledger"
		updates = {}
		if new_label != label:
			updates["label"] = new_label
		if not row.logo_url or "erpnext-logo" in (row.logo_url or "") or "frappe" in (row.logo_url or ""):
			updates["logo_url"] = logo
		if updates:
			frappe.db.set_value("Desktop Icon", row.name, updates, update_modified=False)
			print(f"desktop_icon:{row.name}->{updates}")
except Exception as e:
	print(f"skip desktop icons: {e}")

# Workspaces
try:
	for name, label in frappe.get_all("Workspace", fields=["name", "label"], as_list=True):
		if label and "ERPNext" in label:
			frappe.db.set_value(
				"Workspace",
				name,
				"label",
				label.replace("ERPNext", "Prime Ledger"),
				update_modified=False,
			)
			print(f"workspace:{name}")
except Exception as e:
	print(f"skip workspace labels: {e}")

# Module Def display — Hub may block rename; scrub label field if present
try:
	if frappe.db.exists("Module Def", "ERPNext Integrations"):
		meta = frappe.get_meta("Module Def")
		if meta.has_field("module_name"):
			frappe.db.set_value("Module Def", "ERPNext Integrations", "module_name", "Integrations")
		try:
			frappe.rename_doc(
				"Module Def", "ERPNext Integrations", "Integrations", force=True, show_alert=False
			)
			print("module_renamed")
		except Exception as e:
			print(f"module_rename_skip: {e}")
except Exception as e:
	print(f"skip module: {e}")

# Navbar app switcher / splash
try:
	frappe.db.set_single_value("System Settings", "disable_standard_email_footer", 1)
except Exception:
	pass

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
	try:
		from erpnext.setup.ensure_users import ensure_admin_roles

		ensure_admin_roles(email)
	except Exception as e:
		print(f"admin_roles_skip: {e}")

frappe.db.commit()
frappe.clear_cache()
print("branding_ok")
