import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const TENANT = process.env.VITE_API_TARGET || "https://sultan.65.1.92.180.sslip.io";
const CONTROL = process.env.VITE_CONTROL_TARGET || "https://65.1.92.180.sslip.io";

export default defineConfig({
	plugins: [react(), tailwindcss()],
	server: {
		port: 5174,
		host: "0.0.0.0",
		proxy: {
			"/control": {
				target: CONTROL,
				changeOrigin: true,
				secure: false,
				cookieDomainRewrite: "",
				rewrite: (p) => p.replace(/^\/control/, "") || "/",
			},
			"^/(api|assets|files|private|login|start)": {
				target: TENANT,
				changeOrigin: true,
				secure: false,
				cookieDomainRewrite: "",
			},
		},
	},
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
	},
	build: {
		outDir: "dist",
		emptyOutDir: true,
		target: "es2018",
	},
});
