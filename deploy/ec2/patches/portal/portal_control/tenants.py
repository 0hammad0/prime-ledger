# Copyright (c) 2026, Prime Ledger and Contributors
# License: GNU General Public License v3. See license.txt

"""Phase 2: multi-site tenant registry + public organization signup."""

from __future__ import annotations

import os
import re
import secrets

import frappe
from frappe import _
from frappe.utils import cint, now_datetime, validate_email_address, strip_html

from erpnext.portal_control.tenancy import is_super_admin

_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]{0,46}[a-z0-9])?$")
_RESERVED = frozenset({"frontend", "www", "admin", "api", "assets", "portal", "login", "start"})
_STATUSES = ("Pending", "Approved", "Provisioning", "Active", "Error", "Archived")
_OPEN_STATUSES = ("Pending", "Approved", "Provisioning", "Active")


def _slugify(name: str) -> str:
	s = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
	return s[:48] or "org"


def _clean_host(val: str) -> str:
	v = str(val or "").strip()
	v = re.sub(r"^https?://", "", v, flags=re.I)
	v = v.split("/")[0]
	# Drop port if present
	if v.count(":") == 1 and not v.startswith("["):
		v = v.split(":")[0]
	return v.strip().lower()


def _public_base_host() -> str:
	for key in ("public_host", "hostname"):
		val = frappe.conf.get(key)
		if val:
			host = _clean_host(val)
			if host and host not in ("https", "http", "localhost"):
				return host
	# host_name may be a full URL — clean carefully
	val = frappe.conf.get("host_name")
	if val:
		host = _clean_host(val)
		if host and host not in ("https", "http"):
			return host
	env = os.environ.get("PUBLIC_HOST")
	if env:
		return _clean_host(env)
	site = str(frappe.local.site or "")
	if "." in site:
		return _clean_host(site)
	return "localhost"


def _pwd_cache_key(site_name: str) -> str:
	return f"pl_tenant_signup_pwd:{(site_name or '').strip().lower()}"


def _cache_set_pwd(site_name: str, password: str) -> None:
	key = _pwd_cache_key(site_name)
	try:
		frappe.cache.set_value(key, password, expires_in_sec=7 * 24 * 3600, shared=True)
	except TypeError:
		frappe.cache.set_value(key, password, expires_in_sec=7 * 24 * 3600)


def _cache_get_pwd(site_name: str) -> str | None:
	key = _pwd_cache_key(site_name)
	pwd = None
	try:
		pwd = frappe.cache.get_value(key, shared=True)
	except TypeError:
		pwd = None
	if not pwd:
		pwd = frappe.cache.get_value(key)
	out = str(pwd).strip() if pwd else ""
	return out or None


def _cache_del_pwd(site_name: str) -> None:
	key = _pwd_cache_key(site_name)
	_cache_del(key)


def _cache_set(key: str, value, expires_in_sec: int) -> None:
	try:
		frappe.cache.set_value(key, value, expires_in_sec=expires_in_sec, shared=True)
	except TypeError:
		frappe.cache.set_value(key, value, expires_in_sec=expires_in_sec)


def _cache_get(key: str):
	value = None
	try:
		value = frappe.cache.get_value(key, shared=True)
	except TypeError:
		value = None
	if value is None:
		value = frappe.cache.get_value(key)
	return value


def _cache_del(key: str) -> None:
	for kwargs in ({"shared": True}, {}):
		try:
			frappe.cache.delete_value(key, **kwargs)
		except TypeError:
			continue
		except Exception:
			pass


def _on_control_plane() -> bool:
	if frappe.conf.get("pl_is_control_plane"):
		return True
	site = str(frappe.local.site or "")
	if site == "frontend":
		return True
	req = getattr(frappe.local, "request", None)
	host = ""
	if req is not None:
		host = (getattr(req, "host", None) or "").split(":")[0].lower()
	return bool(host) and host == _public_base_host()


def _poll_cache_key(token: str) -> str:
	return f"pl_signup_poll:{(token or '').strip()}"


def _ticket_cache_key(ticket: str) -> str:
	return f"pl_login_ticket:{(ticket or '').strip()}"


def _confirm_cache_key(token: str) -> str:
	return f"pl_signup_confirm:{(token or '').strip()}"


def _issue_poll_token(site_name: str) -> str:
	token = secrets.token_urlsafe(24)
	_cache_set(_poll_cache_key(token), (site_name or "").strip().lower(), 7 * 24 * 3600)
	return token


def _site_from_poll_token(token: str) -> str | None:
	site = _cache_get(_poll_cache_key(token))
	out = str(site).strip().lower() if site else ""
	return out or None


