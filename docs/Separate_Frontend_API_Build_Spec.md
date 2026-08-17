# Prime Ledger — Separate Frontend API & Build Spec

**Purpose:** Source of truth for a **new standalone frontend** (CRM / product UI) that talks to the existing Frappe / ERPNext / Prime Ledger backend via APIs.  
**Constraint:** Do **not** replace or break the current portal (`/portal`) or Desk. This frontend is additive.

**Status:** Spec plus a working app in `web/` (Vite/React, port 5174). `/portal` is untouched.

**Live backend (today):** `https://65.1.92.180.sslip.io`  
**Control site:** `frontend`  
**Auth model:** Cookie session (`sid`) + CSRF token (same as Frappe web).

---

## 1. What we are building

```
[ New Frontend App ]  ──HTTPS JSON──►  [ Existing Frappe/ERPNext APIs ]
        │                                        │
        │  login / signup / CRM / stock / $      │
        ▼                                        ▼
   only the screens you need              current /portal + Desk stay as-is
```

| Keep as-is | New work |
|---|---|
| `/portal` SPA | Separate FE repo or `apps/web-crm/` (your choice later) |
| Desk `/app/*` | Consumes `/api/method/*` + `/api/resource/*` |
| Hot-patches / brand | CORS + cookie domain if FE is on another origin |

---

## 2. Architecture rules (aligned with tenancy)

1. **Organization (tenant)** = hard boundary (ideally one site per org).  
2. **Business (Company)** = books inside a tenant (multiple companies allowed later, QBO-style).  
3. **User** belongs to one tenant; tenant admin invites more users.  
4. Public **Create organization** ≠ shared-site desk signup.  
5. New frontend must never assume “everyone shares one org.”

```
Signup /start     → Pending PL Tenant (not a shared desk user)
Provision site    → private tenant host
Login             → that tenant’s API host
Admin adds users  → User create on *that* site only
```

---

## 3. Connection basics (every request)

### 3.1 Base URL

- Same-origin (recommended while prototyping): FE proxied to backend host.  
- Cross-origin later: set CORS + `SameSite` cookies; use `credentials: "include"`.

### 3.2 Session

| Step | How |
|---|---|
| Login | `POST /` or `POST /api/method/login` with `usr`, `pwd` |
| Cookies | Browser stores `sid`, `system_user`, `user_id`, … |
| CSRF | After login, read CSRF from bootstrap or `frappe.sessions.get_csrf_token` pattern; send `X-Frappe-CSRF-Token` on mutating calls |
| Logged-in check | `GET /api/method/frappe.auth.get_logged_user` |
| Logout | `GET /api/method/logout` or `POST` logout |

### 3.3 Standard response shape

```json
{ "message": { /* payload */ } }
```

Errors:

```json
{ "exc_type": "PermissionError", "exception": "...", "_error_message": "..." }
```

### 3.4 Headers checklist

```
Accept: application/json
Content-Type: application/x-www-form-urlencoded   # or application/json where supported
X-Frappe-CSRF-Token: <token>
Cookie: sid=...   # via credentials: include
X-Requested-With: XMLHttpRequest   # useful for login
```

---

## 4. End-to-end flow map

```
[Landing]
   │
   ├─► Create organization ──► signup_organization ──► Pending tenant
   │                              (ops: provision-tenant.sh)
   │                              └─► tenant host Active
   │
   └─► Sign in ──► login ──► get_portal_boot ──► home
                      │
                      ├─► Products / Items
                      ├─► Customers / CRM
                      ├─► Sales (SO / Invoice)
                      ├─► Purchases
                      ├─► Stock / Batch
                      ├─► Money / Accounts
                      ├─► Reports
                      ├─► Settings / Company
                      └─► (Super Admin) Organizations / Modules / Users
```

---

## 5. Auth & session APIs

| # | Action | Method | Endpoint | Auth | Body / params | Returns (message) |
|---|---|---|---|---|---|---|
| A1 | Login | `POST` | `/` or `/api/method/login` | Guest | `usr`, `pwd` (`cmd=login` if posting to `/`) | `Logged In`, `redirect_to`, `full_name`, `home_page` |
| A2 | Who am I | `GET` | `/api/method/frappe.auth.get_logged_user` | Session | — | email / user name |
| A3 | Logout | `GET`/`POST` | `/api/method/logout` | Session | — | ok |
| A4 | Forgot password | stock Frappe | `/api/method/frappe.core.doctype.user.user.reset_password` | Guest | `user` | depends on email config |
| A5 | Portal boot | `GET` | `/api/method/erpnext.portal_control.api.get_portal_boot` | Session | — | user, roles, modules, companies, tenants?, settings |

