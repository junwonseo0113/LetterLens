// Same-origin /api by default (proxied by Vite to the backend; see
// vite.config.js). Set VITE_API_BASE_URL to call a backend directly.
const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

// Fired on any 401 so the app can drop an expired or revoked session.
export const UNAUTHORIZED_EVENT = "letterlens:unauthorized";

async function handleResponse(response) {
  if (!response.ok) {
    let detail = response.statusText;
    let detailZh = "";
    let fromServer = false;
    let retryable = response.status >= 500;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        detail = body.detail;
        fromServer = true;
      }
      detailZh = body.detail_zh || "";
      if (typeof body.retryable === "boolean") retryable = body.retryable;
    } catch {
      // response had no JSON body -- keep statusText
    }
    if (response.status === 401) window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    const error = new Error(detail);
    error.status = response.status;
    error.detailZh = detailZh;
    error.fromServer = fromServer;
    error.retryable = retryable;
    throw error;
  }
  return response.json();
}

// Pick the backend's error message in the user's language when it sent one.
export function errorText(error, language) {
  return (language === "zh" && error.detailZh) || error.message;
}

// The server's explanation of an error, if it gave one we can show (English
// or Chinese). Network failures ("Failed to fetch") return "".
export function serverDetail(error, language) {
  if (!error?.fromServer) return "";
  if (language === "zh") return error.detailZh || "";
  return language === "en" ? error.message : "";
}

function jsonRequest(method, path, body, headers = {}) {
  return fetch(`${API_BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then(handleResponse);
}

function bearer(token) {
  return { Authorization: `Bearer ${token}` };
}

export async function uploadLetter({ file, language, token }) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("language", language);
  const response = await fetch(`${API_BASE}/letters`, { method: "POST", headers: bearer(token), body: formData });
  return handleResponse(response);
}

export function fetchLetter(token, letterId, language) {
  return jsonRequest(
    "GET",
    `/letters/${letterId}?language=${encodeURIComponent(language)}`,
    undefined,
    bearer(token),
  );
}

export function answerQuestion(token, key, value) {
  return jsonRequest("POST", "/profile/answers", { key, value }, bearer(token));
}

export function fetchCurrentApplication(token, program = "MSP") {
  return jsonRequest("GET", `/applications/current?program=${program}`, undefined, bearer(token));
}

export function fetchLetters(token) {
  return jsonRequest("GET", "/letters", undefined, bearer(token));
}

export function fetchReminders(token) {
  return jsonRequest("GET", "/reminders", undefined, bearer(token));
}

export function fetchBenefits(token, language) {
  return jsonRequest("GET", `/benefits?language=${encodeURIComponent(language)}`, undefined, bearer(token));
}

export function fetchMspChecklist(token) {
  return jsonRequest("GET", "/msp-checklist", undefined, bearer(token));
}

export function fetchOnQmb(token) {
  return jsonRequest("GET", "/profile/on-qmb", undefined, bearer(token));
}

export function setOnQmb(token, onQmb) {
  return jsonRequest("POST", `/profile/on-qmb?on_qmb=${onQmb}`, undefined, bearer(token));
}

// --- sign-in ---------------------------------------------------------------

export function requestCode(phone) {
  return jsonRequest("POST", "/auth/request-code", { phone });
}

export function verifyCode(phone, code) {
  return jsonRequest("POST", "/auth/verify", { phone, code });
}

export function signOutRequest(token) {
  return jsonRequest("POST", "/auth/sign-out", undefined, bearer(token));
}

// --- applications ------------------------------------------------------------

export function startApplication(token, program = "MSP") {
  return jsonRequest("POST", "/applications", { program }, bearer(token));
}

export function answerField(token, applicationId, key, value) {
  return jsonRequest("PUT", `/applications/${applicationId}/fields/${key}`, { value }, bearer(token));
}

export async function addDocument(token, applicationId, key, file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE}/applications/${applicationId}/documents/${key}`, {
    method: "POST",
    headers: bearer(token),
    body: formData,
  });
  return handleResponse(response);
}

export function submitApplication(token, applicationId, signaturePng) {
  return jsonRequest(
    "POST",
    `/applications/${applicationId}/submit`,
    { signature_png: signaturePng, confirmed: true },
    bearer(token),
  );
}

// --- caseworker ----------------------------------------------------------------

function caseworker(key) {
  return { "X-Caseworker-Key": key };
}

export function fetchReviewQueue(key) {
  return jsonRequest("GET", "/review-queue", undefined, caseworker(key));
}

export function approveApplication(key, applicationId, note, verifiedDocuments = []) {
  return jsonRequest(
    "POST",
    `/review-queue/${applicationId}/approve`,
    { note, verified_documents: verifiedDocuments },
    caseworker(key),
  );
}

export function requestMoreInfo(key, applicationId, note) {
  return jsonRequest("POST", `/review-queue/${applicationId}/request-info`, { note }, caseworker(key));
}
