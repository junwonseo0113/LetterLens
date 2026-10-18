const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function handleResponse(response) {
  if (!response.ok) {
    let detail = response.statusText;
    let detailZh = "";
    try {
      const body = await response.json();
      detail = body.detail || detail;
      detailZh = body.detail_zh || "";
    } catch {
      // response had no JSON body -- keep statusText
    }
    const error = new Error(detail);
    error.status = response.status;
    error.detailZh = detailZh;
    throw error;
  }
  return response.json();
}

// Pick the backend's error message in the user's language when it sent one.
export function errorText(error, language) {
  return (language === "zh" && error.detailZh) || error.message;
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

export async function uploadLetter({ file, language, userId }) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("language", language);
  formData.append("user_id", userId);
  const response = await fetch(`${API_BASE}/letters`, { method: "POST", body: formData });
  return handleResponse(response);
}

export async function fetchLetters(userId) {
  const response = await fetch(`${API_BASE}/letters?user_id=${encodeURIComponent(userId)}`);
  return handleResponse(response);
}

export async function fetchReminders(userId) {
  const response = await fetch(`${API_BASE}/reminders?user_id=${encodeURIComponent(userId)}`);
  return handleResponse(response);
}

export async function fetchBenefits(userId, language) {
  const response = await fetch(
    `${API_BASE}/benefits?user_id=${encodeURIComponent(userId)}&language=${encodeURIComponent(language)}`
  );
  return handleResponse(response);
}

export async function fetchMspChecklist(userId) {
  const response = await fetch(`${API_BASE}/msp-checklist?user_id=${encodeURIComponent(userId)}`);
  return handleResponse(response);
}

export async function fetchOnQmb(userId) {
  const response = await fetch(
    `${API_BASE}/profile/on-qmb?user_id=${encodeURIComponent(userId)}`,
  );
  return handleResponse(response);
}

export async function setOnQmb(userId, onQmb) {
  const response = await fetch(
    `${API_BASE}/profile/on-qmb?user_id=${encodeURIComponent(userId)}&on_qmb=${onQmb}`,
    { method: "POST" },
  );
  return handleResponse(response);
}

// --- sign-in ---------------------------------------------------------------

export function requestCode(phone) {
  return jsonRequest("POST", "/auth/request-code", { phone });
}

export function verifyCode(phone, code) {
  return jsonRequest("POST", "/auth/verify", { phone, code });
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

export function approveApplication(key, applicationId, note) {
  return jsonRequest("POST", `/review-queue/${applicationId}/approve`, { note }, caseworker(key));
}

export function requestMoreInfo(key, applicationId, note) {
  return jsonRequest("POST", `/review-queue/${applicationId}/request-info`, { note }, caseworker(key));
}