**Login notes (verified live):**

- Prefer `redirect_to` from login JSON (portal). `home_page` may still say `desk`.  
- After login, call **A5** before rendering the app shell.

**Example login**

```http
POST /api/method/login
Content-Type: application/x-www-form-urlencoded

usr=admin@primeledger.local&pwd=***
```

---

## 6. Organization (tenant) APIs — Prime Ledger custom

| # | Action | Method | Endpoint | Auth | Body | Returns |
|---|---|---|---|---|---|---|
| T1 | Public org signup | `POST` | `/api/method/erpnext.portal_control.tenants.signup_organization` | **Guest** + CSRF | `organization_name`, `admin_full_name`, `admin_email`, `password`, optional `site_name` | `site_name`, `host`, `status=Pending`, message |
| T2 | List tenants | `GET`/`POST` | `/api/method/erpnext.portal_control.tenants.list_tenants` | Super Admin | — | list of PL Tenant |
| T3 | Register tenant (admin) | `POST` | `/api/method/erpnext.portal_control.tenants.register_tenant` | Super Admin | `organization_name`, optional `site_name`, `admin_email`, `company`, `host` | Pending row + provision hint |
| T4 | Set tenant status | `POST` | `/api/method/erpnext.portal_control.tenants.set_tenant_status` | Super Admin | `site_name`, `status`, optional `notes` | ok |
| T5 | Provision (ops, not HTTP) | shell | `deploy/ec2/provision-tenant.sh <slug> "Org Name" [admin-email]` | Server | — | new site + Active |

**Public page (existing):** `GET /start` — Create organization form (keep or re-skin in new FE).

**Statuses:** `Pending` → `Provisioning` → `Active` | `Error` | `Archived`

---

## 7. Portal / product shell APIs — Prime Ledger custom

| # | Action | Method | Endpoint | Auth | Notes |
|---|---|---|---|---|---|
| P1 | Boot payload | `GET` | `erpnext.portal_control.api.get_portal_boot` | User | Modules, companies (filtered), tenants (super), settings |
| P2 | Toggle module | `POST` | `erpnext.portal_control.api.set_module_enabled` | Super Admin | `module_key`, `enabled` |
| P3 | Save portal settings | `POST` | `erpnext.portal_control.api.save_portal_settings` | Super Admin | `enable_portal_home`, `portal_title` |
| P4 | Bind user→company | `POST` | `erpnext.portal_control.tenancy.bind_user_company` | Super Admin | `user`, `company` |
| P5 | List company bindings | `GET`/`POST` | `erpnext.portal_control.tenancy.list_company_bindings` | Super Admin | overview |

### 7.1 `get_portal_boot` message shape (contract)

```ts
{
  app_name: string
  user: { name, full_name, email, user_image? }
  is_super_admin: boolean
  roles: string[]
  settings: {
    enable_portal_home: number
    default_tenant_landing: string
    default_super_admin_landing: string
    support_email?: string
  }
  modules: PortalModule[]       // visible to this user
  all_modules: PortalModule[]   // super admin catalog
  companies: { name, abbr?, default_currency?, country? }[]
  tenants?: {                   // super admin only
    name, organization_name, site_name, host?, status,
    company?, admin_email?, admin_full_name?, creation?, notes?
  }[]
}
```

### 7.2 Seeded modules (menu → backend DocType)

Use this table when wiring the new FE nav. `desk_route` is the ERPNext DocType/page the module opens today.

| module_key | Label | Audience | Typical resource / screen |
|---|---|---|---|
| `dashboard` | Home | Tenant | app home / KPIs (compose from list APIs) |
| `products` | Products | Tenant | **Item** |
| `inventory` | Stock | Tenant | Stock Balance / Stock Entry / Bin |
| `batch_expiry` | Batch & Expiry | Tenant | **Batch** |
| `purchases` | Purchases | Tenant | **Purchase Order**, Purchase Invoice, Supplier |
| `sales` | Sales | Tenant | **Sales Order**, Sales Invoice, Customer |
| `quality` | Quality checks | Tenant | **Quality Inspection** |
| `finance` | Money | Tenant | **Account**, Payment Entry, GL |
| `reports` | Reports | Tenant | Query Report / `frappe.desk.query_report.run` |
| `settings` | Settings | Tenant | **Company**, User defaults |
| `admin_home` | Site admin | Super | control home |
| `master_controls` | What teams can see | Super | Portal Module toggles (P2) |
| `tenants` | Organizations | Super | PL Tenant (T2–T4) |
| `users` | People | Super / Admin | **User** |

