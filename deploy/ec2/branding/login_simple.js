/* Prime Ledger — plain-language helpers for login / signup */
(function () {
	function text(el, value) {
		if (el) el.textContent = value;
	}

	function simplifyLoginCopy() {
		document.querySelectorAll(".btn-login, button.btn-primary").forEach(function (btn) {
			var t = (btn.textContent || "").trim().toLowerCase();
			if (t === "continue" || t === "login" || t === "sign in") {
				btn.textContent = "Sign in";
			}
		});
		document.querySelectorAll(".btn-signup").forEach(function (btn) {
			var t = (btn.textContent || "").trim().toLowerCase();
			if (t === "sign up" || t === "register") {
				btn.textContent = "Create account";
			}
		});

		document.querySelectorAll(".for-login .page-card-head-text h4").forEach(function (h) {
			if (/sign in|login/i.test(h.textContent || "")) {
				h.textContent = "Sign in with your email";
			}
		});
		document.querySelectorAll(".for-signup .page-card-head-text h4").forEach(function (h) {
			h.textContent = "Create your free account";
		});
		document.querySelectorAll(".for-forgot .page-card-head-text h4").forEach(function (h) {
			h.textContent = "Reset your password";
		});

		// Soften field labels where present
		document.querySelectorAll("label, .form-label").forEach(function (lab) {
			var t = (lab.textContent || "").trim();
			if (/^email$/i.test(t) || /email or username/i.test(t)) {
				lab.textContent = "Your email";
			}
			if (/^password$/i.test(t)) {
				lab.textContent = "Your password";
			}
			if (/full name/i.test(t)) {
				lab.textContent = "Your full name";
			}
		});

		// One-line tip under login card (once)
		var login = document.querySelector(".for-login .page-card");
		if (login && !login.querySelector(".pl-easy-tip")) {
			var tip = document.createElement("p");
			tip.className = "pl-easy-tip";
			tip.textContent =
				"New here? Tap Sign up below. After you create an account, check your email, then come back and sign in.";
			login.appendChild(tip);
		}

		var signup = document.querySelector(".for-signup .page-card");
		if (signup && !signup.querySelector(".pl-easy-tip")) {
			var tip2 = document.createElement("p");
			tip2.className = "pl-easy-tip";
			tip2.textContent =
				"Step 1: enter your name and email. Step 2: open the email we send you. Step 3: come back here and sign in.";
			signup.appendChild(tip2);
		}
	}

	function boot() {
		simplifyLoginCopy();
		// Frappe swaps sections via hash — re-run on navigation
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
