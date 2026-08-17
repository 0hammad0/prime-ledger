from pathlib import Path

hooks = Path("/home/frappe/frappe-bench/apps/erpnext/erpnext/hooks.py")
text = hooks.read_text()

# Portal website routes
needle = '{"from_route": "/portal", "to_route": "portal"}'
if needle not in text:
	old = '{"from_route": "/banking/<path:app_path>", "to_route": "banking"},'
	if old in text:
		text = text.replace(
			old,
			old
			+ '\n\t{"from_route": "/portal", "to_route": "portal"},'
			+ '\n\t{"from_route": "/portal/<path:app_path>", "to_route": "portal"},',
			1,
		)

# App home → portal dashboard
import re

text2, n = re.subn(
	r'app_home\s*=\s*["\']/desk/home["\']',
	'app_home = "/portal"',
	text,
	count=1,
)
if n:
	text = text2
	print("app_home_portal_ok")
elif 'app_home = "/portal"' not in text and "app_home=" in text.replace(" ", ""):
	text2, n = re.subn(r'app_home\s*=\s*["\'][^"\']+["\']', 'app_home = "/portal"', text, count=1)
	if n:
		text = text2
		print("app_home_forced_portal")

# on_login hook
if "erpnext.portal_control.redirects.on_login" not in text:
	if "on_session_creation" in text and "on_login" not in text:
		text = text.replace(
			"on_session_creation",
			'on_login = "erpnext.portal_control.redirects.on_login"\non_session_creation',
			1,
		)
		print("on_login_hook_ok")
	elif 'on_login = "' not in text:
		text += '\n\non_login = "erpnext.portal_control.redirects.on_login"\n'
		print("on_login_hook_appended")

# Customize guardrails — only admins may change Custom Field / Property Setter
if "erpnext.portal_control.tenancy.assert_can_customize" not in text and "doc_events" in text:
	text += (
		"\n\n# Prime Ledger: block non-admin form customization\n"
		'for _pl_dt in ("Custom Field", "Property Setter"):\n'
		'\tdoc_events.setdefault(_pl_dt, {}).setdefault("validate", [])\n'
		'\tif "erpnext.portal_control.tenancy.assert_can_customize" not in doc_events[_pl_dt]["validate"]:\n'
		'\t\tdoc_events[_pl_dt]["validate"].append(\n'
		'\t\t\t"erpnext.portal_control.tenancy.assert_can_customize"\n'
		"\t\t)\n"
	)
	print("customize_guard_hooks_ok")

# Force Prime Ledger product branding (strip ERPNext-named logos / titles)
brand_subs = [
	(r'app_title\s*=\s*["\'][^"\']*["\']', 'app_title = "Prime Ledger"'),
	(r'app_publisher\s*=\s*["\'][^"\']*["\']', 'app_publisher = "Prime Ledger"'),
	(
		r'app_logo_url\s*=\s*["\'][^"\']*["\']',
		'app_logo_url = "/assets/erpnext/images/prime-ledger-logo.svg"',
	),
	(
		r'["\']/assets/erpnext/images/erpnext-logo\.svg["\']',
		'"/assets/erpnext/images/prime-ledger-logo.svg"',
	),
	(
		r'["\']/assets/erpnext/images/erpnext-favicon\.svg["\']',
		'"/assets/erpnext/images/prime-ledger-favicon.svg"',
	),
	(
		r'email_brand_image\s*=\s*["\'][^"\']*["\']',
		'email_brand_image = "/assets/erpnext/images/prime-ledger-logo.svg"',
	),
]
for pattern, repl in brand_subs:
	text2, n = re.subn(pattern, repl, text)
	if n:
		text = text2
		print(f"brand_sub_ok:{pattern[:40]}:{n}")

# Product string scrub in hooks comments / footers if present
if "ERPNext" in text:
	# Keep package identifiers (erpnext.xxx) but scrub product title tokens in string literals
	text2, n = re.subn(r'(["\'])ERPNext\1', r"\1Prime Ledger\1", text)
	if n:
		text = text2
		print(f"erpnext_literal_scrubbed:{n}")

# Hub stock footer is unquoted HTML, not a "ERPNext" Python string
if "via_email_footer" in text or "frappe.io/erpnext" in text:
	text = text.replace(
		"https://frappe.io/erpnext?source=via_email_footer",
		"https://github.com/0hammad0/prime-ledger",
	)
	text = text.replace(
		"https://erpnext.com?source=via_email_footer",
		"https://github.com/0hammad0/prime-ledger",
	)
	print("mail_footer_url_branded")
# Compact ">ERPNext<" and the stock indented-line label between <a>...</a>
text = text.replace(">ERPNext<", ">Prime Ledger<")
text2, n = re.subn(
	r'(<a class="text-muted"[^>]*>)\s*ERPNext\s*(</a>)',
	r"\1Prime Ledger\2",
	text,
	count=1,
)
if n:
	text = text2
	print("mail_footer_branded")

# Website login helpers on every site (signup ticket + apex redirect)
if "login_simple.js" not in text:
	if 'web_include_css = "erpnext-web.bundle.css"' in text:
		text = text.replace(
			'web_include_css = "erpnext-web.bundle.css"',
			'web_include_css = "erpnext-web.bundle.css"\n'
			'web_include_js = ["/assets/erpnext/js/login_simple.js"]',
			1,
		)
		print("web_include_js_login_simple")
	else:
		text += '\nweb_include_js = ["/assets/erpnext/js/login_simple.js"]\n'
		print("web_include_js_login_simple_appended")

hooks.write_text(text)

patches = Path("/home/frappe/frappe-bench/apps/erpnext/erpnext/patches.txt")
pt = patches.read_text()
for line in (
	"erpnext.patches.v16_0.restore_frappe_portal_settings",
	"erpnext.patches.v16_0.seed_portal_control",
	"erpnext.patches.v16_0.seed_pl_tenant",
):
	if line not in pt:
		pt = pt.rstrip() + "\n" + line + "\n"
		print("patches_txt_added", line)
patches.write_text(pt)
print("inject_portal_hooks_ok")
