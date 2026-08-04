#!/usr/bin/env python3
"""Post-login E2E: portal pages, APIs, and desk routes after authentication."""
from __future__ import annotations

import json
import pathlib
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import http.cookiejar

BASE = "https://65.1.92.180.sslip.io"
CTX = ssl._create_unverified_context()

PORTAL_PATHS = [
	"/portal",
	"/portal/admin",
	"/portal/admin/modules",
	"/portal/admin/tenants",
	"/portal/admin/users",
	"/portal/tenant",
	"/portal/tenant/products",
	"/portal/tenant/inventory",
	"/portal/tenant/sales",
	"/portal/tenant/purchases",
	"/portal/tenant/finance",
	"/portal/tenant/reports",
	"/portal/tenant/settings",
]

DESK_PATHS = [
	"/app",
	"/app/home",
	"/app/item",
	"/app/sales-invoice",
	"/app/purchase-invoice",
	"/app/customer",
	"/app/company",
]


def admin_pw() -> str:
	p = pathlib.Path("/home/ubuntu/deploy-ec2/.admin_password")
	if p.exists():
		return p.read_text().strip()
	for line in pathlib.Path("/home/ubuntu/deploy-ec2/.env").read_text().splitlines():
		if line.startswith("ADMIN_PASSWORD="):
			return line.split("=", 1)[1].strip().strip("'\"")
	return ""


def make_opener():
	cj = http.cookiejar.CookieJar()
	op = urllib.request.build_opener(
		urllib.request.HTTPCookieProcessor(cj),
		urllib.request.HTTPSHandler(context=CTX),
	)
	return op


def login(op, usr: str, pwd: str) -> dict:
	data = urllib.parse.urlencode({"usr": usr, "pwd": pwd, "cmd": "login"}).encode()
	req = urllib.request.Request(
		f"{BASE}/",
		data=data,
		headers={
			"Content-Type": "application/x-www-form-urlencoded",
			"X-Requested-With": "XMLHttpRequest",
		},
	)
	with op.open(req) as r:
		return json.loads(r.read().decode())


def get_csrf(op) -> str | None:
	with op.open(urllib.request.Request(f"{BASE}/portal")) as r:
		html = r.read().decode("utf-8", "replace")
	m = re.search(r"csrf_token\s*=\s*[\"']([^\"']+)", html)
	return m.group(1) if m else None


def api(op, method: str, csrf: str | None, params: dict | None = None, post: bool = False):
	url = f"{BASE}/api/method/{method}"
	headers = {
		"Accept": "application/json",
		"X-Frappe-CSRF-Token": csrf or "",
		"X-Requested-With": "XMLHttpRequest",
	}
	try:
		if post:
			data = urllib.parse.urlencode(params or {}).encode()
			headers["Content-Type"] = "application/x-www-form-urlencoded"
			req = urllib.request.Request(url, data=data, headers=headers)
		else:
			if params:
				url += "?" + urllib.parse.urlencode(params)
			req = urllib.request.Request(url, headers=headers)
		with op.open(req) as r:
			return r.status, json.loads(r.read().decode())
	except urllib.error.HTTPError as e:
		raw = e.read().decode("utf-8", "replace")
		try:
			return e.code, json.loads(raw)
		except Exception:
			return e.code, {"_raw": raw[:300]}


def page_check(op, path: str) -> dict:
	try:
		with op.open(urllib.request.Request(f"{BASE}{path}")) as r:
			html = r.read().decode("utf-8", "replace")
			bad = any(
				x in html
				for x in (
					"SessionBootFailed",
					"Traceback (most recent call last)",
					"Internal Server Error",
				)
			)
			return {
				"path": path,
				"status": r.status,
				"bad": bad,
				"len": len(html),
			}
	except urllib.error.HTTPError as e:
		raw = e.read().decode("utf-8", "replace")
		bad = any(x in raw for x in ("SessionBootFailed", "Traceback", "Internal Server Error"))
		return {"path": path, "status": e.code, "bad": bad or e.code >= 500, "len": len(raw)}
	except Exception as e:
		return {"path": path, "status": 0, "bad": True, "err": str(e)[:120]}


