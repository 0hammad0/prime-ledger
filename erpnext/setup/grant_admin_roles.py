"""Back-compat: bench execute erpnext.setup.grant_admin_roles.run"""


def run():
	from erpnext.setup.ensure_users import run as ensure_users_run

	return ensure_users_run()
