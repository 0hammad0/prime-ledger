"""Apply Prime Ledger white-label site settings. Run inside bench console via exec()."""
from __future__ import annotations

import os
import re

import frappe
from frappe.utils.password import update_password

logo = "/assets/erpnext/images/prime-ledger-logo.svg"
favicon = "/assets/erpnext/images/prime-ledger-favicon.svg"
# Also keep legacy filename path used by login templates
legacy_logo = "/assets/erpnext/images/erpnext-logo.svg"
css_link = '<link rel="stylesheet" href="/assets/erpnext/css/prime_ledger_brand.css">'
js_link = '<script src="/assets/erpnext/js/login_simple.js?v=20260818" defer></script>'
CLEAN_HEAD = css_link + "\n" + js_link

ERP_URL_RE = re.compile(
	r"https?://(?:docs\.)?(?:frappe\.io/erpnext|erpnext\.com)[^\s\"'<>]*",
	re.I,
)
EMPTY_DOC_ANCHOR_RE = re.compile(
	r'\s*<a\s+[^>]*href=["\'][^"\']*(?:erpnext|frappe\.io/erpnext)[^"\']*["\'][^>]*>.*?</a>',
	re.I | re.S,
)


def _scrub_text(value: str | None) -> str | None:
	if not value:
		return value
	out = EMPTY_DOC_ANCHOR_RE.sub("", value)
	out = ERP_URL_RE.sub("", out)
	out = out.replace("ERPNext", "Prime Ledger").replace("erpnext.com", "")
	return out


frappe.db.set_single_value("System Settings", "app_name", "Prime Ledger")
frappe.db.set_single_value("Website Settings", "app_name", "Prime Ledger")
try:
	# Stock signup disabled — organization signup is /start
	frappe.db.set_single_value("Website Settings", "disable_signup", 1)
	frappe.db.set_single_value("Website Settings", "hide_footer_signup", 1)
except Exception as e:
	print(f"skip signup flags: {e}")

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
	head = CLEAN_HEAD
	frappe.db.set_single_value("Website Settings", "head_html", head)
	print("head_html_clean")
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
		"docs.frappe.io",
		"discuss.frappe.io",
		"frappe.io",
		"github.com/frappe/erpnext",
		"github.com/frappe",
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
		elif label.strip().lower() == "erpnext":
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

# Strip ERPNext documentation URLs / help anchors from DocFields (Desk "?" links)
try:
	cleared = frappe.db.sql(
		"""
		UPDATE `tabDocField`
		SET documentation_url = NULL
		WHERE documentation_url LIKE %s OR documentation_url LIKE %s
		""",
		("%erpnext%", "%frappe.io/erpnext%"),
	)
	print(f"docfield_docs_cleared:{cleared}")
except Exception as e:
	print(f"skip docfield docs: {e}")

try:
	rows = frappe.db.sql(
		"""
		SELECT name, description FROM `tabDocField`
		WHERE description LIKE %s OR description LIKE %s OR description LIKE %s
		""",
		("%erpnext%", "%ERPNext%", "%frappe.io/erpnext%"),
		as_dict=True,
	)
	for row in rows:
		scrubbed = _scrub_text(row.description)
		if scrubbed != row.description:
			frappe.db.set_value("DocField", row.name, "description", scrubbed, update_modified=False)
	print(f"docfield_desc_scrubbed:{len(rows)}")
except Exception as e:
	print(f"skip docfield desc: {e}")

# Custom Field / Property Setter copies of the same help text
for doctype in ("Custom Field", "Property Setter"):
	try:
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		text_fields = [df.fieldname for df in meta.fields if df.fieldtype in ("Small Text", "Text", "Long Text", "Data", "Code", "HTML Editor")]
		filters = []
		for tf in text_fields:
			filters.append([doctype, tf, "like", "%erpnext%"])
			filters.append([doctype, tf, "like", "%ERPNext%"])
		if not filters:
			continue
		names = set()
		for f in filters:
			for n in frappe.get_all(doctype, filters=[f], pluck="name"):
				names.add(n)
		for name in names:
			doc = frappe.get_doc(doctype, name)
			changed = False
			for tf in text_fields:
				val = doc.get(tf)
				if isinstance(val, str) and ("erpnext" in val.lower() or "ERPNext" in val):
					doc.set(tf, _scrub_text(val))
					changed = True
			if changed:
				doc.db_update()
		print(f"{doctype}_scrubbed:{len(names)}")
	except Exception as e:
		print(f"skip {doctype}: {e}")

# Onboarding steps that deep-link to ERPNext docs
try:
	for row in frappe.get_all("Onboarding Step", fields=["name", "path", "title"]):
		path = row.path or ""
		title = row.title or ""
		updates = {}
		if "erpnext" in path.lower():
			updates["path"] = ""
		if "ERPNext" in title:
			updates["title"] = title.replace("ERPNext", "Prime Ledger")
		if updates:
			frappe.db.set_value("Onboarding Step", row.name, updates, update_modified=False)
			print(f"onboarding:{row.name}->{updates}")
except Exception as e:
	print(f"skip onboarding: {e}")

# Notifications / system messages mentioning ERPNext
try:
	for row in frappe.get_all("Notification", fields=["name", "subject", "message"]):
		updates = {}
		for field in ("subject", "message"):
			val = row.get(field) or ""
			if "ERPNext" in val or "erpnext.com" in val.lower():
				updates[field] = _scrub_text(val)
		if updates:
			frappe.db.set_value("Notification", row.name, updates, update_modified=False)
except Exception as e:
	print(f"skip notifications: {e}")

# Email templates
try:
	for row in frappe.get_all("Email Template", fields=["name", "subject", "response"]):
		updates = {}
		for field in ("subject", "response"):
			val = row.get(field) or ""
			if "ERPNext" in val or "erpnext" in val.lower():
				updates[field] = _scrub_text(val)
		if updates:
			frappe.db.set_value("Email Template", row.name, updates, update_modified=False)
except Exception as e:
	print(f"skip email templates: {e}")

# Disable standard "Powered by" / product email footers
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
