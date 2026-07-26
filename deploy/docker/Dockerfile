# Overlay Prime Ledger branding onto a stock ERPNext image.
# Full app-source builds are heavier; this image swaps logos/CSS for white-label.
#
# Build:
#   docker build -f deploy/docker/Dockerfile -t prime-ledger/erpnext:v16.29.0 .
#
# Then set in deploy/ec2/.env:
#   CUSTOM_IMAGE=prime-ledger/erpnext:v16.29.0
#   # or push to a registry and pull on EC2

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

RUN mkdir -p /home/frappe/frappe-bench/apps/erpnext/erpnext/public/css
COPY deploy/ec2/branding/prime_ledger_brand.css \
	/home/frappe/frappe-bench/apps/erpnext/erpnext/public/css/prime_ledger_brand.css

RUN printf '%s\n' \
	'{{ _("Powered by {0}").format('\''<a href="https://github.com/0hammad0/prime-ledger" target="_blank" class="text-muted">Prime Ledger</a>'\'') }}' \
	> /home/frappe/frappe-bench/apps/erpnext/erpnext/templates/includes/footer/footer_powered.html \
	&& chown -R frappe:frappe /home/frappe/frappe-bench/apps/erpnext/erpnext/public/images \
	&& chown -R frappe:frappe /home/frappe/frappe-bench/apps/erpnext/erpnext/public/css \
	&& chown frappe:frappe /home/frappe/frappe-bench/apps/erpnext/erpnext/templates/includes/footer/footer_powered.html

USER frappe
