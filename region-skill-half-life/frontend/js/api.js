const API_BASE = "http://127.0.0.1:8000";
const IS_DEV = ["127.0.0.1", "localhost"].includes(window.location.hostname);

function devLog(...args) {
  if (IS_DEV) {
    console.log(...args);
  }
}

async function callApi(endpoint, options = {}) {
  devLog("Calling API:", endpoint);
  let response;

  try {
    response = await fetch(`${API_BASE}${endpoint}`, options);
  } catch (error) {
    throw new Error("Backend unavailable. Please verify local API server.");
  }

  return parseResponse(response);
}

async function parseResponse(response) {
  if (!response.ok) {
    const errorPayload = await response.json().catch(() => ({}));
    throw new Error(errorPayload.detail || "Request failed");
  }
  return response;
}

export async function fetchRegions() {
  const okResponse = await callApi("/regions");
  return okResponse.json();
}

export async function fetchCountries() {
  const okResponse = await callApi("/countries");
  return okResponse.json();
}

export async function getCountries() {
  return fetchCountries();
}

export async function getCities(country) {
  const okResponse = await callApi(`/cities/${encodeURIComponent(country)}`);
  return okResponse.json();
}

export async function getSkills() {
  const okResponse = await callApi("/skills");
  return okResponse.json();
}

export async function fetchAnalytics(country, city, skill, experience = "Mid", time_horizon = "1y") {
  if (arguments.length === 0) {
    throw new Error("country, city, and skill are required for analytics.");
  }

  const query = new URLSearchParams({ country, city, skill, experience, time_horizon });
  const okResponse = await callApi(`/analytics?${query.toString()}`);
  return okResponse.json();
}

export const getAnalytics = fetchAnalytics;

export async function fetchReportPreview(payload) {
  const okResponse = await callApi("/report/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return okResponse.json();
}

export async function compareCities(payload) {
  const okResponse = await callApi("/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return okResponse.json();
}

export async function downloadReport(payload) {
  const okResponse = await callApi("/report", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  const blob = await okResponse.blob();

  const disposition = okResponse.headers.get("Content-Disposition") || "";
  const matched = disposition.match(/filename="?([^\"]+)"?/i);
  const fileName = matched?.[1] || "skill_half_life_report.pdf";

  return { blob, fileName };
}

export const generateReport = downloadReport;

export async function sendChatMessage(payload) {
  const okResponse = await callApi("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return okResponse.json();
}

export async function sendVoicePayload(payload) {
  const okResponse = await callApi("/voice", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return okResponse.json();
}

export async function runSimulationRefresh() {
  const okResponse = await callApi("/simulation/refresh");
  return okResponse.json();
}

export async function pingBackend() {
  const okResponse = await callApi("/");
  return okResponse.json();
}
