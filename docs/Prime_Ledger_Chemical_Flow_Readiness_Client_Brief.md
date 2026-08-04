# Prime Ledger  
## Chemical & Laboratory Operations — Flow Readiness Brief

**Date:** 4 August 2026  
**Prepared for:** Client discussion  
**Platform:** Prime Ledger  
**Scope:** Chemicals, laboratory products, laboratory equipment, PCR / molecular biology — distributor / importer / wholesaler / institutional supply  

---

### Executive conclusion

**Prime Ledger can run the confirmed chemical and laboratory distributor flow today.**

Purchase, import costing, sales, returns, batch/expiry, serial tracking, and quality inspection are already available. Alignment is **configuration and operating policy** — not a rebuild of the product, and not a change to the core transaction engine.

| Area | Status |
|------|--------|
| Core buy / sell / stock flow | **Ready** |
| Industry masters & warehouses | **Configure** |
| Dedicated CAS / SDS field masters | **Optional later** |

---

### 1. End-to-end transaction flows

| Flow | Document path | Status | Notes |
|------|---------------|--------|-------|
| Local purchase | RFQ → Supplier Quotation → PO → Purchase Receipt → Purchase Invoice → Payment | Ready | Batch / serial / QI at receipt |
| Imported purchase | PO → Purchase Receipt → Landed Cost Voucher → Purchase Invoice → Payment | Ready | Multi-currency + landed cost |
| Sales | Quotation → Sales Order → Delivery Note → Sales Invoice → Payment | Ready | Batch / FEFO picking supported |
| Returns | Return note → credit / debit adjustment | Ready | Batch / serial reversal preserved |
| Stock transfer | Stock Entry between warehouses | Ready | Batch and serial carried across |
| Quality hold | Receipt → Quarantine WH → Quality Inspection → Released / Rejected WH | Ready (configure) | Warehouses + QI policy |
| Equipment service | Serial receipt → Asset / Maintenance / Calibration | Partial | Available; full lifecycle pack optional |

---

### 2. Product master alignment

| Industry need | Prime Ledger capability | Mode |
|---------------|-------------------------|------|
| Item groups (Chemicals, PCR, Equipment, etc.) | Item Group hierarchy | Configure |
| Manufacturer | Brand | Configure |
| Pack size / physical form as SKUs | Item Attributes + Variants | Configure |
| Lot, manufacturing date, expiry | Batch on Purchase Receipt | Ready |
| Equipment serial tracking | Serial No | Ready |
| Price by currency / segment | Price List / Item Price | Ready |
| Incoming QC | Quality Inspection | Ready |
| SDS / COA / TDS files | Attachments on Item / Batch | Configure |
| CAS, formula, storage, hazard fields | Not dedicated masters today | Optional later |

---

### 3. What is ready now

- Local and imported purchasing with multi-currency  
- Wholesale, retail, and institutional sales  
- Batch, expiry, and serial traceability  
- Landed cost for imports  
- Quality Inspection on receipt  
- Price lists, taxes, receivables and payables  
- Stock transfers with lot preservation  

---

### 4. Out of scope for this phase

- No change to the core buy/sell document flow  
- No new chemical LIMS / assay module  
- No dedicated CAS / SDS / PCR DocTypes in this phase  
- SDS / COA handled via attachments until fields are added later (if needed)  
- Industry sidebar packs remain optional  

---

### 5. Configuration checklist (go-live alignment)

1. Create Item Group tree for chemicals, media, PCR, kits, glassware, equipment  
2. Enable batch + expiry (and serial where needed) on relevant items  
3. Create Quarantine, Released, Rejected warehouses; map cold storage if required  
4. Set Stock Settings pick method to **Expiry (FEFO)**; disable negative stock  
5. Require Quality Inspection on incoming for regulated items  
6. Set up purchase / selling price lists, currencies, and tax templates  
7. Attach SDS / COA / datasheets on Item (and lot COA on Batch when needed)  

---

### 6. Recommended operating model

| Phase | Focus | Outcome |
|-------|--------|---------|
| **A — Run on current engine** | Groups, warehouses, QI, FEFO, price lists | Start buying and selling with batch/expiry immediately |
| **B — Compliance hygiene** | SDS/COA attachments, naming rules, quarantine SOPs | Clean audit-friendly operations |
| **C — Optional enrichment** | CAS / storage / hazard / PCR fields | Only if attachments prove insufficient |

---

### Client takeaway

Prime Ledger is **fit for the chemical trading flow**. The system can execute the full commercial and inventory lifecycle for chemicals, laboratory products, and PCR kits. Success depends on **master-data setup and warehouse/QC policy**, not on rebuilding the application.

---

*Confidential — for client discussion. Platform branding: Prime Ledger.*
