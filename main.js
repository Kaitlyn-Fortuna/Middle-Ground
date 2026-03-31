const API_BASE = "http://127.0.0.1:5001/api";

const outputEl = document.getElementById("output");
const healthBtn = document.getElementById("healthBtn");
const requestPayloadEl = document.getElementById("requestPayload");
const buildPayloadBtn = document.getElementById("buildPayloadBtn");
const rankBtn = document.getElementById("rankBtn");
const maxFlightTimeEl = document.getElementById("max-flight-time");
const maxFlightTimeValueEl = document.getElementById("max-flight-time-value");
const resultsListEl = document.getElementById("resultsList");
const apiKeyInputEl = document.getElementById("apiKeyInput");
const submitBtn = document.getElementById("submitBtn");
const resetBtn = document.getElementById("resetBtn");

let submittedApiKey = "";
let hasSubmittedApiKey = false;
let isEditingApiKey = false;

function getApiKeyDraft() {
  return (apiKeyInputEl?.value || "").trim();
}

function isApiKeyChanged() {
  return getApiKeyDraft() !== submittedApiKey;
}

function updateApiKeyButtonText() {
  if (!submitBtn || !apiKeyInputEl) return;

  if (!hasSubmittedApiKey) {
    submitBtn.textContent = getApiKeyDraft() ? "Submit" : "Paste & Submit";
    return;
  }

  if (!isEditingApiKey) {
    submitBtn.textContent = "Edit";
    return;
  }

  submitBtn.textContent = isApiKeyChanged() ? "Update" : "Cancel";
}

function syncApiKeyUI() {
  if (!apiKeyInputEl) return;
  apiKeyInputEl.disabled = hasSubmittedApiKey && !isEditingApiKey;
  if (resetBtn) {
    const showReset = hasSubmittedApiKey && !isEditingApiKey;
    resetBtn.classList.toggle("hidden", !showReset);
  }
  updateApiKeyButtonText();
}

async function pasteFromClipboardIfEmpty() {
  if (!apiKeyInputEl || getApiKeyDraft()) return;
  try {
    const clipboardText = await navigator.clipboard.readText();
    const trimmed = clipboardText.trim();
    if (trimmed) {
      apiKeyInputEl.value = trimmed;
    }
  } catch (error) {
    // Ignore clipboard access errors and fall back to manual typing.
  }
}

function submitApiKeyValue() {
  const value = getApiKeyDraft();
  if (!value) {
    setOutput({ error: "Please enter an API key before submitting." });
    return false;
  }

  submittedApiKey = value;
  hasSubmittedApiKey = true;
  isEditingApiKey = false;
  apiKeyInputEl.value = value;
  setOutput({ status: "ok", message: "API key submitted and locked." });
  syncApiKeyUI();
  return true;
}

function enterApiKeyEditMode() {
  isEditingApiKey = true;
  syncApiKeyUI();
  apiKeyInputEl.focus();
  apiKeyInputEl.setSelectionRange(apiKeyInputEl.value.length, apiKeyInputEl.value.length);
}

function cancelApiKeyEdit() {
  isEditingApiKey = false;
  apiKeyInputEl.value = submittedApiKey;
  syncApiKeyUI();
}

function resetApiKeyState() {
  submittedApiKey = "";
  hasSubmittedApiKey = false;
  isEditingApiKey = false;
  if (apiKeyInputEl) {
    apiKeyInputEl.value = "";
  }
  setOutput({ status: "ok", message: "API key reset." });
  syncApiKeyUI();
}

async function handleApiKeySubmitButtonClick() {
  if (!apiKeyInputEl || !submitBtn) return;

  if (!hasSubmittedApiKey) {
    await pasteFromClipboardIfEmpty();
    submitApiKeyValue();
    return;
  }

  if (!isEditingApiKey) {
    enterApiKeyEditMode();
    return;
  }

  if (!isApiKeyChanged()) {
    cancelApiKeyEdit();
    return;
  }

  submitApiKeyValue();
}

