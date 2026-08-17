#!/usr/bin/env python3
"""Live smoke of Separate Frontend API spec — guest + admin."""
from __future__ import annotations

import json
import pathlib
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar

BASE = "https://65.1.92.180.sslip.io"
CTX = ssl._create_unverified_context()
fails: list[str] = []


def make_opener():
	cj = http.cookiejar.CookieJar()
	op = urllib.request.build_opener(
		urllib.request.HTTPCookieProcessor(cj),
		urllib.request.HTTPSHandler(context=CTX),
	)
	return op


def call(op, method: str | None, *, data=None, csrf="", path=None):
	url = f"{BASE}{path}" if path else f"{BASE}/api/method/{method}"
	headers = {
		"Accept": "application/json",
		"X-Frappe-CSRF-Token": csrf or "",
		"X-Requested-With": "XMLHttpRequest",
	}
	body = None
	if data is not None:
		body = urllib.parse.urlencode(data).encode()
		headers["Content-Type"] = "application/x-www-form-urlencoded"
	req = urllib.request.Request(url, data=body, headers=headers)
	try:
		with op.open(req) as r:
			raw = r.read().decode()
			try:
				return r.status, json.loads(raw)
			except Exception:
				return r.status, {"_html": raw[:180]}
	except urllib.error.HTTPError as e:
		raw = e.read().decode("utf-8", "replace")
		try:
			return e.code, json.loads(raw)
		except Exception:
			return e.code, {"_raw": raw[:240]}


def check(name: str, ok: bool, extra="") -> None:
	print(("PASS" if ok else "FAIL"), name, extra)
	if not ok:
		fails.append(name)


def admin_pw() -> str:
	p = pathlib.Path("/home/ubuntu/deploy-ec2/.admin_password")
	if p.exists():
		return p.read_text().strip()
	env = pathlib.Path("/home/ubuntu/deploy-ec2/.env")
	if env.exists():
		for line in env.read_text().splitlines():
			if line.startswith("ADMIN_PASSWORD="):
				return line.split("=", 1)[1].strip().strip("'\"")
	return ""


def csrf_from(op, path: str) -> str:
	with op.open(urllib.request.Request(f"{BASE}{path}")) as r:
		html = r.read().decode("utf-8", "replace")
	m = re.search(r"csrf_token\s*=\s*[\"']([^\"']+)", html)
	return m.group(1) if m else ""


