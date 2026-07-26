# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.geo.country_info import get_country_info
from frappe.utils.telemetry import capture

from erpnext.setup.demo import setup_demo_data
from erpnext.setup.setup_wizard.operations import install_fixtures as fixtures


def normalize_setup_args(args):  # nosemgrep
	"""Fill required setup keys when Frappe's first wizard slide values are missing.

	Mutates ``args`` in place so later stages see the same values.
	"""
	if args is None:
		return frappe._dict()

	if not isinstance(args, dict):
		args = frappe._dict(args)

	# Country
	if not args.get("country"):
		args["country"] = (
			frappe.db.get_default("country")
			or frappe.db.get_single_value("System Settings", "country")
			or (frappe.db.exists("Country", "United States") and "United States")
			or frappe.db.get_value("Country", {}, "name", order_by="name asc")
			or "United States"
		)

	country_info = {}
	try:
		country_info = get_country_info(args.get("country")) or {}
	except Exception:
		country_info = {}

	# Currency
	if not args.get("currency"):
		args["currency"] = (
			country_info.get("currency")
			or frappe.db.get_default("currency")
			or frappe.db.get_single_value("Global Defaults", "default_currency")
			or "USD"
		)

	# Ensure currency doc exists / is enabled later; keep a safe ISO code
	if not frappe.db.exists("Currency", args["currency"]):
		args["currency"] = "USD" if frappe.db.exists("Currency", "USD") else args["currency"]

	# Language / timezone (used by Frappe stages / telemetry)
	if not args.get("language"):
		args["language"] = frappe.db.get_single_value("System Settings", "language") or "English"
	if not args.get("timezone"):
		timezones = country_info.get("timezones") or []
		args["timezone"] = (
			(timezones[0] if timezones else None)
			or frappe.db.get_single_value("System Settings", "time_zone")
			or "Asia/Kolkata"
		)

	# Ensure locale helpers work during fixture inserts (frappe#39289)
	lang_code = "en"
	language_name = args.get("language")
	if language_name and frappe.db.exists("Language", language_name):
		lang_code = language_name
	elif language_name:
		lang_code = frappe.db.get_value("Language", {"language_name": language_name}, "name") or "en"
	frappe.local.lang = lang_code
	try:
		frappe.db.set_default("language", lang_code)
	except Exception:
		pass

	# Chart of accounts — company create fails if this is blank on some paths
	if not args.get("chart_of_accounts"):
		args["chart_of_accounts"] = "Standard"

	# Domain is optional on Company; keep empty string rather than None
	if args.get("domain") is None:
		args["domain"] = ""

	# Company name guard used by later stages
	if not args.get("company_name"):
		frappe.throw(_("Company Name is required to complete setup"))

	if not args.get("company_abbr"):
		name = args.get("company_name") or "Company"
		args["company_abbr"] = "".join(part[:1] for part in name.split() if part)[:10].upper() or "CO"

	return args


def get_setup_stages(args=None):  # nosemgrep
	normalize_setup_args(args)

	stages = [
		{
			"status": _("Installing presets"),
			"fail_msg": _("Failed to install presets"),
			"tasks": [{"fn": stage_fixtures, "args": args, "fail_msg": _("Failed to install presets")}],
		},
		{
			"status": _("Setting up company"),
			"fail_msg": _("Failed to setup company"),
			"tasks": [{"fn": setup_company, "args": args, "fail_msg": _("Failed to setup company")}],
		},
		{
			"status": _("Setting defaults"),
			"fail_msg": _("Failed to set defaults"),
			"tasks": [
				{"fn": setup_defaults, "args": args, "fail_msg": _("Failed to setup defaults")},
			],
		},
		{
			"status": _("Personalizing your setup"),
			"fail_msg": _("Failed to personalize your setup"),
			"tasks": [
				{"fn": capture_user_persona, "args": args, "fail_msg": _("Failed to personalize your setup")}
			],
		},
	]

	if args.get("setup_demo"):
		stages.append(
			{
				"status": _("Creating demo data"),
				"fail_msg": _("Failed to create demo data"),
				"tasks": [{"fn": setup_demo, "args": args, "fail_msg": _("Failed to create demo data")}],
			}
		)

	return stages


def capture_user_persona(args):  # nosemgrep
	"""Send the persona answers captured on the setup slide to telemetry."""
	if not args:
		return

	capture(
		"user_persona_submitted",
		"erpnext",
		properties={
			"implementing_for": args.get("persona_implementing_for"),
			"company_size": args.get("persona_company_size"),
			"industry": args.get("persona_industry"),
			"current_system": args.get("persona_current_system"),
			"module_accounting": bool(args.get("module_accounting")),
			"module_stock": bool(args.get("module_stock")),
			"module_manufacturing": bool(args.get("module_manufacturing")),
			"module_projects": bool(args.get("module_projects")),
			"country": args.get("country"),
			"language": args.get("language"),
		},
	)


def stage_fixtures(args):  # nosemgrep
	normalize_setup_args(args)
	fixtures.install(args.get("country"))


def setup_company(args):  # nosemgrep
	normalize_setup_args(args)
	fixtures.install_company(args)


def setup_defaults(args):  # nosemgrep
	normalize_setup_args(args)
	fixtures.install_defaults(frappe._dict(args))


def setup_demo(args):  # nosemgrep
	normalize_setup_args(args)
	setup_demo_data(args.get("company_name"))


# Only for programmatical use
def setup_complete(args=None):  # nosemgrep
	normalize_setup_args(args)
	stage_fixtures(args)
	setup_company(args)
	setup_defaults(args)
