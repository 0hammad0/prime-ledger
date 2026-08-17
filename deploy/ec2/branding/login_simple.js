/* Prime Ledger — login helpers; org signup goes to /start; tenant redirect from apex */
(function () {
	var APEX = "65.1.92.180.sslip.io";
	var APEX_URL = "https://" + APEX;

	function isControlHost() {
		var h = (location.hostname || "").toLowerCase();
		return h === APEX || h === "65.1.92.180";
	}

	function isTenantHost() {
		var h = (location.hostname || "").toLowerCase();
		return h.slice(-("." + APEX).length) === "." + APEX && h !== APEX;
	}

	function startHref() {
		return isTenantHost() ? APEX_URL + "/start" : "/start";
	}

	function csrfToken() {
		if (window.csrf_token) return window.csrf_token;
		var m = (document.cookie || "").match(/(?:^|; )csrf_token=([^;]+)/);
		return m ? decodeURIComponent(m[1]) : "";
	}

	function text(el, value) {
		if (el) el.textContent = value;
	}

	function rewriteSignupLinks() {
		var href = startHref();
		document.querySelectorAll("a.btn-signup, .btn-signup, a[href*='#signup'], a[href*='signup']").forEach(function (el) {
			if (el.tagName === "A") {
				el.setAttribute("href", href);
			} else if (el.tagName === "BUTTON") {
				el.addEventListener(
					"click",
					function (ev) {
						ev.preventDefault();
						ev.stopPropagation();
						window.location.href = href;
					},
					true
				);
			}
			var t = (el.textContent || "").trim().toLowerCase();
			if (t === "sign up" || t === "register" || t === "create account") {
				el.textContent = "Create organization";
			}
		});
	}

	function simplifyLoginCopy() {
		document.querySelectorAll(".btn-login, button.btn-primary").forEach(function (btn) {
			var t = (btn.textContent || "").trim().toLowerCase();
			if (t === "continue" || t === "login" || t === "sign in") {
				btn.textContent = "Sign in";
			}
		});

		document.querySelectorAll(".for-login .page-card-head-text h4").forEach(function (h) {
			if (/sign in|login/i.test(h.textContent || "")) {
				h.textContent = isTenantHost()
					? "Sign in to your organization"
					: "Sign in with your email";
			}
		});
		document.querySelectorAll(".for-forgot .page-card-head-text h4").forEach(function (h) {
			h.textContent = "Reset your password";
		});

		document.querySelectorAll("label, .form-label").forEach(function (lab) {
			var t = (lab.textContent || "").trim();
			if (/^email$/i.test(t) || /email or username/i.test(t)) {
				lab.textContent = "Your email";
			}
			if (/^password$/i.test(t)) {
				lab.textContent = "Your password";
			}
		});

		var login = document.querySelector(".for-login .page-card");
		if (login && !login.querySelector(".pl-easy-tip")) {
			var tip = document.createElement("p");
			tip.className = "pl-easy-tip";
			if (isTenantHost()) {
				tip.textContent = "This URL is only for your organization. Use the email you signed up with.";
			} else {
				tip.textContent =
					"New business? Create your organization — you get a private workspace and your own URL.";
			}
			login.appendChild(tip);
			var link = document.createElement("p");
			link.className = "pl-easy-tip";
			link.innerHTML = '<a href="' + startHref() + '">Create organization →</a>';
			login.appendChild(link);
		}

		rewriteSignupLinks();
		fillEmailFromQuery();
	}

	function emailInput() {
		return (
			document.querySelector("input[name=usr]") ||
			document.querySelector("input#login_email") ||
			document.querySelector(".for-login input[type=email]") ||
			document.querySelector(".for-login input[type=text]")
		);
	}

	function fillEmailFromQuery() {
		var params = new URLSearchParams(location.search);
		var email = params.get("email");
		if (!email) return;
		var input = emailInput();
		if (input && !input.value) input.value = email;
	}

	function showBanner(text, isError) {
		var login = document.querySelector(".for-login .page-card") || document.body;
		var el = document.getElementById("pl-login-banner");
		if (!el) {
			el = document.createElement("p");
			el.id = "pl-login-banner";
			el.className = "pl-easy-tip";
			login.insertBefore(el, login.firstChild);
		}
		el.textContent = text;
		el.style.color = isError ? "#9b1c1c" : "#0f766e";
	}

	function call(method, params) {
		var body = new URLSearchParams(params);
		return fetch("/api/method/" + method, {
			method: "POST",
			credentials: "same-origin",
			headers: {
				Accept: "application/json",
				"Content-Type": "application/x-www-form-urlencoded",
				"X-Frappe-CSRF-Token": csrfToken(),
				"X-Requested-With": "XMLHttpRequest"
			},
			body: body
		}).then(function (r) {
			return r.json().then(function (j) {
				return { ok: r.ok, j: j };
			});
		}).then(function (res) {
			var j = res.j || {};
			if (j.exc_type || j.exception || !res.ok) {
				throw new Error(j._error_message || j.exception || "Request failed");
			}
			return j.message || {};
		});
	}

	function consumeTicket() {
		var ticket = new URLSearchParams(location.search).get("ticket");
		if (!ticket) return;
		showBanner("Signing you in…", false);
		call("erpnext.portal_control.tenants.login_with_ticket", { ticket: ticket })
			.then(function (m) {
				window.location.href = m.redirect_to || "/portal";
			})
			.catch(function (err) {
				showBanner(err.message || "Sign-in link expired. Use your email and password.", true);
			});
	}

	function interceptLogin() {
		if (!isControlHost() || isTenantHost()) return;
		var origFetch = window.fetch;
		if (typeof origFetch === "function") {
			window.fetch = function (input, init) {
				var url = typeof input === "string" ? input : input && input.url;
				var method = (init && init.method) || (input && input.method) || "GET";
				if (
					!url ||
					String(method).toUpperCase() !== "POST" ||
					String(url).indexOf("/api/method/login") === -1
				) {
					return origFetch.apply(this, arguments);
				}
				var body = (init && init.body) || "";
				var email = "";
				try {
					email = new URLSearchParams(body).get("usr") || "";
				} catch (e) {}
				if (!email) return origFetch.apply(this, arguments);
				return call("erpnext.portal_control.tenants.resolve_workspace", { email: email }).then(
					function (m) {
						if (m && m.found && m.ready && m.host && m.host !== location.hostname) {
							window.location.href =
								"https://" + m.host + "/login?email=" + encodeURIComponent(email);
							return new Promise(function () {});
						}
						if (m && m.found && !m.ready) {
							showBanner(m.message || "Your workspace is still being prepared.", false);
							return Promise.reject(new Error(m.message || "Workspace not ready"));
						}
						return origFetch.apply(window, [input, init]);
					}
				);
			};
		}
	}

	function boot() {
		simplifyLoginCopy();
		interceptLogin();
		consumeTicket();
		window.addEventListener("hashchange", simplifyLoginCopy);
		setTimeout(simplifyLoginCopy, 400);
		setTimeout(simplifyLoginCopy, 1200);
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", boot);
	} else {
		boot();
	}
})();