def _issue_confirm_token(site_name: str) -> str:
	token = secrets.token_urlsafe(32)
	_cache_set(_confirm_cache_key(token), (site_name or "").strip().lower(), 2 * 24 * 3600)
	return token


def _site_from_confirm_token(token: str) -> str | None:
	site = _cache_get(_confirm_cache_key(token))
	out = str(site).strip().lower() if site else ""
	return out or None


def _rate_limit_signup(email: str) -> None:
	"""Simple per-IP / email throttle for public org signup."""
	ip = getattr(getattr(frappe.local, "request", None), "remote_addr", None) or "unknown"
	for key, limit in (
		(f"pl_signup_ip:{ip}", 8),
		(f"pl_signup_email:{(email or '').lower()}", 3),
	):
		n = cint(frappe.cache.get_value(key) or 0) + 1
		frappe.cache.set_value(key, n, expires_in_sec=3600)
		if n > limit:
			frappe.throw(_("Too many signup attempts. Try again later."), frappe.ValidationError)


@frappe.whitelist()
def list_tenants():
	if not is_super_admin():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if not frappe.db.exists("DocType", "PL Tenant"):
		return []
	return frappe.get_all(
		"PL Tenant",
		fields=[
			"name",
			"organization_name",
			"site_name",
			"host",
			"status",
			"company",
			"admin_email",
			"admin_full_name",
			"creation",
			"notes",
		],
		order_by="creation desc",
	)


def _insert_pending_tenant(
	*,
	organization_name: str,
	site_name: str | None,
	admin_email: str | None,
	admin_full_name: str | None = None,
	company: str | None = None,
	host: str | None = None,
	notes: str | None = None,
) -> dict:
	if not frappe.db.exists("DocType", "PL Tenant"):
		frappe.throw(_("PL Tenant DocType is not installed. Run migrate."))

	organization_name = (organization_name or "").strip()
	if not organization_name:
		frappe.throw(_("Organization name is required"))

	slug = (site_name or _slugify(organization_name)).strip().lower()
	if not _SLUG_RE.match(slug) or slug in _RESERVED:
		frappe.throw(_("Invalid or reserved organization id. Try another name."))

	if frappe.db.exists("PL Tenant", slug):
		frappe.throw(_("That organization id is already taken. Choose another name."))

	base = _public_base_host()
	host = (host or f"{slug}.{base}").strip().lower()
	company = (company or organization_name).strip()
	admin_email = (admin_email or "").strip().lower() or None
	admin_full_name = (admin_full_name or "").strip() or None

	doc = frappe.get_doc(
		{
			"doctype": "PL Tenant",
			"organization_name": organization_name,
			"site_name": slug,
			"host": host,
			"status": "Pending",
			"company": company,
			"admin_email": admin_email,
			"admin_full_name": admin_full_name,
			"notes": notes
			or "Pending provisioning. Run: bash deploy/ec2/provision-tenant.sh {0} \"{1}\"".format(
				slug, organization_name
			),
		}
	)
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	return {
		"tenant": doc.name,
		"site_name": slug,
		"host": host,
		"status": doc.status,
		"admin_email": admin_email,
		"provision_hint": f'bash deploy/ec2/provision-tenant.sh {slug} "{organization_name}"'
		+ (f" {admin_email}" if admin_email else ""),
	}


@frappe.whitelist()
def register_tenant(
	organization_name: str,
	site_name: str | None = None,
	admin_email: str | None = None,
	company: str | None = None,
	host: str | None = None,
):
	"""Super Admin: register a tenant row (does not create the Frappe site)."""
	if not is_super_admin():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return _insert_pending_tenant(
		organization_name=organization_name,
		site_name=site_name,
		admin_email=admin_email,
		company=company,
		host=host,
	)


