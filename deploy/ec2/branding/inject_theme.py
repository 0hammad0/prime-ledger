"""Inject / refresh Prime Ledger brand CSS into built asset bundles."""
from __future__ import annotations

from pathlib import Path

MARKER = "Prime Ledger desk / login skin"
CANDIDATES = [
	"/home/frappe/frappe-bench/apps/erpnext/erpnext/public/css/prime_ledger_brand.css",
	"/home/frappe/frappe-bench/sites/assets/erpnext/css/prime_ledger_brand.css",
]

css_src = next((Path(p) for p in CANDIDATES if Path(p).is_file()), None)
if not css_src:
	raise SystemExit(0)

skin = css_src.read_text(encoding="utf-8")
globs = [
	"/home/frappe/frappe-bench/sites/assets/erpnext/dist/css/*.css",
	"/home/frappe/frappe-bench/sites/assets/frappe/dist/css/desk*.css",
	"/home/frappe/frappe-bench/sites/assets/frappe/dist/css/login*.css",
	"/home/frappe/frappe-bench/sites/assets/frappe/dist/css/website*.css",
]

import glob

targets: list[Path] = []
for pattern in globs:
	targets.extend(Path(p) for p in glob.glob(pattern))

for path in targets:
	text = path.read_text(encoding="utf-8", errors="ignore")
	if MARKER in text and text.rfind(MARKER) > len(text) * 0.45:
		start = text.rfind("\n", 0, text.rfind(MARKER))
		if start == -1:
			start = text.rfind(MARKER)
		text = text[:start].rstrip() + "\n"
	if MARKER not in text:
		text = text.rstrip() + "\n\n" + skin + "\n"
		path.write_text(text, encoding="utf-8")
		print("themed", path)
	else:
		# Marker still present earlier in file — append refreshed copy
		text = text.rstrip() + "\n\n" + skin + "\n"
		path.write_text(text, encoding="utf-8")
		print("themed_append", path)

for dest in (
	Path("/home/frappe/frappe-bench/sites/assets/css"),
	Path("/home/frappe/frappe-bench/sites/assets/erpnext/css"),
	Path("/home/frappe/frappe-bench/sites/assets/erpnext/images"),
):
	dest.mkdir(parents=True, exist_ok=True)

Path("/home/frappe/frappe-bench/sites/assets/css/prime_ledger_brand.css").write_text(skin, encoding="utf-8")
Path("/home/frappe/frappe-bench/sites/assets/erpnext/css/prime_ledger_brand.css").write_text(
	skin, encoding="utf-8"
)
print("theme_inject_ok")
