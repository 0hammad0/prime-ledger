const APEX = "65.1.92.180.sslip.io";

export function isTenantHost(hostname = window.location.hostname) {
  return hostname.endsWith(`.${APEX}`) && hostname !== APEX;
}

export function isControlHost(hostname = window.location.hostname) {
  return hostname === APEX || hostname === "65.1.92.180" || hostname === "localhost" || hostname === "127.0.0.1";
}

export function apexOrigin() {
  return `https://${APEX}`;
}
