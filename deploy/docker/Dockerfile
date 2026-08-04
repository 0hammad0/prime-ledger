# Overlay Prime Ledger branding + portal onto a stock Hub image.
#
# Build:
#   yarn build:portal
#   bash deploy/ec2/sync-portal-patches.sh
#   docker build -f deploy/docker/Dockerfile -t prime-ledger/erpnext:v16.29.0 .
#
# Then set in deploy/ec2/.env:
#   CUSTOM_IMAGE=prime-ledger/erpnext:v16.29.0

ARG ERPNEXT_VERSION=v16.29.0
FROM frappe/erpnext:${ERPNEXT_VERSION}

USER root

COPY deploy/ec2/branding/prime-ledger-logo.svg \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/public/images/prime-ledger-logo.svg
COPY deploy/ec2/branding/prime-ledger-favicon.svg \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/public/images/prime-ledger-favicon.svg
COPY deploy/ec2/branding/prime-ledger-logo.svg \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/public/images/erpnext-logo.svg
COPY deploy/ec2/branding/prime-ledger-favicon.svg \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/public/images/erpnext-favicon.svg

RUN mkdir -p /home/frappe/frappe-bench/apps/erpnext/erpnext/public/css \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/public/portal \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/portal_control \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/setup/doctype \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/patches/v16_0

COPY deploy/ec2/branding/prime_ledger_brand.css \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/public/css/prime_ledger_brand.css

COPY deploy/ec2/patches/portal/portal_control/ \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/portal_control/
COPY deploy/ec2/patches/portal/doctype/portal_module \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/setup/doctype/portal_module
COPY deploy/ec2/patches/portal/doctype/portal_module_role \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/setup/doctype/portal_module_role
COPY deploy/ec2/patches/portal/doctype/portal_settings \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/setup/doctype/portal_settings
COPY deploy/ec2/patches/portal/www/portal.py \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/www/portal.py
COPY deploy/ec2/patches/portal/www/portal.html \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/www/portal.html
COPY deploy/ec2/patches/portal/public/ \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/public/portal/
COPY deploy/ec2/patches/portal/patches/seed_portal_control.py \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/patches/v16_0/seed_portal_control.py
COPY deploy/docker/inject_portal_hooks.py /tmp/inject_portal_hooks.py

RUN printf '%s\n' \
	'{{ _("Powered by {0}").format('\''<a href="https://github.com/0hammad0/prime-ledger" target="_blank" class="text-muted">Prime Ledger</a>'\'') }}' \
	> /home/frappe/frappe-bench/apps/erpnext/erpnext/templates/includes/footer/footer_powered.html \
	&& python3 /tmp/inject_portal_hooks.py \
	&& rm -f /tmp/inject_portal_hooks.py \
	&& chown -R frappe:frappe /home/frappe/frappe-bench/apps/erpnext/erpnext/public \
	&& chown -R frappe:frappe /home/frappe/frappe-bench/apps/erpnext/erpnext/portal_control \
	&& chown -R frappe:frappe /home/frappe/frappe-bench/apps/erpnext/erpnext/setup/doctype/portal_module \
	&& chown -R frappe:frappe /home/frappe/frappe-bench/apps/erpnext/erpnext/setup/doctype/portal_module_role \
	&& chown -R frappe:frappe /home/frappe/frappe-bench/apps/erpnext/erpnext/setup/doctype/portal_settings \
	&& chown frappe:frappe /home/frappe/frappe-bench/apps/erpnext/erpnext/www/portal.py \
	&& chown frappe:frappe /home/frappe/frappe-bench/apps/erpnext/erpnext/www/portal.html \
	&& chown frappe:frappe /home/frappe/frappe-bench/apps/erpnext/erpnext/patches/v16_0/seed_portal_control.py \
	&& chown frappe:frappe /home/frappe/frappe-bench/apps/erpnext/erpnext/templates/includes/footer/footer_powered.html

USER frappe