@frappe.whitelist(allow_guest=True)
def signup_organization(
	organization_name: str,
	admin_full_name: str,
	admin_email: str,
	password: str,
	site_name: str | None = None,
):
	"""Public: create a Pending organization (tenant). Does NOT add a shared-site desk user.

	Ops provisions the private tenant site later; first admin is created on that site only.
	"""
	organization_name = (organization_name or "").strip()
	admin_full_name = (admin_full_name or "").strip()
	admin_email = (admin_email or "").strip().lower()
	password = password or ""

	if len(organization_name) < 2:
		frappe.throw(_("Enter your organization name"))
	if len(admin_full_name) < 2:
		frappe.throw(_("Enter your full name"))
	if not validate_email_address(admin_email):
		frappe.throw(_("Enter a valid work email"))
	if len(password) < 8:
		frappe.throw(_("Password must be at least 8 characters"))
	if not _on_control_plane():
		frappe.throw(
			_("Create your organization at {0}").format(f"https://{_public_base_host()}/start")
		)

	_rate_limit_signup(admin_email)

	existing = None
	if frappe.db.exists("DocType", "PL Tenant"):
		existing = frappe.db.get_value(
			"PL Tenant",
			{"admin_email": admin_email, "status": ("in", _OPEN_STATUSES)},
			["name", "site_name", "host", "status", "organization_name", "admin_full_name"],
			as_dict=True,
		)
	if existing:
		if existing.status in ("Approved", "Provisioning", "Active"):
			frappe.throw(_("An organization is already registered with this email."))
		# Pending: resend confirmation instead of creating a second org
		_cache_set_pwd(existing.site_name, password)
		token = _issue_confirm_token(existing.site_name)
		mail = _send_confirm_email(
			admin_email=admin_email,
			admin_full_name=admin_full_name or existing.admin_full_name,
			organization_name=existing.organization_name,
			host=existing.host,
			token=token,
		)
		return {
			"tenant": existing.name,
			"site_name": existing.site_name,
			"host": existing.host,
			"status": existing.status,
			"needs_confirm": True,
			"mail_queued": bool(mail.get("queued")),
			"message": _(
				"Check your email and open the confirmation link. "
				"After you confirm, we create your private URL."
			),
		}

	result = _insert_pending_tenant(
		organization_name=organization_name,
		site_name=site_name,
		admin_email=admin_email,
		admin_full_name=admin_full_name,
		notes=(
			f"Public signup {now_datetime()}. Waiting for email confirmation. "
			f'Provision after confirm: bash deploy/ec2/provision-tenant.sh '
			f'{{site}} "{organization_name}" {admin_email}'
		),
	)
	_cache_set_pwd(result["site_name"], password)
	frappe.db.set_value(
		"PL Tenant",
		result["site_name"],
		"notes",
		(
			f"Public signup {now_datetime()}. Admin: {admin_full_name} <{admin_email}>. "
			"Waiting for email confirmation before provisioning."
		),
	)
	frappe.db.commit()
	token = _issue_confirm_token(result["site_name"])
	mail = _send_confirm_email(
		admin_email=admin_email,
		admin_full_name=admin_full_name,
		organization_name=organization_name,
		host=result["host"],
		token=token,
	)
	result.update(
		{
			"needs_confirm": True,
			"mail_queued": bool(mail.get("queued")),
			"login_url": _login_url(result["host"]),
			"message": _(
				"Check your email and open the confirmation link. "
				"After you confirm, we create your private URL and sign you in."
			),
		}
	)
	if not mail.get("queued"):
		result["message"] = _(
			"We saved your organization but could not send the confirmation email. "
			"Wait a minute and try again, or contact support."
		)
	return result


def _login_url(host: str) -> str:
	host = _clean_host(host)
	return f"https://{host}/login"


def _product_name() -> str:
	name = (
		frappe.get_website_settings("app_name")
		or frappe.get_system_settings("app_name")
		or "Prime Ledger"
	)
	name = str(name).strip() or "Prime Ledger"
	return name


def _scrub_product_words(text: str) -> str:
	"""Customer-facing copy must never say Frappe / ERPNext."""
	brand = _product_name()
	out = str(text or "")
	out = re.sub(r"X-Frappe-Site", "X-Site", out, flags=re.I)
	out = re.sub(r"https?://(?:www\.)?frappe\.io\S*", "#", out, flags=re.I)
	out = re.sub(r"https?://(?:www\.)?erpnext\.com\S*", "#", out, flags=re.I)
	out = re.sub(r"ERP\s*Next", brand, out, flags=re.I)
	out = re.sub(r"\berpnext\b", brand, out, flags=re.I)
	out = re.sub(r"\bfrappe\b", brand, out, flags=re.I)
	return out


def _ensure_mail_brand() -> None:
	"""Turn off stock Frappe/ERPNext email footer (branding only; no user data)."""
	try:
		cur = frappe.db.get_single_value("System Settings", "disable_standard_email_footer")
		if cint(cur) != 1:
			frappe.db.set_single_value("System Settings", "disable_standard_email_footer", 1)
	except Exception:
		frappe.log_error(title="PL mail footer setting failed")


