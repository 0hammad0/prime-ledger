frappe.provide("erpnext.setup");

frappe.pages["setup-wizard"].on_page_load = function (wrapper) {
	// Only skip wizard when setup is marked complete (not merely company exists).
	const apps = frappe.boot?.setup_wizard_completed_apps || [];
	if (apps.includes("erpnext") && (frappe.sys_defaults.company || frappe.boot?.sysdefaults?.company)) {
		window.location.assign("/portal");
		return;
	}
};

// After setup wizard finishes, land on Prime Ledger portal dashboard.
frappe.ready(function () {
	$(document).on("setup_complete", function () {
		setTimeout(function () {
			window.location.assign("/portal");
		}, 800);
	});
});

// Patch wizard submit so country/currency from later slides are never dropped.
frappe.setup.on("after_load", function () {
	if (!frappe.setup.SetupWizard?.prototype || frappe.setup.SetupWizard.prototype.__pl_args_patched) {
		return;
	}
	const original = frappe.setup.SetupWizard.prototype.setup_complete_and_show_working_state;
	if (typeof original !== "function") {
		return;
	}
	frappe.setup.SetupWizard.prototype.setup_complete_and_show_working_state = function () {
		try {
			const values = this.values || frappe.wizard?.values || {};
			(this.slides || []).forEach((slide) => {
				if (!slide?.form?.fields_dict) return;
				["country", "currency", "company_name", "company_abbr", "chart_of_accounts", "timezone"].forEach(
					(key) => {
						const field = slide.form.fields_dict[key];
						const val = field?.get_value?.();
						if (val) values[key] = val;
					}
				);
			});
			this.values = values;
			if (frappe.wizard) frappe.wizard.values = values;
		} catch (e) {
			console.warn("Prime Ledger setup args merge skipped", e);
		}
		return original.apply(this, arguments);
	};
	frappe.setup.SetupWizard.prototype.__pl_args_patched = true;
});

// Brand the setup working state (Frappe core still says "Starting Frappe ...").
frappe.setup.on("after_load", function () {
	if (!frappe.setup.SetupWizard?.prototype || frappe.setup.SetupWizard.prototype.__prime_ledger_branded) {
		return;
	}
	frappe.setup.SetupWizard.prototype.show_working_state = function () {
		this.container.hide();
		frappe.set_route(this.page_name);

		this.$working_state = this.get_message(
			__("Almost done"),
			__("Setting up Prime Ledger for you… Please wait.")
		).appendTo(this.parent);

		this.attach_abort_button();

		this.current_id = this.slides.length;
		this.current_slide = null;
	};
	frappe.setup.SetupWizard.prototype.__prime_ledger_branded = true;
});

frappe.setup.on("before_load", function () {
	if (
		frappe.boot.setup_wizard_completed_apps?.length &&
		frappe.boot.setup_wizard_completed_apps.includes("erpnext")
	) {
		return;
	}

	erpnext.setup.slides_settings.map(frappe.setup.add_slide);
});