---

## 8. Generic Frappe resource API (CRM building blocks)

These are the **standard** backend APIs the new frontend should use for almost all business objects. Prefix: `/api/resource/<DocType>`.

| # | Action | Method | Path | Notes |
|---|---|---|---|---|
| R1 | List | `GET` | `/api/resource/{DocType}?fields=[...]&filters=[...]&limit_page_length=20&order_by=modified desc` | Respects permissions + company User Permission |
| R2 | Get one | `GET` | `/api/resource/{DocType}/{name}` | Encoded name |
| R3 | Create | `POST` | `/api/resource/{DocType}` | JSON body = fields |
| R4 | Update | `PUT` | `/api/resource/{DocType}/{name}` | JSON body |
| R5 | Delete | `DELETE` | `/api/resource/{DocType}/{name}` | Permission required |

**Alternate method API (same power):**

| # | Action | Endpoint |
|---|---|---|
| R6 | List | `frappe.client.get_list` |
| R7 | Get | `frappe.client.get` |
| R8 | Insert | `frappe.client.insert` |
| R9 | Set value | `frappe.client.set_value` |
| R10 | Delete | `frappe.client.delete` |
| R11 | Count | `frappe.client.get_count` |

### 8.1 Core DocTypes for a CRM-style product

Map your product screens to these. Expand when you share the feature list.

| Domain | DocType | Common fields to start |
|---|---|---|
| Party | `Customer` | customer_name, customer_type, territory, customer_group, default_currency |
| Party | `Lead` | lead_name, email_id, status, source, company |
| Party | `Opportunity` | opportunity_from, party_name, status, opportunity_amount |
| Party | `Contact` | first_name, email_id, links |
| Party | `Address` | address_line1, city, country, links |
| Selling | `Quotation` | party_name, transaction_date, items, company, currency |
| Selling | `Sales Order` | customer, delivery_date, items, company |
| Selling | `Sales Invoice` | customer, posting_date, items, company, outstanding_amount |
| Buying | `Supplier` | supplier_name, supplier_group |
| Buying | `Purchase Order` | supplier, schedule_date, items, company |
| Buying | `Purchase Invoice` | supplier, posting_date, items, company |
| Stock | `Item` | item_code, item_name, stock_uom, is_stock_item, item_group |
| Stock | `Warehouse` | warehouse_name, company |
| Stock | `Stock Entry` | stock_entry_type, items, company |
| Stock | `Batch` | batch_id, item, expiry_date |
| Accounting | `Payment Entry` | payment_type, party, paid_amount, company |
| Accounting | `Account` | account_name, parent_account, company |
| Org | `Company` | company_name, abbr, default_currency, country |
| People | `User` | email, first_name, roles / role_profile_name, enabled |

**Always send `company` on transactional docs** when the user is company-locked.

### 8.2 Submit / cancel / amend (documents with workflow)

Many ERPNext docs are Submittable:

| Action | Typical method |
|---|---|
| Submit | `frappe.client.submit` → `{ doc: { doctype, name, ... } }` |
| Cancel | `frappe.client.cancel` |
| Get meta (fields, permissions) | `frappe.desk.form.load.getdoctype` / `frappe.client.get` meta via `frappe.get_meta` wrappers |

Exact signatures can be confirmed in Network tab of Desk while building each screen.

### 8.3 Reports

| Action | Endpoint | Params |
|---|---|---|
| Run report | `/api/method/frappe.desk.query_report.run` | `report_name`, `filters` (JSON) |
| List reports | resource `Report` or boot / workspace | filter `ref_doctype` |

---

## 9. Users under a tenant (invite flow)

**Target UX:** Tenant admin adds users; they only exist on that org’s site.

| # | Action | How (today) | FE notes |
|---|---|---|---|
| U1 | Create user | `POST /api/resource/User` | Set email, name; `send_welcome_email` as needed |
| U2 | Assign roles | User.roles / Role Profile | Prefer `Prime Ledger User` or Admin profile |
| U3 | Bind company | `bind_user_company` (P4) or User Permission | Required for data isolation |
| U4 | Disable user | `PUT` User `enabled: 0` | Soft offboard |
| U5 | List users | `GET /api/resource/User?filters=...` | Exclude Guest/Administrator in UI |

**Guardrails already on backend:**

