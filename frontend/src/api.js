const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function handleResponse(response) {
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // response had no JSON body -- keep statusText
    }
    throw new Error(detail);
  }
  return response.json();
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

export async function setOnQmb(userId, onQmb) {
  const response = await fetch(
    `${API_BASE}/profile/on-qmb?user_id=${encodeURIComponent(userId)}&on_qmb=${onQmb}`,
    { method: "POST" },
  );
  return handleResponse(response);
}
