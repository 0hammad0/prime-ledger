#!/usr/bin/env python3
import json
import pathlib
import re
import ssl
import urllib.error
import urllib.request
import http.cookiejar

BASE = "https://65.1.92.180.sslip.io"


def admin_password() -> str:
	p = pathlib.Path("/home/ubuntu/deploy-ec2/.admin_password")
	if p.exists():
		return p.read_text().strip()
	env = pathlib.Path("/home/ubuntu/deploy-ec2/.env")
	if env.exists():
		for line in env.read_text().splitlines():
			if line.startswith("ADMIN_PASSWORD="):
				return line.split("=", 1)[1].strip().strip("'\"")
	return ""


def main():
	pw = admin_password()
	if not pw:
		print("NO_ADMIN_PASSWORD")
		return
	cj = http.cookiejar.CookieJar()
	opener = urllib.request.build_opener(
		urllib.request.HTTPCookieProcessor(cj),
		urllib.request.HTTPSHandler(context=ssl._create_unverified_context()),
	)
	req = urllib.request.Request(
		f"{BASE}/api/method/login",
		data=json.dumps({"usr": "admin@primeledger.local", "pwd": pw}).encode(),
		headers={"Content-Type": "application/json"},
	)
	with opener.open(req) as r:
		login = json.loads(r.read().decode())
	print(
		"LOGIN",
		login.get("message"),
		"home",
		login.get("home_page"),
		"redirect_to",
		login.get("redirect_to"),
	)

	for path in ("/portal", "/portal/tenant", "/app"):
		req = urllib.request.Request(f"{BASE}{path}")
		try:
			with opener.open(req) as r:
				body = r.read().decode("utf-8", "replace")
				print(
					"OK",
					path,
					r.status,
					"len",
					len(body),
					"root",
					'id="root"' in body,
					"tb",
					"Traceback" in body,
				)
		except urllib.error.HTTPError as e:
			body = e.read().decode("utf-8", "replace")
			print("ERR", path, e.code, "len", len(body))
			m = re.search(
				r"(Unknown column[^<\n]+|ModuleNotFoundError:[^<\n]+|ProgrammingError:[^<\n]+|OperationalError:[^<\n]+|SessionBootFailed)",
				body,
			)
			print("  snip:", m.group(1) if m else body[:300].replace("\n", " "))

	req = urllib.request.Request(
		f"{BASE}/api/method/erpnext.portal_control.api.get_portal_boot",
		data=b"{}",
		headers={"Content-Type": "application/json"},
	)
	try:
		with opener.open(req) as r:
			data = json.loads(r.read().decode())
		msg = data.get("message") or {}
		print(
			"API_BOOT modules",
			len(msg.get("modules") or []),
			"companies",
			len(msg.get("companies") or []),
			"app",
			msg.get("app_name"),
		)
	except urllib.error.HTTPError as e:
		print("API_BOOT_ERR", e.code, e.read()[:300])


if __name__ == "__main__":
	main()
