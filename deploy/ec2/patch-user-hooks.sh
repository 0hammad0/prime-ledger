#!/usr/bin/env bash
# Hot-patch Hub erpnext hooks + user_onboarding so new System Users get Role Profiles.
# Uses `bench restart` (not docker recreate) so the patched hooks.py stays on disk.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
SITE_NAME="${SITE_NAME:-frontend}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
fi
SITE_NAME="${SITE_NAME:-frontend}"

if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
  DC=(docker compose)
elif sudo docker info >/dev/null 2>&1; then
  DOCKER=(sudo docker)
  DC=(sudo docker compose)
else
  echo "Docker not available" >&2
  exit 1
fi

BACKEND_CID="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q backend | head -n1)"
[[ -n "$BACKEND_CID" ]] || { echo "backend not running"; exit 1; }

SETUP_ROOT="/home/frappe/frappe-bench/apps/erpnext/erpnext/setup"

cat > /tmp/pl_patch_hooks.py <<'PY'
from pathlib import Path
p = Path("/home/frappe/frappe-bench/apps/erpnext/erpnext/hooks.py")
text = p.read_text()
marker = "erpnext.setup.user_onboarding.on_user_after_insert"
if marker in text:
    print("hooks_already_patched")
    raise SystemExit(0)

needle = '"after_insert": "frappe.contacts.doctype.contact.contact.update_contact",'
if needle not in text:
    needle = "'after_insert': 'frappe.contacts.doctype.contact.contact.update_contact',"
if needle not in text:
    raise SystemExit("hooks_needle_not_found")

replacement = (
    '"after_insert": [\n'
    '\t\t\t"frappe.contacts.doctype.contact.contact.update_contact",\n'
    f'\t\t\t"{marker}",\n'
    "\t\t],"
)
user_idx = text.find('"User"')
if user_idx < 0:
    user_idx = text.find("'User'")
if user_idx < 0:
    raise SystemExit("hooks_user_block_missing")

before, after = text[:user_idx], text[user_idx:]
if needle not in after:
    raise SystemExit("hooks_needle_not_in_user_block")
after = after.replace(needle, replacement, 1)
p.write_text(before + after)
print("hooks_patched")
PY

for svc in backend queue-short queue-long scheduler websocket; do
  cid="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q "$svc" 2>/dev/null | head -n1 || true)"
  [[ -n "${cid:-}" ]] || continue
  for f in user_onboarding.py ensure_users.py grant_admin_roles.py; do
    [[ -f "$SCRIPT_DIR/patches/$f" ]] || continue
    "${DOCKER[@]}" cp "$SCRIPT_DIR/patches/$f" "${cid}:${SETUP_ROOT}/$f" || true
  done
  "${DOCKER[@]}" cp /tmp/pl_patch_hooks.py "${cid}:/tmp/pl_patch_hooks.py" || true
  "${DOCKER[@]}" exec -u root "$cid" python3 /tmp/pl_patch_hooks.py || true
done

"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" set-config server_script_enabled 1 || true
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench set-config -g server_script_enabled 1 || true

# Reload python processes without wiping the container filesystem
echo "==> bench restart (keeps patched hooks.py)"
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench restart || true
sleep 5

"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$SITE_NAME" clear-cache || true

# Ensure frontend still points at backend
"${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --no-deps frontend || true

echo "User hooks patched."
