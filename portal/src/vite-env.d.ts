/// <reference types="vite/client" />

interface Window {
  frappe?: {
    boot?: Record<string, unknown>;
  };
  csrf_token?: string;
}
