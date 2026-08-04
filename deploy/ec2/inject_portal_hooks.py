from pathlib import Path

hooks = Path("/home/frappe/frappe-bench/apps/erpnext/erpnext/hooks.py")
text = hooks.read_text()
needle = '{"from_route": "/portal", "to_route": "portal"}'
if needle not in text:
	old = '{"from_route": "/banking/<path:app_path>", "to_route": "banking"},'
	if old in text:
		hooks.write_text(
			text.replace(
				old,
				old
				+ '\n\t{"from_route": "/portal", "to_route": "portal"},'
				+ '\n\t{"from_route": "/portal/<path:app_path>", "to_route": "portal"},',
				1,
			)
		)

patches = Path("/home/frappe/frappe-bench/apps/erpnext/erpnext/patches.txt")
pt = patches.read_text()
for line in (
	"erpnext.patches.v16_0.restore_frappe_portal_settings",
	"erpnext.patches.v16_0.seed_portal_control",
):
	if line not in pt:
		pt = pt.rstrip() + "\n" + line + "\n"
patches.write_text(pt)
