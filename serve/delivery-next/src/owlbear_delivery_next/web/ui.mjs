// What every Delivery page shares (TD-264): the token, calls to the host and the design system's arrival.

const hash = new URLSearchParams(location.hash.slice(1));
if (hash.get("token")) {
  sessionStorage.setItem("token", hash.get("token"));
  history.replaceState(null, "", location.pathname);
}
export const token = sessionStorage.getItem("token");

export class HostDown extends Error {
  constructor() {
    super("Delivery is not running. Start it, then reload this page.");
  }
}

export class Restarted extends Error {
  constructor() {
    super("Delivery restarted at a new address. Open the link from chat or owlbear-next status.");
  }
}

// The host's error detail in words: a validation list names each field, anything else is said as given.
function said(detail) {
  if (Array.isArray(detail)) {
    return detail.map((e) => {
      const at = (e.loc ?? []).filter((p, i) => !(i === 0 && p === "body")).join(".");
      return at ? `${at}: ${e.msg}` : e.msg;
    }).join("; ");
  }
  return typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : "";
}

// One call to the host's API; GET without a body. Throws HostDown, Restarted, or an Error with the host's words.
export async function call(path, { method, body, timeout = 5000 } = {}) {
  if (!token) throw new Error("Open the URL the host printed, including #token=…");
  const init = { method: method ?? (body ? "POST" : "GET"), headers: { Authorization: `Bearer ${token}` },
    signal: AbortSignal.timeout(timeout) };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
    init.headers["Content-Type"] = "application/json";
  }
  let response;
  try {
    response = await fetch(`/api/next${path}`, init);
  } catch {
    throw new HostDown();
  }
  if (response.status === 401) throw new Restarted();
  const data = await response.json().catch(() => null);
  if (!response.ok || data === null) {
    const error = new Error(said(data?.detail) || `Delivery answered ${response.status} ${response.statusText}`);
    error.status = response.status;
    throw error;
  }
  return data;
}

// Whether the design system's components arrived within three seconds; without them the page shows plain controls.
export async function designSystem() {
  const ready = customElements.whenDefined("p-heading").then(() => true);
  const pds = await Promise.race([ready, new Promise((resolve) => setTimeout(resolve, 3000, false))]);
  if (!pds) document.documentElement.classList.add("no-pds");
  return pds;
}
