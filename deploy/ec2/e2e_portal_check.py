"""Read-only / safe E2E checks for portal boot. Run via: bench --site frontend execute erpnext... or console exec."""

from __future__ import annotations

import frappe


def run():
	out = []
	out.append(("is_single", frappe.db.get_value("DocType", "PL Portal Settings", "issingle")))
	out.append(("portal_module_count", frappe.db.count("Portal Module") if frappe.db.table_exists("Portal Module") else None))

	results = []
	for user in (
		"admin@primeledger.local",
		"bigbird@hotmail.com",
		"bigbirdvr@gmail.com",
		"vehari@live.com",
	):
		row = {"user": user}
		try:
			frappe.set_user(user)
			from erpnext.startup.boot import boot_session

			bootinfo = frappe._dict(
				sysdefaults=frappe._dict(),
				docs=[],
				page_info={},
				customer_count=0,
				user={"name": user},
			)
			boot_session(bootinfo)
			row["boot_companies"] = len(bootinfo.docs)

			from erpnext.portal_control.api import get_portal_boot

			pb = get_portal_boot()
			row["modules"] = len(pb.get("modules") or [])
			row["super"] = pb.get("is_super_admin")
			row["app"] = pb.get("app_name")

			try:
				frappe.sessions.get()
				row["session"] = "ok"
			except Exception as e:
				row["session"] = f"fail:{type(e).__name__}:{str(e)[:160]}"
			row["status"] = "OK" if row.get("session") == "ok" else "SESS_FAIL"
		except Exception as e:
			row["status"] = "FAIL"
			row["error"] = f"{type(e).__name__}:{str(e)[:200]}"
			try:
				frappe.db.rollback()
			except Exception:
				pass
		results.append(row)

	errors = []
	for r in frappe.get_all("Error Log", fields=["creation", "error"], order_by="creation desc", limit=12):
		errors.append({"creation": str(r.creation), "error": (r.error or "").replace("\n", " ")[:180]})

	return {"meta": dict(out), "users": results, "errors": errors}
