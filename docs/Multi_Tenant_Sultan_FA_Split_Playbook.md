# Playbook: Split Sultan Group / FA Traders onto separate tenant sites

**Do not run until explicitly approved.** This touches production data.

## Goal

Move from one shared site (`frontend`) with two companies to:

- `frontend` — Super Admin control plane + PL Tenant registry  
- `sultan` — Sultan Group only  
- `fa` — FA Traders only  

## Prerequisites

1. Phase 1 company locks applied and verified  
2. Fresh backup: `bash deploy/ec2/backup-now.sh`  
3. Wildcard Traefik `SITES_RULE` + `dns_multitenant on` + `FRAPPE_SITE_NAME_HEADER` unset  
4. Maintenance window agreed  

## Steps (high level)

1. **Backup** current `frontend` site + MariaDB.  
2. **Provision empty tenants**  
   ```bash
   bash deploy/ec2/provision-tenant.sh sultan "Sultan Group"
   bash deploy/ec2/provision-tenant.sh fa "FA Traders"
   ```  
3. **Export company-scoped data** from `frontend` (Data Import / `bench export-fixtures` / selective DocType dumps for each company). Prefer ERPNext’s company filter on export where available.  
4. **Import** into the matching tenant site; complete setup wizard / COA if needed.  
5. **Recreate users** on each tenant site; bind User Permission → Company (only one company per site after split).  
6. **Smoke test** login, portal boot, invoices, stock per org.  
7. **Cutover DNS/hosts** — point users to `sultan.<PUBLIC_HOST>` / `fa.<PUBLIC_HOST>`.  
8. On control site, leave companies listed as archived or remove after verification.  
9. Keep `frontend` for Super Admin / PL Tenant registry only (disable open signup).  

## Rollback

Restore MariaDB + site backups from step 1; re-enable `FRAPPE_SITE_NAME_HEADER=frontend` if needed.

## Notes

- Form customizations on `frontend` do **not** copy automatically — re-apply per tenant if required.  
- Hot-patches must be re-applied after container recreate: `bash deploy/ec2/ensure-portal.sh`.  
