#!/usr/bin/env bash
# Keep Hub hot-patches aligned with erpnext app source (local is source of truth).
# Run from repo root or deploy/ec2: ./sync-app-patches.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
APP_SETUP="$REPO_ROOT/erpnext/setup"
PATCH_DIR="$SCRIPT_DIR/patches"

copy() {
  local src="$1" dest="$2"
  if [[ ! -f "$src" ]]; then
    echo "skip missing $src"
    return 0
  fi
  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
  echo "synced $(basename "$src") → ${dest#"$REPO_ROOT"/}"
}

copy "$APP_SETUP/ensure_users.py" "$PATCH_DIR/ensure_users.py"
copy "$APP_SETUP/user_onboarding.py" "$PATCH_DIR/user_onboarding.py"
copy "$APP_SETUP/grant_admin_roles.py" "$PATCH_DIR/grant_admin_roles.py"
copy "$APP_SETUP/setup_wizard/setup_wizard.py" "$PATCH_DIR/setup-wizard/setup_wizard.py"

# Optional: setup wizard JS / fixtures if present under patches already as Hub copies
if [[ -f "$REPO_ROOT/erpnext/public/js/setup_wizard.js" ]]; then
  copy "$REPO_ROOT/erpnext/public/js/setup_wizard.js" "$PATCH_DIR/setup-wizard/setup_wizard.js"
fi
if [[ -f "$REPO_ROOT/erpnext/setup/setup_wizard/operations/install_fixtures.py" ]]; then
  copy "$REPO_ROOT/erpnext/setup/setup_wizard/operations/install_fixtures.py" \
    "$PATCH_DIR/setup-wizard/install_fixtures.py"
fi
if [[ -f "$REPO_ROOT/erpnext/setup/demo.py" ]]; then
  copy "$REPO_ROOT/erpnext/setup/demo.py" "$PATCH_DIR/setup-wizard/demo.py"
fi

echo "App → deploy patches sync complete."
echo "Push to main (or rsync deploy/ec2/) to update live."