erpnext.setup.slides_settings = [
	{
		// Persona — help us tailor the setup
		name: "persona",
		title: __("Welcome to Prime Ledger"),
		help: __("Answer a few easy questions. We will set things up for you."),
		fields: [
			{
				fieldname: "persona_implementing_for",
				label: __("Who is this for?"),
				fieldtype: "Select",
				options: ["", "My own business", "A company I work for", "A client I'm helping"].join("\n"),
				reqd: 1,
			},
			{
				fieldname: "persona_company_size",
				label: __("How many people work there?"),
				fieldtype: "Select",
				options: ["", "Just me / 1–10", "11–50", "51–200", "201–1,000", "1,000+"].join("\n"),
				reqd: 1,
			},
			{
				fieldname: "persona_industry",
				label: __("What kind of business?"),
				fieldtype: "Select",
				options: [
					"",
					"Manufacturing",
					"Retail / Shop",
					"Wholesale / Distribution",
					"Online shop",
					"Services / Consulting",
					"Construction / Real Estate",
					"Technology / Software",
					"Healthcare",
					"Education",
					"Agriculture",
					"Food & Beverage",
					"Non Profit",
					"Other",
				].join("\n"),
				reqd: 1,
			},
			{
				fieldname: "persona_current_system",
				label: __("How do you keep records today?"),
				fieldtype: "Select",
				options: [
					"",
					"Paper / notebook",
					"Excel / Spreadsheets",
					"Tally",
					"QuickBooks",
					"Zoho",
					"Xero",
					"Something else",
					"Nothing yet — starting fresh",
				].join("\n"),
				reqd: 1,
			},
			{
				fieldtype: "Section Break",
				description: __("What do you need? (you can change this later)"),
			},
			{ fieldname: "module_accounting", label: __("Money & accounts"), fieldtype: "Check" },
			{ fieldname: "module_stock", label: __("Stock / inventory"), fieldtype: "Check" },
			{ fieldtype: "Column Break" },
			{ fieldname: "module_manufacturing", label: __("Making products"), fieldtype: "Check" },
			{ fieldname: "module_projects", label: __("Projects / jobs"), fieldtype: "Check" },
		],

		onload: function (slide) {
			this.bind_industry_modules(slide);
		},

		bind_industry_modules: function (slide) {
			let me = this;
			slide.get_input("persona_industry").on("change", function () {
				me.apply_industry_modules(slide);
			});
		},

		apply_industry_modules: function (slide) {
			let industry = slide.get_field("persona_industry").get_value();
			let modules = erpnext.setup.industry_modules[industry] || ["accounting"];
			["accounting", "stock", "manufacturing", "projects"].forEach(function (module) {
				slide.get_field("module_" + module).set_value(modules.includes(module) ? 1 : 0);
			});
		},
	},
	{
		// Organization
		name: "organization",
		title: __("Tell us about your business"),
		help: __("Use the real name people know. We fill the hard parts for you."),
		fields: [
			{
				fieldname: "company_name",
				label: __("Business name"),
				fieldtype: "Data",
				reqd: 1,
				description: __("Example: Sultan Traders"),
			},
			{
				fieldname: "company_abbr",
				label: __("Short code"),
				fieldtype: "Data",
				reqd: 1,
				description: __("A short code for documents — we can fill this for you"),
			},
			{ fieldtype: "Section Break" },
			{
				fieldname: "country",
				label: __("Country"),
				fieldtype: "Link",
				options: "Country",
				reqd: 1,
			},
			{
				fieldname: "currency",
				label: __("Money you use (currency)"),
				fieldtype: "Link",
				options: "Currency",
				reqd: 1,
			},
			{ fieldtype: "Section Break" },
			{
				fieldname: "chart_of_accounts",
				label: __("Accounts list"),
				options: "",
				fieldtype: "Select",
				description: __("Leave the first option if you are not sure"),
			},
			{ fieldname: "view_coa", label: __("Preview accounts list"), fieldtype: "Button", hidden: 1 },
			{
				fieldname: "fy_start_date",
				label: __("Business year starts on"),
				fieldtype: "Date",
				reqd: 1,
				description: __("Usually 1 January or 1 July"),
			},
			// end date should be hidden (auto calculated)
			{ fieldname: "fy_end_date", label: __("End Date"), fieldtype: "Date", reqd: 1, hidden: 1 },
			{ fieldtype: "Section Break" },
			{
				fieldname: "setup_demo",
				label: __("Add sample data so I can click around"),
				fieldtype: "Check",
				description: __("Optional. You can delete the sample data later."),
			},
		],

		onload: function (slide) {
			this.bind_events(slide);
			this.prefill_country_currency(slide);
		},

		before_show: function () {
			this.prefill_country_currency(this);
			this.load_chart_of_accounts(this);
			this.set_fy_dates(this);
		},

		prefill_country_currency: function (slide) {
			const country =
				(frappe.wizard && frappe.wizard.values && frappe.wizard.values.country) ||
				frappe.defaults.get_default("country") ||
				"";
			const currency =
				(frappe.wizard && frappe.wizard.values && frappe.wizard.values.currency) ||
				frappe.defaults.get_default("currency") ||
				"";
			if (country && !slide.get_value("country")) {
				slide.get_field("country").set_value(country);
			}
			if (currency && !slide.get_value("currency")) {
				slide.get_field("currency").set_value(currency);
			}
		},

		validate: function () {
			if (!this.validate_fy_dates()) {
				return false;
			}

			if ((this.values.company_name || "").toLowerCase() == "company") {
				frappe.msgprint(__("Please type your real business name"));
				return false;
			}
			if (!this.values.company_abbr) {
				frappe.msgprint(__("Please enter a short code (or keep the one we filled)"));
				return false;
			}
			if (this.values.company_abbr.length > 10) {
				frappe.msgprint(__("Short code should be 10 letters or less"));
				return false;
			}
			if (!this.values.country) {
				frappe.msgprint(__("Please choose your country"));
				return false;
			}
			if (!this.values.currency) {
				frappe.msgprint(__("Please choose your currency (money type)"));
				return false;
			}

			// Keep Frappe wizard values in sync for later stages / retries
			if (frappe.wizard && frappe.wizard.values) {
				frappe.wizard.values.country = this.values.country;
				frappe.wizard.values.currency = this.values.currency;
			}

			return true;
		},

		validate_fy_dates: function () {
			// validate fiscal year start and end dates
			const invalid =
				this.values.fy_start_date == "Invalid date" || this.values.fy_end_date == "Invalid date";
			const start_greater_than_end = this.values.fy_start_date > this.values.fy_end_date;

			if (invalid || start_greater_than_end) {
				frappe.msgprint(__("Please enter valid Financial Year Start and End Dates"));
				return false;
			}

			return true;
		},

		set_fy_dates: function (slide) {
			var country =
				slide.get_value("country") ||
				(frappe.wizard && frappe.wizard.values && frappe.wizard.values.country) ||
				frappe.defaults.get_default("country");

			if (country) {
				let fy = erpnext.setup.fiscal_years[country];
				let current_year = moment(new Date()).year();
				let next_year = current_year + 1;
				if (!fy) {
					fy = ["01-01", "12-31"];
					next_year = current_year;
				}

				let year_start_date = current_year + "-" + fy[0];
				if (year_start_date > frappe.datetime.get_today()) {
					next_year = current_year;
					current_year -= 1;
				}
				slide.get_field("fy_start_date").set_value(current_year + "-" + fy[0]);
				slide.get_field("fy_end_date").set_value(next_year + "-" + fy[1]);
			}
		},

		load_chart_of_accounts: function (slide) {
			let country =
				slide.get_value("country") ||
				(frappe.wizard && frappe.wizard.values && frappe.wizard.values.country) ||
				frappe.defaults.get_default("country");

			if (country) {
				frappe.call({
					method: "erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts.get_charts_for_country",
					args: { country: country, with_standard: true },
					callback: function (r) {
						if (r.message) {
							slide.get_input("chart_of_accounts").empty().add_options(r.message);
						}
					},
				});
			}
		},

		bind_events: function (slide) {
			let me = this;
			slide.get_input("country").on("change", function () {
				const country = slide.get_value("country");
				if (frappe.wizard && frappe.wizard.values) {
					frappe.wizard.values.country = country;
				}
				me.set_fy_dates(slide);
				me.load_chart_of_accounts(slide);
				if (country) {
					frappe.call({
						method: "frappe.geo.country_info.get_country_timezone_info",
						callback: function () {},
					});
					frappe.model.with_doc("Country", country, function () {
						// Currency often mirrors System Settings after country pick on core slide;
						// keep a sensible default when empty.
						if (!slide.get_value("currency") && frappe.wizard?.values?.currency) {
							slide.get_field("currency").set_value(frappe.wizard.values.currency);
						}
					});
				}
			});

			slide.get_input("currency").on("change", function () {
				if (frappe.wizard && frappe.wizard.values) {
					frappe.wizard.values.currency = slide.get_value("currency");
				}
			});

			slide.get_input("fy_start_date").on("change", function () {
				var start_date = slide.form.fields_dict.fy_start_date.get_value();
				var year_end_date = frappe.datetime.add_days(frappe.datetime.add_months(start_date, 12), -1);
				slide.form.fields_dict.fy_end_date.set_value(year_end_date);
			});

			slide.get_input("view_coa").on("click", function () {
				let chart_template = slide.form.fields_dict.chart_of_accounts.get_value();
				if (!chart_template) return;

				me.charts_modal(slide, chart_template);
			});

			slide
				.get_input("company_name")
				.on("input", function () {
					let parts = slide.get_input("company_name").val().split(" ");
					let abbr = $.map(parts, function (p) {
						return p ? p.substr(0, 1) : null;
					}).join("");
					slide.get_field("company_abbr").set_value(abbr.slice(0, 10).toUpperCase());
				})
				.val(frappe.boot.sysdefaults.company_name || "")
				.trigger("change");

			slide
				.get_input("company_abbr")
				.on("change", function () {
					let abbr = slide.get_input("company_abbr").val();
					if (abbr.length > 10) {
						frappe.msgprint(__("Company Abbreviation cannot have more than 5 characters"));
						abbr = abbr.slice(0, 10);
					}
					slide.get_field("company_abbr").set_value(abbr);
				})
				.val(frappe.boot.sysdefaults.company_abbr || "")
				.trigger("change");
		},

		charts_modal: function (slide, chart_template) {
			let parent = __("All Accounts");

			let dialog = new frappe.ui.Dialog({
				title: chart_template,
				fields: [
					{
						fieldname: "expand_all",
						label: __("Expand All"),
						fieldtype: "Button",
						click: function () {
							// expand all nodes on button click
							coa_tree.load_children(coa_tree.root_node, true);
						},
					},
					{
						fieldname: "collapse_all",
						label: __("Collapse All"),
						fieldtype: "Button",
						click: function () {
							// collapse all nodes
							coa_tree
								.get_all_nodes(coa_tree.root_node.data.value, coa_tree.root_node.is_root)
								.then((data_list) => {
									data_list.map((d) => {
										coa_tree.toggle_node(coa_tree.nodes[d.parent]);
									});
								});
						},
					},
				],
			});

			// render tree structure in the dialog modal
			let coa_tree = new frappe.ui.Tree({
				parent: $(dialog.body),
				label: parent,
				expandable: true,
				method: "erpnext.accounts.utils.get_coa",
				args: {
					chart: chart_template,
					parent: parent,
					doctype: "Account",
				},
				onclick: function (node) {
					parent = node.value;
				},
			});

			// add class to show buttons side by side
			const form_container = $(dialog.body).find("form");
			const buttons = $(form_container).find(".frappe-control");
			form_container.addClass("flex");
			buttons.map((index, button) => {
				$(button).css({ "margin-right": "1em" });
			});

			dialog.show();
			coa_tree.load_children(coa_tree.root_node, true); // expand all node trigger
		},
	},
];