def _scrub_queued_mail(subject: str, recipients: list[str] | None = None) -> None:
	"""Rewrite latest Email Queue MIME so stock headers/footers cannot leak.

	tabEmail Queue has no subject column in this Frappe version — match recipient
	or MIME text instead.
	"""
	try:
		name = None
		recips = [str(r).strip() for r in (recipients or []) if r]
		if recips:
			rows = frappe.db.sql(
				"""
				select eq.name
				from `tabEmail Queue` eq
				inner join `tabEmail Queue Recipient` r on r.parent = eq.name
				where r.recipient = %s
				order by eq.creation desc
				limit 1
				""",
				(recips[0],),
			)
			if rows:
				name = rows[0][0]
		if not name and subject:
			rows = frappe.db.sql(
				"""
				select name from `tabEmail Queue`
				where message like %s
				order by creation desc
				limit 1
				""",
				(f"%{subject}%",),
			)
			if rows:
				name = rows[0][0]
		if not name:
			return
		row = frappe.db.get_value("Email Queue", name, ["message", "sender"], as_dict=True)
		if not row:
			return
		updates = {}
		message = row.get("message") or ""
		scrubbed_message = _scrub_product_words(message)
		if scrubbed_message != message:
			updates["message"] = scrubbed_message
		sender = row.get("sender") or ""
		if sender:
			scrubbed_sender = _scrub_product_words(sender)
			if scrubbed_sender != sender:
				updates["sender"] = scrubbed_sender
		if updates:
			frappe.db.set_value("Email Queue", name, updates, update_modified=False)
	except Exception:
		frappe.log_error(title="PL queued mail scrub failed")