def run_as(label: str, usr: str, pwd: str) -> dict:
	print(f"\n===== {label} ({usr}) =====")
	op = make_opener()
	try:
		body = login(op, usr, pwd)
	except Exception as e:
		print("LOGIN_FAIL", type(e).__name__, str(e)[:160])
		return {"ok": False, "login": "fail"}

	print(
		"LOGIN",
		{k: body.get(k) for k in ("message", "home_page", "redirect_to", "full_name", "exc_type")},
	)
	if body.get("message") != "Logged In":
		return {"ok": False, "login": body}

	csrf = get_csrf(op)
	print("CSRF", bool(csrf))

	st, boot = api(op, "erpnext.portal_control.api.get_portal_boot", csrf)
	msg = boot.get("message") if isinstance(boot, dict) else None
	if not isinstance(msg, dict):
		print(
			"BOOT_FAIL",
			st,
			boot.get("exc_type"),
			(boot.get("exception") or boot.get("_error_message") or str(boot))[:220],
		)
		return {"ok": False, "boot": "fail"}

	print(
		"PORTAL_BOOT",
		"modules",
		len(msg.get("modules") or []),
		"companies",
		len(msg.get("companies") or []),
		"super",
		msg.get("is_super_admin"),
		"app",
		msg.get("app_name"),
		"user",
		(msg.get("user") or {}).get("name"),
	)

	st2, logged = api(op, "frappe.auth.get_logged_user", csrf)
	print("LOGGED_USER", st2, logged.get("message"))

	# Desk list API — proves authenticated desk data layer works after login
	st3, items = api(
		op,
		"frappe.client.get_list",
		csrf,
		{"doctype": "Item", "fields": '["name"]', "limit_page_length": 1},
	)
	desk_api_ok = st3 < 400 and not items.get("exc_type")
	print(
		"DESK_API",
		st3,
		"ok" if desk_api_ok else "FAIL",
		items.get("exc_type") or "",
		(str(items.get("exception") or items.get("_error_message") or items.get("message") or "")[:160]),
	)

	bad_pages = []
	for path in PORTAL_PATHS:
		info = page_check(op, path)
		mark = "BAD" if info.get("bad") or info["status"] >= 400 else "ok"
		if mark != "ok":
			bad_pages.append(info)
		print("PAGE", mark, info["path"], info["status"], "bad" if info.get("bad") else "")

	desk_bad = []
	for path in DESK_PATHS:
		info = page_check(op, path)
		if info["status"] >= 500 or info.get("bad"):
			desk_bad.append(info)
			print("DESK BAD", info)
		else:
			print("DESK ok", info["path"], info["status"])

	mod_bad = []
	for m in msg.get("modules") or []:
		route = m.get("desk_route") or ""
		if not route.startswith("/app"):
			continue
		info = page_check(op, route)
		if info["status"] >= 500 or info.get("bad"):
			mod_bad.append({"module": m.get("module_key"), **info})
			print("MOD BAD", m.get("module_key"), info)
		else:
			print("MOD ok", m.get("module_key"), route, info["status"])

	redirect_ok = bool(body.get("redirect_to") and str(body.get("redirect_to")).startswith("/portal"))
	ok = not bad_pages and not desk_bad and not mod_bad and desk_api_ok and redirect_ok
	print(
		"SUMMARY",
		label,
		"OK" if ok else "FAIL",
		{
			"bad_pages": len(bad_pages),
			"desk_bad": len(desk_bad),
			"mod_bad": len(mod_bad),
			"desk_api_ok": desk_api_ok,
			"redirect_ok": redirect_ok,
			"redirect_to": body.get("redirect_to"),
		},
	)
	return {
		"ok": ok,
		"redirect_to": body.get("redirect_to"),
		"modules": len(msg.get("modules") or []),
		"companies": len(msg.get("companies") or []),
		"bad_pages": bad_pages,
		"desk_bad": desk_bad,
		"mod_bad": mod_bad,
	}


def main():
	result = run_as("ADMIN", "admin@primeledger.local", admin_pw())
	print("\nFINAL", "PASS" if result.get("ok") else "FAIL")
	raise SystemExit(0 if result.get("ok") else 1)


if __name__ == "__main__":
	main()
