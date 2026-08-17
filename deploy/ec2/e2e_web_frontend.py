#!/usr/bin/env python3
"""E2E: new web frontend APIs against a freshly signed-up tenant.

Phase 1 (this process): guest signup on apex → Super Admin approve.
Phase 2: operator runs provision-approved.sh (separate, slow).
Phase 3: login on the new host and probe every method the web app calls.
"""

from __future__ import annotations

import http.cookiejar
import json
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

APEX = "https://65.1.92.180.sslip.io"
PEM = "/Users/hammad/Personal/aws pem/prime_ledger_aws_pem.pem"
SSH_HOST = "ubuntu@65.1.92.180"
CTX = ssl._create_unverified_context()
FAILS: list[str] = []


def ssh(remote: str, timeout: int = 40) -> tuple[int, str, str]:
    p = subprocess.run(
        [
            "ssh",
            "-i",
            PEM,
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "ConnectTimeout=20",
            SSH_HOST,
            remote,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return p.returncode, p.stdout or "", p.stderr or ""


def opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler(context=CTX),
    )


def csrf(op, base: str, path: str = "/start") -> str:
    with op.open(urllib.request.Request(f"{base}{path}"), timeout=25) as r:
        html = r.read().decode("utf-8", "replace")
    m = re.search(r'csrf_token\s*=\s*["\']([^"\']+)', html)
    return m.group(1) if m else ""


def call(op, base: str, method: str, data=None, token: str = "", as_get: bool = False):
    url = f"{base}/api/method/{method}"
    headers = {
        "Accept": "application/json",
        "X-Frappe-CSRF-Token": token or "",
        "X-Requested-With": "XMLHttpRequest",
    }
    body = None
    if as_get and data:
        url += "?" + urllib.parse.urlencode({k: v if isinstance(v, str) else json.dumps(v) for k, v in data.items()})
    elif data is not None:
        body = urllib.parse.urlencode(
            {k: v if isinstance(v, str) else json.dumps(v) for k, v in data.items()}
        ).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with op.open(req, timeout=60) as r:
            raw = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(raw)
            except Exception:
                return r.status, {"_raw": raw[:240]}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_raw": raw[:300]}


def check(name: str, ok: bool, extra: str = "") -> None:
    print(("PASS" if ok else "FAIL"), name, extra)
    if not ok:
        FAILS.append(name)


def msg(data: dict):
    return data.get("message") if isinstance(data, dict) else data


def admin_password() -> str:
    rc, out, err = ssh("cat ~/deploy-ec2/.admin_password")
    if rc == 0 and out.strip():
        return out.strip()
    rc, out, err = ssh("grep ^ADMIN_PASSWORD= ~/deploy-ec2/.env | cut -d= -f2-")
    return (out or "").strip().strip("'\"")


def http_status(url: str) -> int:
    req = urllib.request.Request(url, headers={"Accept": "text/html,application/json"})
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=25) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def phase_signup(stamp: str) -> dict:
    org = f"Nexis E2E {stamp}"
    slug = f"nexise2e{stamp}"
    email = f"owner.{slug}@example.com"
    password = f"NexisE2e!{stamp}"
    op = opener()
    token = csrf(op, APEX)
    st, data = call(
        op,
        APEX,
        "erpnext.portal_control.tenants.signup_organization",
        {
            "organization_name": org,
            "admin_full_name": "Nexis E2E Owner",
            "admin_email": email,
            "password": password,
            "site_name": slug,
        },
        token=token,
    )
    payload = msg(data) if isinstance(msg(data), dict) else data
    check("signup_organization", st == 200 and isinstance(payload, dict) and payload.get("status") in ("Pending", "Approved"), str(payload)[:240])
    if st != 200:
        raise SystemExit(f"signup failed {st} {data}")
    host = payload.get("host") or f"{slug}.65.1.92.180.sslip.io"
    print("SIGNUP", json.dumps({"slug": slug, "host": host, "email": email, "status": payload.get("status")}))
    return {"slug": slug, "org": org, "email": email, "password": password, "host": host}