def _branded_sender() -> str | None:
	brand = _product_name()
	email_id = None
	try:
		email_id = frappe.db.get_value("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}, "email_id")
	except Exception:
		email_id = None
	if not email_id:
		try:
			email_id = frappe.db.get_single_value("Email Account", "email_id")
		except Exception:
			email_id = None
	if email_id and "@" in str(email_id):
		return f"{brand} <{email_id}>"
	# Display name only — Frappe fills the address from Email Account
	return brand


def _sendmail_branded(*, recipients: list[str], subject: str, html: str, now: bool = False) -> None:
	_ensure_mail_brand()
	subject = _scrub_product_words(subject)
	html = _scrub_product_words(html)
	kwargs = dict(
		recipients=recipients,
		subject=subject,
		message=html,
		delayed=not now,
		now=now,
		sender=_branded_sender(),
		header=None,
		add_unsubscribe_link=0,
		with_container=False,
		expose_recipients="header",
	)
	# Keep with_container=False as long as possible; popping it re-enables the HTML wrapper.
	optional_keys = ("header", "expose_recipients", "add_unsubscribe_link", "with_container")
	while True:
		try:
			frappe.sendmail(**kwargs)
			break
		except TypeError:
			removed = False
			for key in optional_keys:
				if key in kwargs:
					kwargs.pop(key, None)
					removed = True
					break
			if not removed:
				raise
	_scrub_queued_mail(subject, recipients)


def _confirm_url(token: str) -> str:
	return f"https://{_public_base_host()}/confirm?token={token}"


def _send_confirm_email(
	*,
	admin_email: str,
	admin_full_name: str | None,
	organization_name: str,
	host: str,
	token: str,
) -> dict:
	name = (admin_full_name or admin_email.split("@")[0]).strip()
	org = organization_name or host
	brand = _product_name()
	url = _confirm_url(token)
	future = _login_url(host)
	subject = _("Confirm your {0} organization").format(brand)
	text = (
		f"Hi {name},\n\n"
		f"Confirm {org} to create your private workspace.\n"
		f"Your login URL will be:\n{future}\n\n"
		f"Open this link to confirm:\n{url}\n\n"
		"After you confirm, we prepare the workspace (a few minutes) and sign you in.\n\n"
		f"{brand}\n"
	)
	html = "<p>" + strip_html(text).replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
	try:
		# Send in this request. Scheduler flush skips mail younger than 10s and
		# is slow across multiple tenant sites, so delayed queue misses confirmations.
		_sendmail_branded(recipients=[admin_email], subject=subject, html=html, now=True)
		frappe.db.commit()
		return {"queued": True, "to": admin_email, "confirm_url": url}
	except Exception:
		frappe.log_error(title="PL signup confirmation email failed")
		return {"queued": False, "reason": "sendmail_failed", "to": admin_email}


@frappe.whitelist(allow_guest=True)
def confirm_signup(token: str):
	"""Guest: email confirmation starts provisioning of the private URL."""
	if not _on_control_plane():
		frappe.throw(_("Open the confirmation link from the email we sent."))
	site_name = _site_from_confirm_token((token or "").strip())
	if not site_name:
		frappe.throw(_("This confirmation link expired. Sign up again or request a new email."))
	row = frappe.db.get_value(
		"PL Tenant",
		site_name,
		["organization_name", "site_name", "host", "status"],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("This confirmation link expired. Sign up again."))
	approved = _approve_pending(site_name, actor="email-confirm", send_mail=False)
	poll_token = _issue_poll_token(site_name)
	host = approved.get("host") or row.host
	return {
		"ok": True,
		"site_name": site_name,
		"host": host,
		"login_url": _login_url(host),
		"status": approved.get("status") or row.status,
		"poll_token": poll_token,
		"ready": (approved.get("status") or row.status) == "Active",
		"message": _(
			"Email confirmed. We're creating your private URL. Keep this page open."
		),
	}


def _send_tenant_invite(
	*,
	ready: bool,
	organization_name: str,
	host: str,
	admin_email: str | None,
	admin_full_name: str | None = None,
) -> dict:
	"""Queue an invite email. Never fails the approve/provision action."""
	if not admin_email:
		return {"queued": False, "reason": "no_admin_email", "login_url": _login_url(host)}
	url = _login_url(host)
	name = (admin_full_name or admin_email.split("@")[0]).strip()
	org = organization_name or host
	brand = _product_name()
	if ready:
		subject = _("Your {0} workspace is ready").format(brand)
		text = (
			f"Hi {name},\n\n"
			f"{org} is ready. Sign in here:\n{url}\n\n"
			"Use the email and password you chose when you created the organization.\n\n"
			f"{brand}\n"
		)
	else:
		subject = _("Your organization was approved")
		text = (
			f"Hi {name},\n\n"
			f"We approved {org}. Your private login URL:\n{url}\n\n"
			"Sign in with the email and password you chose when you signed up. "
			"If the page is still preparing, wait a few minutes and try again.\n\n"
			f"{brand}\n"
		)
	html = "<p>" + strip_html(text).replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
	try:
		_sendmail_branded(recipients=[admin_email], subject=subject, html=html)
		frappe.db.commit()
		return {"queued": True, "login_url": url, "to": admin_email}
	except Exception:
		frappe.log_error(title="PL tenant invite email failed")
		return {"queued": False, "reason": "sendmail_failed", "login_url": url, "to": admin_email}


def _approve_pending(site_name: str, *, actor: str, send_mail: bool = True) -> dict:
	site_name = (site_name or "").strip().lower()
	if not site_name or not frappe.db.exists("PL Tenant", site_name):
		frappe.throw(_("Unknown organization"))

	row = frappe.db.get_value(
		"PL Tenant",
		site_name,
		["organization_name", "site_name", "host", "status", "admin_email", "admin_full_name", "notes"],
		as_dict=True,
	)
	if row.status == "Archived":
		frappe.throw(_("This organization is archived"))
	if row.status not in ("Pending", "Approved", "Error"):
		if row.status in ("Provisioning", "Active"):
			mail = _send_tenant_invite(
				ready=row.status == "Active",
				organization_name=row.organization_name,
				host=row.host,
				admin_email=row.admin_email,
				admin_full_name=row.admin_full_name,
			)
			return {
				"site_name": row.site_name,
				"host": row.host,
				"login_url": _login_url(row.host),
				"status": row.status,
				"email": mail,
				"already": True,
			}
		frappe.throw(_("Cannot approve from status {0}").format(row.status))

	host = row.host or f"{row.site_name}.{_public_base_host()}"
	note = (row.notes or "").strip()
	stamp = f"Approved {now_datetime()} by {actor}."
	frappe.db.set_value("PL Tenant", site_name, "host", host)
	frappe.db.set_value("PL Tenant", site_name, "status", "Approved")
	frappe.db.set_value("PL Tenant", site_name, "notes", f"{note}\n{stamp}".strip())
	frappe.db.commit()

	mail = {"queued": False, "skipped": True}
	if send_mail:
		mail = _send_tenant_invite(
			ready=False,
			organization_name=row.organization_name,
			host=host,
			admin_email=row.admin_email,
			admin_full_name=row.admin_full_name,
		)
	return {
		"site_name": site_name,
		"host": host,
		"login_url": _login_url(host),
		"status": "Approved",
		"email": mail,
		"provision_hint": (
			"Host cron auto-provision-approved.sh picks this up within a minute. "
			f"Manual fallback: bash deploy/ec2/provision-approved.sh {site_name}"
		),
	}


@frappe.whitelist()
def approve_tenant(site_name: str):
	"""Super Admin: approve a Pending org, confirm URL, send invite email.

	Does not create the Frappe site (that is provision-tenant.sh / provision-approved.sh).
	"""
	if not is_super_admin():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	return _approve_pending(site_name, actor=frappe.session.user)


def list_tenants_needing_provision():
	"""For bench execute / provision-approved.sh (not a guest API)."""
	if not frappe.db.exists("DocType", "PL Tenant"):
		return []
	return frappe.get_all(
		"PL Tenant",
		filters={"status": ("in", ("Approved", "Provisioning"))},
		fields=["name", "organization_name", "site_name", "host", "status", "admin_email"],
		order_by="creation asc",
	)


def print_provision_queue():
	"""Stdout marker for the provision-approved.sh parser."""
	import json as _json

	print("PL_PROVISION_JSON:" + _json.dumps(list_tenants_needing_provision()))


def list_routing_hosts():
	"""Hosts Traefik must terminate (apex is added by refresh-tenant-routing.sh)."""
	hosts: list[str] = []
	if not frappe.db.exists("DocType", "PL Tenant"):
		return hosts
	rows = frappe.get_all(
		"PL Tenant",
		filters={"status": ("in", ("Approved", "Provisioning", "Active"))},
		fields=["host", "site_name"],
	)
	base = _public_base_host()
	for r in rows:
		h = _clean_host(r.host or "") or _clean_host(f"{r.site_name}.{base}")
		if h:
			hosts.append(h)
	return sorted(set(hosts))


def print_routing_hosts():
	import json as _json

	print("PL_ROUTING_HOSTS:" + _json.dumps(list_routing_hosts()))


@frappe.whitelist()
def set_tenant_status(site_name: str, status: str, notes: str | None = None):
	if not is_super_admin():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if status not in _STATUSES:
		frappe.throw(_("Invalid status"))
	if not frappe.db.exists("PL Tenant", site_name):
		frappe.throw(_("Unknown tenant"))
	frappe.db.set_value("PL Tenant", site_name, "status", status)
	if notes is not None:
		frappe.db.set_value("PL Tenant", site_name, "notes", notes)
	frappe.db.commit()
	return {"site_name": site_name, "status": status}


def _note_reason(reason: str | None) -> str:
	text = strip_html(str(reason or "")).strip()
	return re.sub(r"\s+", " ", text)[:240]


@frappe.whitelist()
def reject_tenant(site_name: str, reason: str | None = None):
	"""Super Admin: reject a Pending or Error org. Reuses Archived (no new status)."""
	if not is_super_admin():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	site_name = (site_name or "").strip().lower()
	if not site_name or not frappe.db.exists("PL Tenant", site_name):
		frappe.throw(_("Unknown organization"))

	row = frappe.db.get_value("PL Tenant", site_name, ["site_name", "status", "notes"], as_dict=True)
	if row.status not in ("Pending", "Error"):
		frappe.throw(_("Cannot reject from status {0}").format(row.status))

	note = (row.notes or "").strip()
	extra = _note_reason(reason)
	stamp = f"{now_datetime()} [rejected] by {frappe.session.user}."
	if extra:
		stamp = f"{stamp} {extra}"
	frappe.db.set_value("PL Tenant", site_name, "status", "Archived")
	frappe.db.set_value("PL Tenant", site_name, "notes", f"{note}\n{stamp}".strip())
	frappe.db.commit()
	return {"site_name": site_name, "status": "Archived", "action": "rejected"}


@frappe.whitelist()
def block_tenant(site_name: str, reason: str | None = None):
	"""Super Admin: block an org. Sets Archived. Does not drop the tenant database.

	list_routing_hosts already excludes Archived, so the registry change is immediate.
	Traefik may still serve the URL until refresh-tenant-routing.sh runs.
	"""
	if not is_super_admin():
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	site_name = (site_name or "").strip().lower()
	if not site_name or not frappe.db.exists("PL Tenant", site_name):
		frappe.throw(_("Unknown organization"))

	row = frappe.db.get_value("PL Tenant", site_name, ["site_name", "status", "notes"], as_dict=True)
	if row.status not in ("Approved", "Provisioning", "Active", "Error"):
		frappe.throw(_("Cannot block from status {0}").format(row.status))

	note = (row.notes or "").strip()
	extra = _note_reason(reason)
	stamp = f"{now_datetime()} [blocked] by {frappe.session.user}."
	if extra:
		stamp = f"{stamp} {extra}"
	frappe.db.set_value("PL Tenant", site_name, "status", "Archived")
	frappe.db.set_value("PL Tenant", site_name, "notes", f"{note}\n{stamp}".strip())
	frappe.db.commit()
	return {
		"site_name": site_name,
		"status": "Archived",
		"action": "blocked",
		"routing_hint": "bash deploy/ec2/refresh-tenant-routing.sh",
	}


def mark_tenant_active_from_host(site_name: str, host: str, company: str | None = None):
	"""Called by provision-tenant.sh via bench execute (no web session)."""
	if not frappe.db.exists("DocType", "PL Tenant"):
		return {"ok": False, "error": "PL Tenant missing — migrate control site first"}
	if not frappe.db.exists("PL Tenant", site_name):
		frappe.get_doc(
			{
				"doctype": "PL Tenant",
				"organization_name": company or site_name,
				"site_name": site_name,
				"host": host,
				"status": "Active",
				"company": company or site_name,
			}
		).insert(ignore_permissions=True)
	else:
		frappe.db.set_value("PL Tenant", site_name, "status", "Active")
		frappe.db.set_value("PL Tenant", site_name, "host", host)
		if company:
			frappe.db.set_value("PL Tenant", site_name, "company", company)
			frappe.db.set_value("PL Tenant", site_name, "organization_name", company)
	frappe.db.commit()
	row = frappe.db.get_value(
		"PL Tenant",
		site_name,
		["organization_name", "host", "admin_email", "admin_full_name"],
		as_dict=True,
	)
	if row and row.admin_email:
		_send_tenant_invite(
			ready=True,
			organization_name=row.organization_name or company or site_name,
			host=row.host or host,
			admin_email=row.admin_email,
			admin_full_name=row.admin_full_name,
		)
	return {"ok": True, "site_name": site_name, "status": "Active"}


def ensure_org_company(org_name: str | None = None):
	"""Ensure at least one Company exists on the current (tenant) site."""
	from erpnext.portal_control.company_seed import ensure_org_company as _seed

	return _seed(org_name=org_name)


def peek_signup_password(site_name: str) -> str | None:
	"""Read signup password without deleting (consume after successful create)."""
	return _cache_get_pwd(site_name)


def consume_signup_password(site_name: str) -> str | None:
	"""Read-once password left by public signup (for provision script)."""
	pwd = _cache_get_pwd(site_name)
	_cache_del_pwd(site_name)
	return pwd


def create_tenant_admin_user(
	email: str,
	full_name: str | None = None,
	password: str | None = None,
	company: str | None = None,
):
	"""Create first System User on the *current* (tenant) site and bind to company."""
	email = (email or "").strip().lower()
	if not email:
		return {"ok": False, "error": "email required"}
	full_name = (full_name or email.split("@")[0]).strip()

	from erpnext.setup.user_onboarding import apply_role_profile
	from erpnext.portal_control.tenancy import bind_user_to_company
	from erpnext.setup.ensure_users import ADMIN_PROFILE, ADMIN_ROLES, ensure_admin_roles, run as ensure_users_run

	try:
		ensure_users_run()
	except Exception:
		frappe.log_error(title="pl_ensure_users_on_tenant_admin")

	password = (password or "").strip() or None
	exists = bool(frappe.db.exists("User", email))
	has_auth_pwd = False
	if exists:
		has_auth_pwd = bool(
			frappe.db.sql(
				"select 1 from `__Auth` where doctype=%s and name=%s and fieldname='password' limit 1",
				("User", email),
			)
		)
	if not password and (not exists or not has_auth_pwd):
		frappe.db.rollback()
		return {"ok": False, "error": "signup_password_MISSING"}

	if exists:
		user = frappe.get_doc("User", email)
	else:
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": full_name.split(" ", 1)[0],
				"last_name": full_name.split(" ", 1)[1] if " " in full_name else "",
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		)
		user.insert(ignore_permissions=True)

	apply_role_profile(email, ADMIN_PROFILE)
	try:
		ensure_admin_roles(email=email)
	except Exception:
		frappe.log_error(title="pl_ensure_admin_roles_on_tenant_admin")
	# Tenant admin role if present
	if frappe.db.exists("Role", "Prime Ledger Tenant Admin"):
		if "Prime Ledger Tenant Admin" not in frappe.get_roles(email):
			user = frappe.get_doc("User", email)
			user.append("roles", {"role": "Prime Ledger Tenant Admin"})
			user.save(ignore_permissions=True)

	if password:
		from frappe.utils.password import update_password

		update_password(email, password)

	if not company:
		companies = frappe.get_all("Company", pluck="name", limit=1)
		company = companies[0] if companies else None
	if company:
		bind_user_to_company(email, company)

	frappe.db.commit()
	return {"ok": True, "user": email, "company": company}