function setOutput(data) {
  outputEl.textContent = JSON.stringify(data, null, 2);
}

function toPercent(value) {
  if (typeof value !== "number") return "N/A";
  return `${Math.round(value * 100)}%`;
}

function renderCombinedResults(data) {
  const rows = Array.isArray(data?.results) ? data.results : [];
  if (rows.length === 0) {
    resultsListEl.innerHTML = '<p class="empty-results">No results found for this filter set.</p>';
    return;
  }

  resultsListEl.innerHTML = rows
    .map(
      (row) => `
        <article class="result-card">
          <div class="result-head">
            <div class="route">#${row.rank} ${row.departure_iata} → ${row.arrival_iata}</div>
            <div class="score-total">Total: ${toPercent(row.percent_match_total)}</div>
          </div>
          <div class="meta">
            Flight ${row.flight_iata || "N/A"} • Airline ${row.airline_iata || "N/A"} •
            Status ${row.flight_status || "N/A"} • Flight Time ${row.flight_time_hours ?? "N/A"}h
          </div>
          <div class="score-breakdown">
            <span>Airport: <strong>${toPercent(row.percent_match_airport)}</strong></span>
            <span>Flight: <strong>${toPercent(row.percent_match_flight)}</strong></span>
            <span>Total: <strong>${toPercent(row.percent_match_total)}</strong></span>
          </div>
        </article>
      `
    )
    .join("");
}

function getCheckedValues(pairs) {
  return pairs
    .filter(([id]) => {
      const el = document.getElementById(id);
      return el && el.checked;
    })
    .map(([, value]) => value);
}

function buildFiltersPayload() {
  return {
    weather_preferences: getCheckedValues([
      ["weather-hot", "hot"],
      ["weather-warm", "warm"],
      ["weather-mild", "mild"],
      ["weather-cool", "cool"],
      ["weather-cold", "cold"],
    ]),
    conditions_preferences: getCheckedValues([
      ["conditions-sunny", "sunny"],
      ["conditions-dry", "dry"],
      ["conditions-wet", "wet"],
      ["conditions-low-humidity", "low humidity"],
      ["conditions-high-humidity", "high humidity"],
    ]),
    geography_preferences: getCheckedValues([
      ["geography-coastal", "coastal"],
      ["geography-beach", "beach"],
      ["geography-urban", "urban"],
      ["geography-mountainous", "mountainous"],
    ]),
    max_flight_time: Number(maxFlightTimeEl.value),
  };
}

function updatePayloadPreview() {
  const payload = buildFiltersPayload();
  requestPayloadEl.textContent = JSON.stringify(payload, null, 2);
}

async function callApi(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.message || data.error || "Request failed");
  }

  return data;
}

healthBtn.addEventListener("click", async () => {
  try {
    const data = await callApi("/health");
    setOutput(data);
  } catch (error) {
    setOutput({ error: error.message });
  }
});

buildPayloadBtn.addEventListener("click", () => {
  updatePayloadPreview();
});

maxFlightTimeEl.addEventListener("input", () => {
  maxFlightTimeValueEl.textContent = `${maxFlightTimeEl.value}h`;
  updatePayloadPreview();
});

rankBtn.addEventListener("click", async () => {
  const payload = buildFiltersPayload();
  updatePayloadPreview();

  try {
    const data = await callApi("/rank-combined?limit=25", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    setOutput(data);
    renderCombinedResults(data);
  } catch (error) {
    setOutput({ error: error.message });
    resultsListEl.innerHTML = `<p class="empty-results">Error: ${error.message}</p>`;
  }
});

apiKeyInputEl?.addEventListener("input", () => {
  updateApiKeyButtonText();
});

submitBtn?.addEventListener("click", async () => {
  await handleApiKeySubmitButtonClick();
});

resetBtn?.addEventListener("click", () => {
  resetApiKeyState();
});

maxFlightTimeValueEl.textContent = `${maxFlightTimeEl.value}h`;
updatePayloadPreview();
syncApiKeyUI();