// Modules pre-selected on the persona slide based on the chosen industry.
// Keys must match the persona_industry option values. Accounting is always on.
erpnext.setup.industry_modules = {
	Manufacturing: ["accounting", "stock", "manufacturing"],
	Retail: ["accounting", "stock"],
	"Wholesale / Distribution": ["accounting", "stock"],
	"E-commerce": ["accounting", "stock"],
	"Services / Consulting": ["accounting", "projects"],
	"Construction / Real Estate": ["accounting", "stock", "projects"],
	"Technology / Software": ["accounting", "projects"],
	Healthcare: ["accounting", "stock"],
	Education: ["accounting", "projects"],
	Agriculture: ["accounting", "stock"],
	"Food & Beverage": ["accounting", "stock", "manufacturing"],
	"Non Profit": ["accounting", "projects"],
	Other: ["accounting"],
};

// Source: https://en.wikipedia.org/wiki/Fiscal_year
// default 1st Jan - 31st Dec

erpnext.setup.fiscal_years = {
	Afghanistan: ["12-21", "12-20"],
	Australia: ["07-01", "06-30"],
	Bangladesh: ["07-01", "06-30"],
	"Costa Rica": ["10-01", "09-30"],
	Egypt: ["07-01", "06-30"],
	Ethiopia: ["07-08", "07-07"],
	"Hong Kong": ["04-01", "03-31"],
	India: ["04-01", "03-31"],
	Iran: ["06-23", "06-22"],
	Kenya: ["07-01", "06-30"],
	Malaysia: ["07-01", "06-30"],
	Myanmar: ["04-01", "03-31"],
	Nepal: ["07-16", "07-15"],
	"New Zealand": ["04-01", "03-31"],
	Pakistan: ["07-01", "06-30"],
	Singapore: ["04-01", "03-31"],
	"South Africa": ["03-01", "02-28"],
	"United Kingdom": ["04-01", "03-31"],
};