def _tenant_row_for_email(email: str) -> dict | None:
	email = (email or "").strip().lower()
	if not email or not frappe.db.exists("DocType", "PL Tenant"):
		return None
	rows = frappe.get_all(
		"PL Tenant",
		filters={"admin_email": email, "status": ("in", _OPEN_STATUSES)},
		fields=["name", "organization_name", "site_name", "host", "status", "admin_email"],
		order_by="creation desc",
		limit=8,
	)
	if not rows:
		return None
	active = [r for r in rows if r.status == "Active"]
	return active[0] if active else rows[0]


def _is_control_user(email: str) -> bool:
	email = (email or "").strip()
	if not email or not frappe.db.exists("User", email):
		return False
	if email == "Administrator":
		return True
	try:
		roles = set(frappe.get_roles(email))
	except Exception:
		return False
	return "Prime Ledger Super Admin" in roles


def _status_copy(status: str, host: str) -> str:
	url = _login_url(host)
	if status == "Active":
		return _("Your workspace is ready: {0}").format(url)
	if status == "Pending":
		return _("Confirm the email we sent. After that we create your private URL.")
	if status in ("Approved", "Provisioning"):
		return _(
			"Your private workspace is still being prepared. Bookmark {0} — "
			"we'll send you there as soon as it's ready."
		).format(url)
	if status == "Error":
		return _("Your workspace hit a setup error. Contact support with this URL: {0}").format(url)
	return _("Check your organization URL: {0}").format(url)


