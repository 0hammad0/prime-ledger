#!/usr/bin/env python3
import json
import pathlib
import re
import ssl
import urllib.parse
import urllib.request
import http.cookiejar

BASE = "https://65.1.92.180.sslip.io"


def pw():
	p = pathlib.Path("/home/ubuntu/deploy-ec2/.admin_password")
	if p.exists():
		return p.read_text().strip()
	for line in pathlib.Path("/home/ubuntu/deploy-ec2/.env").read_text().splitlines():
		if line.startswith("ADMIN_PASSWORD="):
			return line.split("=", 1)[1].strip().strip("'\"")
	return ""


def main():
	password = pw()
	cj = http.cookiejar.CookieJar()
	opener = urllib.request.build_opener(
		urllib.request.HTTPCookieProcessor(cj),
		urllib.request.HTTPSHandler(context=ssl._create_unverified_context()),
	)
	data = urllib.parse.urlencode(
		{"usr": "admin@primeledger.local", "pwd": password, "cmd": "login"}
	).encode()
	req = urllib.request.Request(
		f"{BASE}/",
		data=data,
		headers={
			"Content-Type": "application/x-www-form-urlencoded",
			"X-Requested-With": "XMLHttpRequest",
		},
	)
	with opener.open(req) as r:
		body = r.read().decode()
	j = json.loads(body)
	print(
		"FORM_LOGIN",
		{k: j.get(k) for k in ("message", "home_page", "redirect_to", "full_name")},
	)

	for path in ("/portal", "/portal/tenant"):
		with opener.open(urllib.request.Request(f"{BASE}{path}")) as r:
			html = r.read().decode("utf-8", "replace")
			print(
				"PAGE",
				path,
				r.status,
				"root",
				'id="root"' in html,
				"tb",
				"Traceback" in html or "SessionBootFailed" in html,
			)

	with opener.open(urllib.request.Request(f"{BASE}/portal")) as r:
		html = r.read().decode("utf-8", "replace")
	m = re.search(r"csrf_token\s*=\s*[\"']([^\"']+)", html)
	if not m:
		print("NO_CSRF")
		return
	csrf = m.group(1)
	req = urllib.request.Request(
		f"{BASE}/api/method/erpnext.portal_control.api.get_portal_boot",
		data=b"{}",
		headers={"Content-Type": "application/json", "X-Frappe-CSRF-Token": csrf},
	)
	with opener.open(req) as r:
		msg = json.loads(r.read().decode()).get("message") or {}
	print(
		"API_BOOT",
		"modules",
		len(msg.get("modules") or []),
		"companies",
		len(msg.get("companies") or []),
		"app",
		msg.get("app_name"),
		"super",
		msg.get("is_super_admin"),
	)


if __name__ == "__main__":
	main()
