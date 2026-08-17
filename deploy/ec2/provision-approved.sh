#!/usr/bin/env bash
# Provision tenants that Super Admin approved in the Organizations panel.
# Usage:
#   bash provision-approved.sh           # all Approved/Provisioning
#   bash provision-approved.sh <slug>    # one site
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${ENV_FILE:-$SCRIPT_DIR/.env}"
PROJECT_NAME="${PROJECT_NAME:-prime-ledger}"
COMPOSE_FILE="${COMPOSE_FILE:-$HOME/gitops/prime-ledger-compose.yml}"
CONTROL_SITE="${CONTROL_SITE:-${SITE_NAME:-frontend}}"
ONLY_SLUG="${1:-}"

# shellcheck disable=SC1090
set -a
source "$ENV_FILE"
set +a

if docker info >/dev/null 2>&1; then
  DC=(docker compose)
elif sudo docker info >/dev/null 2>&1; then
  DC=(sudo docker compose)
else
  echo "Docker not available" >&2
  exit 1
fi

RAW="$("${DC[@]}" --project-name "$PROJECT_NAME" -f "$COMPOSE_FILE" exec -T backend \
  bench --site "$CONTROL_SITE" execute erpnext.portal_control.tenants.print_provision_queue 2>/dev/null || true)"
JSON_LINE="$(printf '%s\n' "$RAW" | grep 'PL_PROVISION_JSON:' | tail -n1 || true)"
JSON_LINE="${JSON_LINE#PL_PROVISION_JSON:}"

if [[ -z "$JSON_LINE" ]]; then
  echo "No Approved/Provisioning tenants (or print_provision_queue not patched yet)."
  exit 0
fi

python3 - "$JSON_LINE" "$ONLY_SLUG" "$SCRIPT_DIR" <<'PY'
import json, os, subprocess, sys

raw, only, script_dir = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    rows = json.loads(raw)
except json.JSONDecodeError:
    print("Could not parse provision queue", file=sys.stderr)
    sys.exit(1)
if not isinstance(rows, list):
    rows = []
if only:
    rows = [r for r in rows if (r.get("site_name") or r.get("name")) == only]
allow_test = os.environ.get("PROVISION_TEST_TENANTS", "") == "1"
skip_prefixes = ("smoke-test", "acme-test", "owner-probe", "ownerprobe")
if not allow_test:
    kept = []
    for r in rows:
        slug = r.get("site_name") or r.get("name") or ""
        if slug.startswith(skip_prefixes) or slug == "smoke-test-org":
            print("skip test tenant", slug)
            continue
        kept.append(r)
    rows = kept
if not rows:
    print("Nothing to provision.")
    sys.exit(0)
for r in rows:
    slug = r.get("site_name") or r.get("name")
    org = r.get("organization_name") or slug
    email = r.get("admin_email") or ""
    cmd = ["bash", os.path.join(script_dir, "provision-tenant.sh"), slug, org]
    if email:
        cmd.append(email)
    print("==> provisioning", slug, org, email)
    subprocess.check_call(cmd)
PY
