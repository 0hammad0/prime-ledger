# Prime Ledger Portal (Phase 1)

Tenant + Super Admin shell on top of the ERP engine. Backend DocTypes and APIs live in `erpnext/`; the React app lives here.

## Develop

```sh
# from repo root (bench site on :8000)
yarn install
yarn dev:portal
```

Open http://localhost:8081/portal (proxied API to :8000).

## Build

```sh
yarn build:portal
```

Outputs:

- `erpnext/public/portal/`
- `erpnext/www/portal.html`

## Production URL

`/portal` — login required.

- Tenant: `/portal/tenant`
- Super Admin: `/portal/admin`
- Master Controls: `/portal/admin/modules`

Requires migrate so `Portal Module` and `PL Portal Settings` exist (this fork / custom image).
