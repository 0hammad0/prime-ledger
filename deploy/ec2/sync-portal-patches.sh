#!/usr/bin/env bash
# Copy portal app sources + built SPA into deploy/ec2/patches/portal for Hub hot-patch.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEST="$ROOT/deploy/ec2/patches/portal"

if [[ ! -f "$ROOT/erpnext/www/portal.html" ]]; then
  echo "Missing erpnext/www/portal.html — run: yarn build:portal" >&2
  exit 1
fi

rm -rf "$DEST"
mkdir -p "$DEST/portal_control" \
  "$DEST/doctype" \
  "$DEST/www" \
  "$DEST/public" \
  "$DEST/patches"

cp -R "$ROOT/erpnext/portal_control/." "$DEST/portal_control/"
cp -R "$ROOT/erpnext/setup/doctype/portal_module" "$DEST/doctype/"
cp -R "$ROOT/erpnext/setup/doctype/portal_module_role" "$DEST/doctype/"
cp -R "$ROOT/erpnext/setup/doctype/pl_portal_settings" "$DEST/doctype/"
cp -R "$ROOT/erpnext/setup/doctype/pl_tenant" "$DEST/doctype/"
cp "$ROOT/erpnext/www/portal.py" "$DEST/www/"
cp "$ROOT/erpnext/www/portal.html" "$DEST/www/"
cp "$ROOT/erpnext/www/start.py" "$DEST/www/"
cp "$ROOT/erpnext/www/start.html" "$DEST/www/"
cp -R "$ROOT/erpnext/public/portal/." "$DEST/public/"
cp "$ROOT/erpnext/patches/v16_0/seed_portal_control.py" "$DEST/patches/"
cp "$ROOT/erpnext/patches/v16_0/restore_frappe_portal_settings.py" "$DEST/patches/"
cp "$ROOT/erpnext/patches/v16_0/seed_pl_tenant.py" "$DEST/patches/"
cp "$ROOT/erpnext/startup/boot.py" "$DEST/boot.py"
cp "$ROOT/erpnext/setup/user_onboarding.py" "$ROOT/deploy/ec2/patches/user_onboarding.py"
cp "$ROOT/erpnext/public/js/setup_wizard.js" "$ROOT/deploy/ec2/patches/setup-wizard/setup_wizard.js"

echo "synced portal → deploy/ec2/patches/portal"
echo "Commit deploy/ec2/patches/portal so CI can hot-patch Hub images."