- Control site: stock signup **disabled** (`disable_signup=1`).  
- Public path is **/start** → Pending tenant (T1), not shared desk user.  
- Onboarding hooks skip Guest self-signup on control plane.

---

## 10. Suggested new-frontend screens ↔ APIs

Use this as the wiring checklist when you drop the product feature list in.

| Screen | Primary APIs |
|---|---|
| Marketing landing | Static / CMS — no backend required |
| Create organization | T1 (+ show Pending message) |
| Login | A1 → A5 |
| App shell / nav | A5 modules |
| Home dashboard | R6 counts: Customer, Sales Invoice, Purchase Invoice, Item |
| Customers | R1–R5 `Customer` (+ Contact/Address) |
| Leads / Pipeline | `Lead`, `Opportunity` |
| Products | `Item` |
| Sales orders / invoices | `Sales Order`, `Sales Invoice` + submit |
| Purchases | `Purchase Order`, `Purchase Invoice`, `Supplier` |
| Stock / batches | Stock reports + `Batch` |
| Payments | `Payment Entry` |
| Reports hub | query_report.run |
| Settings | `Company`, user defaults |
| Team / users | U1–U5 |
| Super: Organizations | T2–T4 |
| Super: Module toggles | P2 |

---

## 11. Environments & hosts

| Env | URL / note |
|---|---|
| Control / shared (today) | `https://65.1.92.180.sslip.io` |
| Org signup page | `https://65.1.92.180.sslip.io/start` |
| Future tenant host | `https://{site_name}.65.1.92.180.sslip.io` (needs wildcard Traefik + dns_multitenant) |
| New FE (local) | `web/` — `yarn dev` at `http://localhost:5174`, API proxy to control host |

**Config the FE needs:**

```env
VITE_API_BASE=https://65.1.92.180.sslip.io
VITE_SITE_NAME=frontend
# Later: per-tenant API base from login subdomain
```

---

## 12. Non-goals / honesty

| Topic | Reality |
|---|---|
| Form customizations per company on one site | **Not possible** in ERPNext — site-global |
| Full QBO clone in one sprint | No — ship screen-by-screen on resource APIs |
| Auto-provision on every /start | Not automatic yet — Pending + `provision-tenant.sh` |
| SMTP / forgot-password | Backend email still unreliable — don’t block CRM on it |
| Replacing `/portal` | Out of scope for this FE |

---

## 13. Implementation order (when we build the FE)

1. Scaffold FE (Vite/React or your stack) with API client (cookies + CSRF).  
2. Login + boot shell (A1, A5).  
3. Landing + Create organization (T1) — optional re-skin of `/start`.  
4. Customers + Items (CRM core).  
5. Sales Order / Sales Invoice.  
6. Purchases + Stock as needed.  
7. Team invites (U1–U3).  
8. Super-admin Organizations view if platform operators use the same app.  
9. Wire tenant subdomain switching when multi-site routing is live.

---

## 14. Your feature list (paste here)

When you share the required screens/features, we map each line to a row in §10 and mark:

- [ ] Exists in API today  
- [ ] Needs new whitelist method  
- [ ] Needs DocType / workflow  
- [ ] Out of scope / later  

```
(paste product requirements under this heading)
```

---

## 15. Quick reference — Prime Ledger custom methods

```
erpnext.portal_control.api.get_portal_boot
erpnext.portal_control.api.set_module_enabled
erpnext.portal_control.api.save_portal_settings
erpnext.portal_control.tenants.signup_organization          # guest
erpnext.portal_control.tenants.list_tenants
erpnext.portal_control.tenants.register_tenant
erpnext.portal_control.tenants.set_tenant_status
erpnext.portal_control.tenancy.bind_user_company
erpnext.portal_control.tenancy.list_company_bindings
```

Plus Frappe stock: `login`, `logout`, `frappe.auth.get_logged_user`, `/api/resource/*`, `frappe.client.*`, `frappe.desk.query_report.run`.

---

## 16. Related docs in repo

- [Multi_Tenant_Sultan_FA_Split_Playbook.md](./Multi_Tenant_Sultan_FA_Split_Playbook.md) — splitting shared companies onto sites  
- [Prime_Ledger_Client_Progress_Report.md](./Prime_Ledger_Client_Progress_Report.md) — product progress narrative  
- Deploy: `deploy/ec2/provision-tenant.sh`, `deploy/ec2/e2e_post_login.py`

---

*Last updated: `web/` implements §10 defaults (login, signup, CRM lists, team, super-admin orgs). Update §14 when a custom product checklist arrives; keep §5–§8 as the API contract unless backend methods change.*