def main() -> int:
	op = make_opener()

	st, _ = call(op, None, path="/start")
	check("GET /start", st == 200, str(st))
	st, _ = call(op, None, path="/login")
	check("GET /login", st == 200, str(st))

	st, boot = call(op, "erpnext.portal_control.api.get_portal_boot")
	check(
		"guest get_portal_boot blocked",
		st in (401, 403, 417) or bool(boot.get("exc_type")),
		f"{st} {boot.get('exc_type')}",
	)
	st, tenants = call(op, "erpnext.portal_control.tenants.list_tenants")
	check(
		"guest list_tenants blocked",
		st in (401, 403, 417) or bool(tenants.get("exc_type")),
		f"{st} {tenants.get('exc_type')}",
	)
	st, users = call(op, None, path="/api/resource/User")
	check("guest User list blocked", st >= 400 or bool(users.get("exc_type")), str(st))

	csrf = csrf_from(op, "/start")
	stamp = str(int(time.time()))
	email = f"smoketest{stamp}@example.com"
	st, su = call(
		op,
		"erpnext.portal_control.tenants.signup_organization",
		data={
			"organization_name": f"Smoke Test {stamp}",
			"admin_full_name": "Smoke Tester",
			"admin_email": email,
			"password": "TestPass123",
		},
		csrf=csrf,
	)
	msg = su.get("message") if isinstance(su.get("message"), dict) else {}
	host_ok = str(msg.get("host") or "").endswith("65.1.92.180.sslip.io")
	check(
		"signup_organization Pending tenant",
		st == 200 and msg.get("status") == "Pending" and host_ok and not su.get("exc_type"),
		f"{st} status={msg.get('status')} host={msg.get('host')} slug={msg.get('site_name')} exc={su.get('exc_type')} err={str(su.get('_error_message') or su.get('exception') or su)[:220]}",
	)
	signup_slug = msg.get("site_name")

	st, gapp = call(
		op,
		"erpnext.portal_control.tenants.approve_tenant",
		data={"site_name": signup_slug or "x"},
		csrf=csrf,
	)
	check(
		"guest approve_tenant blocked",
		st in (401, 403, 417) or bool(gapp.get("exc_type")),
		f"{st} {gapp.get('exc_type')}",
	)

	op2 = make_opener()
	st, login = call(op2, "login", data={"usr": "admin@primeledger.local", "pwd": admin_pw()})
	check("POST /api/method/login", st == 200 and login.get("message") == "Logged In", f"{st} {login.get('message')}")

	csrf2 = csrf_from(op2, "/portal")
	st, who = call(op2, "frappe.auth.get_logged_user", csrf=csrf2)
	check(
		"get_logged_user",
		st == 200 and who.get("message") == "admin@primeledger.local",
		f"{st} {who.get('message')}",
	)

	st, boot = call(op2, "erpnext.portal_control.api.get_portal_boot", csrf=csrf2)
	bmsg = boot.get("message") or {}
	check(
		"get_portal_boot",
		st == 200 and bmsg.get("is_super_admin") is True and len(bmsg.get("modules") or []) >= 10,
		f"modules={len(bmsg.get('modules') or [])} tenants={len(bmsg.get('tenants') or [])}",
	)

	st, lt = call(op2, "erpnext.portal_control.tenants.list_tenants", csrf=csrf2)
	tlist = lt.get("message") if isinstance(lt.get("message"), list) else []
	slugs = [t.get("site_name") for t in tlist]
	check("list_tenants includes signup", signup_slug in slugs, f"n={len(tlist)} slug={signup_slug}")

	st, ap = call(
		op2,
		"erpnext.portal_control.tenants.approve_tenant",
		data={"site_name": signup_slug or ""},
		csrf=csrf2,
	)
	am = ap.get("message") if isinstance(ap.get("message"), dict) else {}
	login_url = str(am.get("login_url") or "")
	check(
		"approve_tenant Approved + invite URL",
		st == 200
		and am.get("status") == "Approved"
		and login_url.startswith("https://")
		and login_url.endswith("/login")
		and not ap.get("exc_type"),
		f"{st} status={am.get('status')} url={login_url} email={am.get('email')} err={str(ap.get('_error_message') or ap.get('exception') or ap.get('exc_type') or '')[:220]}",
	)
	st, lt2 = call(op2, "erpnext.portal_control.tenants.list_tenants", csrf=csrf2)
	tlist2 = lt2.get("message") if isinstance(lt2.get("message"), list) else []
	approved_row = next((t for t in tlist2 if t.get("site_name") == signup_slug), {})
	check(
		"tenant status is Approved after panel approve",
		approved_row.get("status") == "Approved",
		f"{approved_row.get('status')}",
	)
	st, eq = call(
		op2,
		"frappe.client.get_list",
		data={
			"doctype": "Email Queue",
			"fields": json.dumps(["name", "status"]),
			"limit_page_length": 5,
			"order_by": "creation desc",
		},
		csrf=csrf2,
	)
	check(
		"Email Queue readable after invite",
		st == 200 and not eq.get("exc_type"),
		f"{st} {eq.get('exc_type')} n={len(eq.get('message') or []) if isinstance(eq.get('message'), list) else 0}",
	)

	st, items = call(
		op2,
		"frappe.client.get_list",
		data={"doctype": "Item", "fields": json.dumps(["name"]), "limit_page_length": 1},
		csrf=csrf2,
	)
	check("frappe.client.get_list Item", st == 200 and not items.get("exc_type"), f"{st} {items.get('exc_type')}")

	fields = urllib.parse.quote('["name"]')
	st, cust = call(op2, None, path=f"/api/resource/Customer?limit_page_length=1&fields={fields}", csrf=csrf2)
	check("GET /api/resource/Customer", st == 200 and not cust.get("exc_type"), f"{st} {cust.get('exc_type')}")
	st, lead = call(op2, None, path=f"/api/resource/Lead?limit_page_length=1&fields={fields}", csrf=csrf2)
	check("GET /api/resource/Lead", st == 200 and not lead.get("exc_type"), f"{st} {lead.get('exc_type')}")

	st, ufind = call(
		op2,
		"frappe.client.get_list",
		data={
			"doctype": "User",
			"filters": json.dumps({"name": email}),
			"fields": json.dumps(["name"]),
			"limit_page_length": 1,
		},
		csrf=csrf2,
	)
	ulist = ufind.get("message") if isinstance(ufind.get("message"), list) else []
	check("signup did not create shared User", ulist == [], f"users={ulist}")

	st, dsu = call(
		op2,
		"frappe.client.get_value",
		data={"doctype": "Website Settings", "fieldname": "disable_signup"},
		csrf=csrf2,
	)
	val = dsu.get("message")
	ds = val.get("disable_signup") if isinstance(val, dict) else val
	check("disable_signup=1", str(ds) in ("1", "True") or ds == 1, f"{ds} raw={val}")

	st, lo = call(op2, "logout", data={"_": "1"}, csrf=csrf2)
	check("logout", st == 200 and not lo.get("exc_type"), f"{st} {lo.get('exc_type')}")

	print("\nRESULT", "PASS" if not fails else "FAIL", "failed=", fails)
	return 1 if fails else 0


if __name__ == "__main__":
	raise SystemExit(main())
