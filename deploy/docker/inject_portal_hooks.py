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
line = "erpnext.patches.v16_0.seed_portal_control"
pt = patches.read_text()
if line not in pt:
	patches.write_text(pt.rstrip() + "\n" + line + "\n")
