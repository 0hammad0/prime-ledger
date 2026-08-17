# Prime Ledger web (separate frontend)

Standalone app that talks to the existing Frappe/ERPNext APIs. It does **not** replace `/portal`.

## Run locally

```bash
cd web
yarn install
VITE_API_TARGET=https://sultan.65.1.92.180.sslip.io yarn dev
```

Opens on **http://localhost:5174**.

- Tenant APIs (`/api`, `/login`, `/start`) proxy to `VITE_API_TARGET` (default **sultan**).
- Organization signup proxies to `VITE_CONTROL_TARGET` (default apex `https://65.1.92.180.sslip.io`) via `/control`.

Sign in on the tenant host. Create organization still goes to the control plane (Pending — no User on the shared site).

FA books: `VITE_API_TARGET=https://fa.65.1.92.180.sslip.io yarn dev`.

## Auth through home

Login, forgot password, reset (`/reset?key=`), org signup, indigo shell, live AR/AP/cash KPIs, module lists, create/submit invoices, ePad (ToDo), duty calculator from live tax templates, named reports.

Empty KPIs are real zeros. **Load known sample data** writes Nexis Demo Customer / Supplier / `NEXIS-DEMO-SVC` plus two sales and two purchase invoices — only if you confirm, and only if that company has no sales invoices yet.

## Build

```bash
yarn build
```

New backend methods live in `erpnext/portal_control/dashboard.py`, `auth.py`, `workspace.py`, and `demo.py`. They must be hot-patched onto the tenant site before the dashboard KPIs work against live data.
