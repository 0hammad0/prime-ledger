# Prime Ledger — Client Progress Report

**Status:** Live on production  
**Site:** https://65.1.92.180.sslip.io/  
**Date:** 4 August 2026  

---

## Bottom line

Prime Ledger now presents as its own product for normal users:

- Branded **login / signup** (no ERPNext product naming on customer screens)
- **Navy + teal** color theme
- After login, users land on a simple **business home** with numbered **Start here** steps
- Setup and portal copy rewritten in everyday language for non-technical staff

The full operations engine (stock, sales, purchases, accounts) still runs underneath. The portal is the easier front door.

---

## What we completed

| Area | What changed | Status |
|------|----------------|--------|
| Product branding | Customer-facing titles, logos, and footers say **Prime Ledger** | Live |
| Color theme | Navy `#102A43` + teal `#0F766E` on login, signup, desk, wizard | Live |
| Login experience | PL logo, brand title, tips, larger buttons, plain language | Live |
| Signup | Sign up enabled with clear steps: create account → email → sign in | Live |
| Post-login routing | Users go to the **portal home**, not the old Desk landing | Live |
| Setup wizard | Everyday questions; finish lands on portal home | Live |
| Business home | Welcome + **Start here**: Products → Sales → Purchases → Money | Live |
| Help / docs cleanup | ERPNext documentation links removed from help and error text | Live |

---

## Color scheme

| Role | Color | Hex |
|------|--------|-----|
| Primary / navbar | Deep navy | `#102A43` |
| Accent / buttons | Teal | `#0F766E` |
| Soft accent | Lighter teal | `#14B8A6` |
| Page background | Cool paper | `#F0F4F8` |

---

## What the client should expect (user journey)

| When | What they should see |
|------|----------------------|
| Open the site | Login page with Prime Ledger branding and navy/teal theme |
| New user | Sign up → check email → Sign in → short setup questions → business home |
| Existing user | Sign in → business home with **Start here** steps |
| Daily work | Tap Products, Sales, Purchases, or Money; other tools under “More tools” |
| Advanced work | **Advanced tools** opens full operational screens when needed |

### Simple path for a first-time user

1. Open **/login**  
2. Tap **Sign up** → enter name and email  
3. Open the verification email  
4. Return and **Sign in**  
5. Answer a few easy setup questions about the business  
6. Land on **Home** → tap **Step 1: Products** to begin  

---

## Easy-flow design goals

- Plain words instead of ERP jargon (e.g. Desk → **Advanced tools**, Tenant → **Your business**)
- Large buttons and clear **Sign in / Create account** labels
- Numbered **Start here** path on the business home
- Setup questions written for shop / warehouse / office staff without accounting training

---

## What is intentionally unchanged

- Internal technical folders may still use the name `erpnext` (package / asset paths). Customers do **not** see this as product branding.
- Full operational screens (items, orders, stock, accounts) remain on the proven engine.
- Chemical / lab **industry packaging** (extra named menus, subscription packs) is capability-ready via configuration; it is not a separate industry app install in this phase.

---

## Suggested next steps

| Item | Why it matters | Priority |
|------|----------------|----------|
| Desk lockout for normal users | Keep everyday users on the simple portal; admins keep full access | Recommended |
| Subscription / pack controls | Turn modules on/off per plan (SaaS packaging) | Phase 2 |
| Training walkthrough | Short guided tour on first login | Recommended |
| Own help docs | Replace removed ERPNext links with Prime Ledger help | Phase 2 |
| Chemical / lab menu pack | Named menus from the blueprint if the client requires them | Optional |

---

## 5-minute verification checklist

1. Open `/login` — PL logo, “Prime Ledger”, navy/teal theme  
2. Tap **Sign up** — see the step tip  
3. **Sign in** — land on business home (not a blank Desk)  
4. Confirm **Start here** shows Products, Sales, Purchases, Money  
5. Open one step — big **Open …** button; no ERPNext product name on screen  

---

## Contact / environment notes

- Production URL: https://65.1.92.180.sslip.io/  
- Portal routes: `/portal`, `/portal/tenant` (business), `/portal/admin` (site admin)  
- Brand assets and easy-flow helpers are applied on the live server and kept in the deploy branding scripts for future updates  

---

*Prepared for client sharing — Prime Ledger project team.*