def phase_approve(slug: str) -> dict:
    pwd = admin_password()
    if not pwd:
        raise SystemExit("no apex admin password")
    op = opener()
    st, data = call(op, APEX, "login", {"usr": "Administrator", "pwd": pwd})
    check("apex_admin_login", st == 200 and (msg(data) == "Logged In" or data.get("message") == "Logged In"), str(data)[:160])
    token = csrf(op, APEX)
    st, data = call(op, APEX, "erpnext.portal_control.tenants.approve_tenant", {"site_name": slug}, token=token)
    payload = msg(data) if isinstance(msg(data), dict) else data
    check("approve_tenant", st == 200 and isinstance(payload, dict) and payload.get("login_url"), str(payload)[:300])
    if st != 200:
        raise SystemExit(f"approve failed {st} {data}")
    print("APPROVE", json.dumps({"login_url": payload.get("login_url"), "status": payload.get("status"), "host": payload.get("host")}))
    return payload


def phase_tenant_probe(host: str, email: str, password: str) -> None:
    base = f"https://{host}" if not host.startswith("http") else host
    base = base.rstrip("/")
    login_url = f"{base}/login"
    st = http_status(login_url)
    check("tenant_login_page", st in (200, 301, 302), f"HTTP {st} {login_url}")
    op = opener()
    st, data = call(op, base, "login", {"usr": email, "pwd": password})
    check("tenant_org_admin_login", st == 200 and data.get("message") == "Logged In", str(data)[:200])
    if st != 200:
        # fallback Administrator with site bootstrap password
        admin_pw = admin_password()
        st2, data2 = call(op, base, "login", {"usr": "Administrator", "pwd": admin_pw})
        check("tenant_administrator_fallback", st2 == 200, str(data2)[:200])
        if st2 != 200:
            return
    token = csrf(op, base)

    def expect(name: str, method: str, data=None, as_get=False, ok=lambda s, d: s == 200):
        s, d = call(op, base, method, data, token=token, as_get=as_get)
        extra = ""
        m = msg(d)
        if isinstance(m, dict):
            extra = ",".join(list(m)[:6])
        elif isinstance(m, list):
            extra = f"n={len(m)}"
        else:
            extra = str(m)[:160]
        if d.get("exc_type"):
            extra = f"{d.get('exc_type')} {extra}"
        check(name, ok(s, d), extra)
        return s, d

    expect("get_portal_boot", "erpnext.portal_control.api.get_portal_boot", as_get=True)
    s, home = expect("get_home", "erpnext.portal_control.dashboard.get_home", as_get=True)
    home_msg = msg(home) if isinstance(msg(home), dict) else {}
    company = home_msg.get("company") or ""
    expect("search", "erpnext.portal_control.dashboard.search", {"q": "ne"})
    expect("set_company", "erpnext.portal_control.dashboard.set_company", {"company": company} if company else None)
    expect("tax_templates", "erpnext.portal_control.dashboard.tax_templates", {"company": company} if company else {}, as_get=True)
    expect("link_options_customer", "erpnext.portal_control.workspace.link_options", {"doctype": "Customer", "q": ""})
    expect("link_options_item", "erpnext.portal_control.workspace.link_options", {"doctype": "Item", "q": ""})
    expect(
        "request_password_reset",
        "erpnext.portal_control.auth.request_password_reset",
        {"email": email},
    )
    expect("save_todo", "erpnext.portal_control.workspace.save_todo", {"description": "E2E note", "date": time.strftime("%Y-%m-%d")})
    expect("get_list_todo", "frappe.client.get_list", {"doctype": "ToDo", "fields": ["name", "description"], "limit_page_length": 10})
    expect("get_list_customer", "frappe.client.get_list", {"doctype": "Customer", "fields": ["name"], "limit_page_length": 10})
    expect("get_list_item", "frappe.client.get_list", {"doctype": "Item", "fields": ["name"], "limit_page_length": 10})
    expect("get_list_si", "frappe.client.get_list", {"doctype": "Sales Invoice", "fields": ["name", "grand_total"], "limit_page_length": 10})
    expect("get_list_pi", "frappe.client.get_list", {"doctype": "Purchase Invoice", "fields": ["name"], "limit_page_length": 10})
    expect("get_list_so", "frappe.client.get_list", {"doctype": "Sales Order", "fields": ["name"], "limit_page_length": 10})
    expect("get_list_po", "frappe.client.get_list", {"doctype": "Purchase Order", "fields": ["name"], "limit_page_length": 10})
    expect("get_list_lead", "frappe.client.get_list", {"doctype": "Lead", "fields": ["name"], "limit_page_length": 10})
    expect("get_list_employee", "frappe.client.get_list", {"doctype": "Employee", "fields": ["name"], "limit_page_length": 10})
    expect("get_list_account", "frappe.client.get_list", {"doctype": "Account", "fields": ["name"], "limit_page_length": 10})
    expect("get_list_bin", "frappe.client.get_list", {"doctype": "Bin", "fields": ["name", "item_code"], "limit_page_length": 10})
    expect("get_list_company", "frappe.client.get_list", {"doctype": "Company", "fields": ["name"], "limit_page_length": 10})
    expect("get_count_customer", "frappe.client.get_count", {"doctype": "Customer"})
    expect("run_report_ar", "erpnext.portal_control.workspace.run_named_report", {"report_name": "Accounts Receivable Summary", "filters": {"company": company}})
    expect("mark_notification_read", "erpnext.portal_control.dashboard.mark_notification_read", {})
    expect("record_open", "erpnext.portal_control.dashboard.record_open", {"doctype": "ToDo", "name": "x", "title": "x"})
    s, seeded = expect(
        "seed_demo_workspace",
        "erpnext.portal_control.demo.seed_demo_workspace",
        {"company": company} if company else {},
    )
    s, home2 = expect("get_home_after_seed", "erpnext.portal_control.dashboard.get_home", as_get=True)
    h2 = msg(home2) if isinstance(msg(home2), dict) else {}
    ar = (h2.get("receivables") or {}).get("amount") if isinstance(h2, dict) else 0
    check("home_receivables_nonzero_after_seed", bool(ar), f"ar={ar}")
    # create invoice via quick_create if item exists
    s, items = call(op, base, "erpnext.portal_control.workspace.link_options", {"doctype": "Item", "q": "NEXIS"}, token=token)
    item_rows = msg(items) if isinstance(msg(items), list) else []
    s, customers = call(op, base, "erpnext.portal_control.workspace.link_options", {"doctype": "Customer", "q": "Nexis"}, token=token)
    cust_rows = msg(customers) if isinstance(msg(customers), list) else []
    if item_rows and cust_rows:
        s, created = expect(
            "quick_create_sales_invoice",
            "erpnext.portal_control.workspace.quick_create",
            {
                "doctype": "Sales Invoice",
                "party": cust_rows[0]["name"],
                "items": [{"item_code": item_rows[0]["name"], "qty": 1, "rate": 100}],
                "company": company,
                "submit": 0,
            },
        )
        created_msg = msg(created) if isinstance(msg(created), dict) else {}
        name = created_msg.get("name")
        if name:
            expect("get_doc_si", "frappe.client.get", {"doctype": "Sales Invoice", "name": name})
            expect(
                "submit_document",
                "erpnext.portal_control.workspace.submit_document",
                {"doctype": "Sales Invoice", "name": name},
            )
    expect("logout", "logout", {"_": "1"})


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "signup"
    if phase == "signup":
        stamp = time.strftime("%H%M%S")
        info = phase_signup(stamp)
        approved = phase_approve(info["slug"])
        out = {**info, "login_url": approved.get("login_url"), "approved_host": approved.get("host")}
        pathlib_write = __import__("pathlib").Path("/tmp/pl_e2e_tenant.json")
        pathlib_write.write_text(json.dumps(out, indent=2))
        print("WROTE", pathlib_write)
        print("NEXT: bash ~/deploy-ec2/provision-approved.sh", info["slug"])
        return
    if phase == "probe":
        info = json.loads(__import__("pathlib").Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/pl_e2e_tenant.json").read_text())
        phase_tenant_probe(info["host"], info["email"], info["password"])
        print("FAILS", len(FAILS), *FAILS)
        sys.exit(1 if FAILS else 0)
    raise SystemExit("usage: e2e_web_frontend.py signup|probe [json]")


if __name__ == "__main__":
    main()
