export class ApiError extends Error {
  status: number;
  excType?: string;
  constructor(message: string, status: number, excType?: string) {
    super(message);
    this.status = status;
    this.excType = excType;
  }
}

let csrf = "";
let controlCsrf = "";

export function getCsrf() {
  return csrf;
}

function readCsrf(html: string) {
  const m = html.match(/csrf_token\s*=\s*["']([^"']+)/);
  return m ? m[1] : "";
}

export async function refreshGuestCsrf() {
  const res = await fetch("/start", { credentials: "include" });
  const html = await res.text();
  const token = readCsrf(html);
  if (token) csrf = token;
  return csrf;
}

export async function refreshControlCsrf() {
  const res = await fetch("/control/start", { credentials: "include" });
  const html = await res.text();
  const token = readCsrf(html);
  if (token) controlCsrf = token;
  return controlCsrf;
}

async function parse(res: Response) {
  const text = await res.text();
  let data: Record<string, unknown> = {};
  try {
    data = text ? (JSON.parse(text) as Record<string, unknown>) : {};
  } catch {
    data = { _raw: text.slice(0, 240) };
  }
  const headerCsrf = res.headers.get("X-Frappe-CSRF-Token");
  if (headerCsrf) {
    if (res.url.includes("/control/")) controlCsrf = headerCsrf;
    else csrf = headerCsrf;
  }
  const excType = data.exc_type as string | undefined;
  const exception = data.exception as string | undefined;
  if (excType || exception || !res.ok) {
    const msg =
      (data._error_message as string) ||
      exception ||
      (typeof data.message === "string" ? data.message : "") ||
      `Request failed (${res.status})`;
    throw new ApiError(String(msg).replace(/<[^>]+>/g, " ").slice(0, 280), res.status, excType);
  }
  return data;
}

async function methodCall(
  url: string,
  token: string,
  params: Record<string, unknown>,
  asPost: boolean,
) {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "X-Frappe-CSRF-Token": token,
    "X-Requested-With": "XMLHttpRequest",
  };
  let res: Response;
  if (asPost) {
    const body = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined || v === null) continue;
      body.set(k, typeof v === "string" ? v : JSON.stringify(v));
    }
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    res = await fetch(url, { method: "POST", credentials: "include", headers, body });
  } else {
    const q = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined || v === null) continue;
      q.set(k, typeof v === "string" ? v : JSON.stringify(v));
    }
    const qs = q.toString();
    res = await fetch(qs ? `${url}?${qs}` : url, { credentials: "include", headers });
  }
  const data = await parse(res);
  return data.message;
}

export async function callMethod(method: string, params: Record<string, unknown> = {}, asPost = true) {
  return methodCall(`/api/method/${method}`, csrf, params, asPost);
}

export async function callControlMethod(method: string, params: Record<string, unknown> = {}) {
  return methodCall(`/control/api/method/${method}`, controlCsrf, params, true);
}

export async function login(usr: string, pwd: string) {
  const body = new URLSearchParams({ usr, pwd });
  const res = await fetch("/api/method/login", {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/x-www-form-urlencoded",
      "X-Requested-With": "XMLHttpRequest",
    },
    body,
  });
  const data = await parse(res);
  await refreshGuestCsrf();
  return data;
}

export async function logout() {
  await callMethod("logout", { _: "1" }, true);
  csrf = "";
}

export async function getList(
  doctype: string,
  fields: string[],
  extras: { filters?: unknown; limit?: number; orderBy?: string } = {},
) {
  return callMethod("frappe.client.get_list", {
    doctype,
    fields,
    filters: extras.filters || {},
    limit_page_length: extras.limit ?? 50,
    order_by: extras.orderBy || "modified desc",
  });
}

export async function getCount(doctype: string, filters: unknown = {}) {
  return callMethod("frappe.client.get_count", { doctype, filters });
}

export async function getDoc(doctype: string, name: string) {
  return callMethod("frappe.client.get", { doctype, name });
}

export async function insertDoc(doc: Record<string, unknown>) {
  return callMethod("frappe.client.insert", { doc });
}

export async function saveDoc(doc: Record<string, unknown>) {
  return callMethod("frappe.client.save", { doc });
}

export async function setValue(doctype: string, name: string, fieldname: string, value: unknown) {
  return callMethod("frappe.client.set_value", { doctype, name, fieldname, value });
}

export async function deleteDoc(doctype: string, name: string) {
  return callMethod("erpnext.portal_control.workspace.delete_document", { doctype, name });
}
