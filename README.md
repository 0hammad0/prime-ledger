<div align="center">
	<img src="./erpnext/public/images/v16/erpnext.svg" alt="Prime Ledger Logo" height="80px" width="80px"/>
	<h2>Prime Ledger</h2>
	<p>Powerful, Intuitive and Open-Source ERP</p>
</div>

<div align="center">
	<img src="./erpnext/public/images/v16/hero_image.png" alt="Prime Ledger Hero Image"/>
</div>

## Prime Ledger

100% Open-Source ERP System to help you run your business. Built on [ERPNext](https://github.com/frappe/erpnext) / [Frappe Framework](https://github.com/frappe/frappe).

### Motivation

Running a business is a complex task - handling invoices, tracking stock, managing personnel, and other daily operations. In a market where software is sold separately to manage each of these tasks, Prime Ledger does all of the above and more.

### Key Features

- **Accounting**: All the tools you need to manage cash flow in one place, right from recording transactions to summarizing and analyzing financial reports.
- **Order Management**: Track inventory levels, replenish stock, and manage sales orders, customers, suppliers, shipments, deliverables, and order fulfillment.
- **Manufacturing**: Simplifies the production cycle, helps track material consumption, exhibits capacity planning, handles subcontracting, and more!
- **Asset Management**: From purchase to disposal, IT infrastructure to equipment. Covers every branch of your organization, all in one centralized system.
- **Projects**: Deliver both internal and external projects on time, budget and profitability. Track tasks, timesheets, and issues by project.

### Under the Hood

- [**Frappe Framework**](https://github.com/frappe/frappe): A full-stack web application framework written in Python and JavaScript.
- [**Frappe UI**](https://github.com/frappe/frappe-ui): A Vue-based UI library for modern single-page applications on Frappe.

## Quick try (Docker)

```sh
git clone https://github.com/frappe/frappe_docker
cd frappe_docker
docker compose -f pwd.yml up -d
```

Open http://localhost:8080 — `Administrator` / `admin`.

> Disposable demo only. For developing this repo, use a local [bench](https://github.com/frappe/bench) install and `bench get-app` from this directory.

## Development Setup

1. Install [bench](https://frappeframework.com/docs/user/en/installation) (Python ≥ 3.14, MariaDB, Redis, Node 24, Yarn).
2. Initialize and create a site:

```sh
bench init --frappe-branch develop frappe-bench
cd frappe-bench
bench new-site prime.localhost
bench get-app /path/to/prime-ledger
bench --site prime.localhost install-app erpnext
bench start
```

3. Open `http://prime.localhost:8000`.

### Banking SPA

```sh
yarn          # installs banking deps
yarn dev      # Vite hot reload for /banking
```

## License

GNU General Public License (v3). See [license.txt](license.txt) and [TRADEMARK_POLICY.md](TRADEMARK_POLICY.md).