@frappe.whitelist(allow_guest=True)
def resolve_workspace(email: str):
	"""Guest: map a login email to that organization's private host (control plane only)."""
	email = (email or "").strip().lower()
	empty = {"found": False, "ready": False}
	if not email or not validate_email_address(email):
		return empty
	if not _on_control_plane():
		return empty
	if _is_control_user(email):
		return {"found": False, "ready": False, "control": True}
	row = _tenant_row_for_email(email)
	if not row:
		return empty
	host = row.host or f"{row.site_name}.{_public_base_host()}"
	ready = row.status == "Active"
	return {
		"found": True,
		"ready": ready,
		"status": row.status,
		"host": host,
		"site_name": row.site_name,
		"organization_name": row.organization_name,
		"login_url": _login_url(host),
		"message": _status_copy(row.status, host),
	}


@frappe.whitelist(allow_guest=True)
def signup_status(poll_token: str):
	"""Guest: poll provisioning for the signup that issued this token."""
	token = (poll_token or "").strip()
	site_name = _site_from_poll_token(token)
	if not site_name or not frappe.db.exists("PL Tenant", site_name):
		frappe.throw(_("This signup session expired. Sign in with your email."))
	row = frappe.db.get_value(
		"PL Tenant",
		site_name,
		["organization_name", "site_name", "host", "status"],
		as_dict=True,
	)
	host = row.host or f"{row.site_name}.{_public_base_host()}"
	return {
		"site_name": row.site_name,
		"organization_name": row.organization_name,
		"host": host,
		"status": row.status,
		"ready": row.status == "Active",
		"login_url": _login_url(host),
		"message": _status_copy(row.status, host),
	}


