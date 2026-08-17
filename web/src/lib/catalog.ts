export type Field = {
  key: string;
  label: string;
  required?: boolean;
  type?: string;
  link?: string;
};

export type Resource = {
  id: string;
  doctype: string;
  title: string;
  hint?: string;
  path: string;
  columns: Field[];
  createFields?: Field[];
  extraDoc?: Record<string, unknown>;
  partyDoctype?: string;
  partyField?: string;
  hasItems?: boolean;
  submitable?: boolean;
  module?: string;
};

export const RESOURCES: Resource[] = [
  {
    id: "customers",
    doctype: "Customer",
    title: "Customers",
    hint: "People and companies you sell to.",
    path: "/customers",
    module: "crm",
    columns: [
      { key: "customer_name", label: "Name" },
      { key: "customer_type", label: "Type" },
      { key: "territory", label: "Territory" },
    ],
    createFields: [{ key: "customer_name", label: "Customer name", required: true }],
    extraDoc: { customer_type: "Company", customer_group: "All Customer Groups", territory: "All Territories" },
  },
  {
    id: "leads",
    doctype: "Lead",
    title: "Leads",
    hint: "New people who may buy.",
    path: "/crm/leads",
    module: "crm",
    columns: [
      { key: "lead_name", label: "Name" },
      { key: "email_id", label: "Email" },
      { key: "status", label: "Status" },
    ],
    createFields: [
      { key: "lead_name", label: "Name", required: true },
      { key: "email_id", label: "Email", type: "email" },
    ],
  },
  {
    id: "opportunities",
    doctype: "Opportunity",
    title: "Opportunities",
    path: "/crm/opportunities",
    module: "crm",
    columns: [
      { key: "opportunity_from", label: "From" },
      { key: "party_name", label: "Party" },
      { key: "status", label: "Status" },
    ],
    createFields: [
      { key: "opportunity_from", label: "From", required: true },
      { key: "party_name", label: "Party", required: true },
    ],
    extraDoc: { opportunity_from: "Customer" },
  },
  {
    id: "items",
    doctype: "Item",
    title: "Items",
    hint: "Things you buy and sell.",
    path: "/products",
    module: "inventory",
    columns: [
      { key: "item_name", label: "Name" },
      { key: "item_group", label: "Group" },
      { key: "stock_uom", label: "UOM" },
    ],
    createFields: [
      { key: "item_code", label: "Item code", required: true },
      { key: "item_name", label: "Name", required: true },
    ],
    extraDoc: { item_group: "All Item Groups", stock_uom: "Nos", is_stock_item: 1 },
  },
  {
    id: "quotations",
    doctype: "Quotation",
    title: "Quotations",
    path: "/sales/quotations",
    module: "sales",
    partyDoctype: "Customer",
    partyField: "party_name",
    hasItems: true,
    submitable: true,
    extraDoc: { quotation_to: "Customer" },
    columns: [
      { key: "party_name", label: "Customer" },
      { key: "transaction_date", label: "Date" },
      { key: "grand_total", label: "Total" },
      { key: "status", label: "Status" },
    ],
  },
  {
    id: "sales-orders",
    doctype: "Sales Order",
    title: "Sales Orders",
    path: "/sales/orders",
    module: "sales",
    partyDoctype: "Customer",
    partyField: "customer",
    hasItems: true,
    submitable: true,
    columns: [
      { key: "customer", label: "Customer" },
      { key: "transaction_date", label: "Date" },
      { key: "grand_total", label: "Total" },
      { key: "status", label: "Status" },
    ],
  },
  {
    id: "delivery-notes",
    doctype: "Delivery Note",
    title: "Delivery Notes",
    path: "/sales/delivery",
    module: "sales",
    partyDoctype: "Customer",
    partyField: "customer",
    hasItems: true,
    submitable: true,
    columns: [
      { key: "customer", label: "Customer" },
      { key: "posting_date", label: "Date" },
      { key: "grand_total", label: "Total" },
      { key: "status", label: "Status" },
    ],
  },
  {
    id: "sales-invoices",
    doctype: "Sales Invoice",
    title: "Sales Invoices",
    path: "/sales/invoices",
    module: "sales",
    partyDoctype: "Customer",
    partyField: "customer",
    hasItems: true,
    submitable: true,
    columns: [
      { key: "customer", label: "Customer" },
      { key: "posting_date", label: "Date" },
      { key: "grand_total", label: "Total" },
      { key: "outstanding_amount", label: "Outstanding" },
      { key: "status", label: "Status" },
    ],
  },
  {
    id: "suppliers",
    doctype: "Supplier",
    title: "Suppliers",
    path: "/purchases/suppliers",
    module: "purchase",
    columns: [
      { key: "supplier_name", label: "Name" },
      { key: "supplier_group", label: "Group" },
    ],
    createFields: [{ key: "supplier_name", label: "Supplier name", required: true }],
    extraDoc: { supplier_group: "All Supplier Groups" },
  },
  {
    id: "supplier-quotations",
    doctype: "Supplier Quotation",
    title: "Supplier Quotations",
    path: "/purchases/rfq",
    module: "purchase",
    partyDoctype: "Supplier",
    partyField: "supplier",
    hasItems: true,
    submitable: true,
    columns: [
      { key: "supplier", label: "Supplier" },
      { key: "transaction_date", label: "Date" },
      { key: "grand_total", label: "Total" },
      { key: "status", label: "Status" },
    ],
  },
  {
    id: "purchase-orders",
    doctype: "Purchase Order",
    title: "Purchase Orders",
    path: "/purchases/orders",
    module: "purchase",
    partyDoctype: "Supplier",
    partyField: "supplier",
    hasItems: true,
    submitable: true,
    columns: [
      { key: "supplier", label: "Supplier" },
      { key: "transaction_date", label: "Date" },
      { key: "grand_total", label: "Total" },
      { key: "status", label: "Status" },
    ],
  },
  {
    id: "purchase-receipts",
    doctype: "Purchase Receipt",
    title: "Purchase Receipts",
    path: "/purchases/receipts",
    module: "purchase",
    partyDoctype: "Supplier",
    partyField: "supplier",
    hasItems: true,
    submitable: true,
    columns: [
      { key: "supplier", label: "Supplier" },
      { key: "posting_date", label: "Date" },
      { key: "grand_total", label: "Total" },
      { key: "status", label: "Status" },
    ],
  },
  {
    id: "purchase-invoices",
    doctype: "Purchase Invoice",
    title: "Purchase Invoices",
    path: "/purchases/bills",
    module: "purchase",
    partyDoctype: "Supplier",
    partyField: "supplier",
    hasItems: true,
    submitable: true,
    columns: [
      { key: "supplier", label: "Supplier" },
      { key: "posting_date", label: "Date" },
      { key: "grand_total", label: "Total" },
      { key: "outstanding_amount", label: "Outstanding" },
      { key: "status", label: "Status" },
    ],
  },
  {
    id: "warehouses",
    doctype: "Warehouse",
    title: "Warehouses",
    path: "/stock/warehouses",
    module: "inventory",
    columns: [
      { key: "warehouse_name", label: "Name" },
      { key: "parent_warehouse", label: "Parent" },
      { key: "company", label: "Company" },
    ],
    createFields: [{ key: "warehouse_name", label: "Warehouse name", required: true }],
  },
  {
    id: "stock-entries",
    doctype: "Stock Entry",
    title: "Stock Entries",
    path: "/stock/entries",
    module: "inventory",
    hasItems: true,
    submitable: true,
    extraDoc: { stock_entry_type: "Material Receipt", purpose: "Material Receipt" },
    columns: [
      { key: "stock_entry_type", label: "Type" },
      { key: "posting_date", label: "Date" },
      { key: "docstatus", label: "Status" },
    ],
  },
  {
    id: "bins",
    doctype: "Bin",
    title: "Stock Balance",
    hint: "On-hand quantity by warehouse.",
    path: "/stock/balance",
    module: "inventory",
    columns: [
      { key: "item_code", label: "Item" },
      { key: "warehouse", label: "Warehouse" },
      { key: "actual_qty", label: "Qty" },
    ],
  },
  {
    id: "batches",
    doctype: "Batch",
    title: "Batches",
    path: "/batches",
    module: "inventory",
    columns: [
      { key: "item", label: "Item" },
      { key: "expiry_date", label: "Expiry" },
      { key: "batch_qty", label: "Qty" },
    ],
  },
  {
    id: "quality",
    doctype: "Quality Inspection",
    title: "Quality checks",
    path: "/quality",
    module: "inventory",
    columns: [
      { key: "inspection_type", label: "Type" },
      { key: "item_code", label: "Item" },
      { key: "status", label: "Status" },
    ],
  },
  {
    id: "accounts",
    doctype: "Account",
    title: "Chart of Accounts",
    path: "/finance/accounts",
    module: "accounts",
    columns: [
      { key: "account_name", label: "Name" },
      { key: "parent_account", label: "Parent" },
      { key: "company", label: "Company" },
    ],
  },
  {
    id: "journal",
    doctype: "Journal Entry",
    title: "Journal Entries",
    path: "/finance/journal",
    module: "accounts",
    submitable: true,
    columns: [
      { key: "posting_date", label: "Date" },
      { key: "voucher_type", label: "Type" },
      { key: "total_debit", label: "Debit" },
      { key: "user_remark", label: "Remark" },
    ],
    createFields: [
      { key: "user_remark", label: "Remark" },
      { key: "posting_date", label: "Date", type: "date" },
    ],
    extraDoc: { voucher_type: "Journal Entry" },
  },
  {
    id: "payments",
    doctype: "Payment Entry",
    title: "Payment Entries",
    path: "/finance/payments",
    module: "accounts",
    partyDoctype: "Customer",
    partyField: "party",
    submitable: true,
    columns: [
      { key: "payment_type", label: "Type" },
      { key: "party", label: "Party" },
      { key: "paid_amount", label: "Amount" },
      { key: "posting_date", label: "Date" },
    ],
    createFields: [
      { key: "payment_type", label: "Type (Receive or Pay)", required: true },
      { key: "party", label: "Party", required: true },
      { key: "paid_amount", label: "Amount", type: "number", required: true },
    ],
  },
  {
    id: "bank-accounts",
    doctype: "Bank Account",
    title: "Bank Accounts",
    path: "/banking/accounts",
    module: "banking",
    columns: [
      { key: "account_name", label: "Name" },
      { key: "bank", label: "Bank" },
      { key: "company", label: "Company" },
    ],
    createFields: [
      { key: "account_name", label: "Account name", required: true },
      { key: "bank", label: "Bank", required: true },
    ],
  },
  {
    id: "bank-transactions",
    doctype: "Bank Transaction",
    title: "Bank Transactions",
    path: "/banking/transactions",
    module: "banking",
    columns: [
      { key: "date", label: "Date" },
      { key: "bank_account", label: "Account" },
      { key: "deposit", label: "Deposit" },
      { key: "withdrawal", label: "Withdrawal" },
      { key: "status", label: "Status" },
    ],
  },
  {
    id: "employees",
    doctype: "Employee",
    title: "Employees",
    path: "/hr/employees",
    module: "hr",
    columns: [
      { key: "employee_name", label: "Name" },
      { key: "status", label: "Status" },
      { key: "company", label: "Company" },
    ],
    createFields: [
      { key: "first_name", label: "First name", required: true },
      { key: "last_name", label: "Last name" },
      { key: "gender", label: "Gender", required: true },
      { key: "date_of_joining", label: "Join date", type: "date", required: true },
    ],
    extraDoc: { status: "Active" },
  },
  {
    id: "attendance",
    doctype: "Attendance",
    title: "Attendance",
    path: "/hr/attendance",
    module: "hr",
    columns: [
      { key: "employee_name", label: "Employee" },
      { key: "attendance_date", label: "Date" },
      { key: "status", label: "Status" },
    ],
    createFields: [
      { key: "employee", label: "Employee", required: true, link: "Employee" },
      { key: "attendance_date", label: "Date", type: "date", required: true },
      { key: "status", label: "Status", required: true },
    ],
    extraDoc: { status: "Present" },
  },
  {
    id: "leave",
    doctype: "Leave Application",
    title: "Leave",
    path: "/hr/leave",
    module: "hr",
    columns: [
      { key: "employee_name", label: "Employee" },
      { key: "from_date", label: "From" },
      { key: "to_date", label: "To" },
      { key: "status", label: "Status" },
    ],
    createFields: [
      { key: "employee", label: "Employee", required: true, link: "Employee" },
      { key: "from_date", label: "From", type: "date", required: true },
      { key: "to_date", label: "To", type: "date", required: true },
      { key: "leave_type", label: "Leave type", required: true },
    ],
  },
  {
    id: "payroll",
    doctype: "Salary Slip",
    title: "Payroll",
    path: "/hr/payroll",
    module: "hr",
    columns: [
      { key: "employee_name", label: "Employee" },
      { key: "start_date", label: "From" },
      { key: "end_date", label: "To" },
      { key: "net_pay", label: "Net pay" },
    ],
  },
  {
    id: "data-import",
    doctype: "Data Import",
    title: "Data Import",
    path: "/import/data",
    module: "import_custom",
    columns: [
      { key: "reference_doctype", label: "DocType" },
      { key: "status", label: "Status" },
      { key: "import_type", label: "Type" },
    ],
  },
  {
    id: "companies",
    doctype: "Company",
    title: "Companies",
    hint: "Books inside this organization. Switching company changes which books you see — not which tenant site you are on.",
    path: "/settings",
    module: "settings",
    columns: [
      { key: "abbr", label: "Abbr" },
      { key: "default_currency", label: "Currency" },
      { key: "country", label: "Country" },
    ],
  },
  {
    id: "bom",
    doctype: "BOM",
    title: "BOM",
    path: "/manufacturing/bom",
    module: "manufacturing",
    columns: [
      { key: "item", label: "Item" },
      { key: "quantity", label: "Qty" },
      { key: "is_active", label: "Active" },
    ],
  },
  {
    id: "work-orders",
    doctype: "Work Order",
    title: "Work Orders",
    path: "/manufacturing/work-orders",
    module: "manufacturing",
    columns: [
      { key: "production_item", label: "Item" },
      { key: "qty", label: "Qty" },
      { key: "status", label: "Status" },
    ],
  },
  {
    id: "projects",
    doctype: "Project",
    title: "Projects",
    path: "/projects",
    module: "projects",
    columns: [
      { key: "project_name", label: "Name" },
      { key: "status", label: "Status" },
      { key: "percent_complete", label: "% complete" },
    ],
    createFields: [{ key: "project_name", label: "Project name", required: true }],
  },
];

export function resourceByPath(path: string) {
  return RESOURCES.find((r) => r.path === path);
}

export function resourcesByModule(module: string) {
  return RESOURCES.filter((r) => r.module === module);
}