@frappe.whitelist(allow_guest=True)
def issue_login_ticket(poll_token: str):
	"""Guest: one-time ticket so signup can land signed-in on the tenant host."""
	token = (poll_token or "").strip()
	site_name = _site_from_poll_token(token)
	if not site_name or not frappe.db.exists("PL Tenant", site_name):
		frappe.throw(_("This signup session expired. Sign in with your email."))
	row = frappe.db.get_value(
		"PL Tenant",
		site_name,
		["site_name", "host", "status", "admin_email"],
		as_dict=True,
	)
	if row.status != "Active":
		frappe.throw(_("Your workspace is not ready yet. Keep this page open."))
	email = (row.admin_email or "").strip().lower()
	if not email:
		frappe.throw(_("No admin email on this organization. Sign in with your email."))
	ticket = secrets.token_urlsafe(32)
	_cache_set(
		_ticket_cache_key(ticket),
		{"email": email, "site_name": row.site_name},
		600,
	)
	host = row.host or f"{row.site_name}.{_public_base_host()}"
	return {
		"ticket": ticket,
		"host": host,
		"email": email,
		"login_url": f"https://{host}/go?ticket={ticket}",
	}


def _current_site_slug() -> str:
	site = str(frappe.local.site or "").strip().lower()
	if not site:
		return ""
	if "." in site:
		return site.split(".", 1)[0]
	return site


@frappe.whitelist(allow_guest=True)
def login_with_ticket(ticket: str):
	"""Guest: redeem a one-time ticket on the tenant site and start a session."""
	ticket = (ticket or "").strip()
	payload = _cache_get(_ticket_cache_key(ticket)) if ticket else None
	if not payload or not isinstance(payload, dict):
		frappe.throw(_("This sign-in link expired. Sign in with your email and password."))
	email = str(payload.get("email") or "").strip().lower()
	site_name = str(payload.get("site_name") or "").strip().lower()
	current = _current_site_slug()
	if not email or not site_name or site_name != current:
		frappe.throw(_("This sign-in link is for a different workspace."))
	if not frappe.db.exists("User", email):
		frappe.throw(_("Your user is still being created. Wait a few seconds and try again."))

	from frappe.auth import LoginManager

	frappe.local.login_manager = LoginManager()
	frappe.local.login_manager.login_as(email)
	_cache_del(_ticket_cache_key(ticket))
	landing = frappe.local.response.get("redirect_to") or "/portal"
	return {"ok": True, "user": email, "redirect_to": landing}
