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
const departureDateEl = document.getElementById("departure-date");
const returnDateEl = document.getElementById("return-date");
const airportInputEl = document.getElementById("airport-input");
const airportSuggestionsEl = document.getElementById("airport-suggestions");
const airportChipsEl = document.getElementById("airport-chips");

let submittedApiKey = "";
let hasSubmittedApiKey = false;
let isEditingApiKey = false;
let airportCatalog = [];
let airportMatches = [];
let selectedAirports = [];
let highlightedAirportIndex = 0;

const AIRPORT_COMMIT_KEYS = new Set(["Enter", "Tab", ",", ".", "\"", " "]);

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

function normalizeSearchText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function compactSearchText(value) {
  return normalizeSearchText(value).replace(/\s+/g, "");
}

function isSubsequence(query, target) {
  if (!query) return false;
  let q = 0;
  let t = 0;
  while (q < query.length && t < target.length) {
    if (query[q] === target[t]) q += 1;
    t += 1;
  }
  return q === query.length;
}

function makeAirportRecord(raw) {
  const iataCode = String(raw?.iata_code || "").trim().toUpperCase();
  const name = String(raw?.name || "").trim();
  const municipality = String(raw?.municipality || "").trim();
  const isoRegion = String(raw?.iso_region || "").trim();
  const combined = `${iataCode} ${name} ${municipality} ${isoRegion}`.trim();

  return {
    iata_code: iataCode,
    name,
    municipality,
    iso_region: isoRegion,
    search_name: normalizeSearchText(name),
    search_city: normalizeSearchText(municipality),
    search_all: normalizeSearchText(combined),
    compact_all: compactSearchText(combined),
  };
}

function scoreAirportMatch(airport, queryNormalized, queryCompact) {
  if (!queryNormalized) return 0;

  let score = 0;
  const iata = airport.iata_code.toLowerCase();

  if (iata === queryCompact) score = 140;
  else if (iata.startsWith(queryCompact)) score = 125;

  if (airport.search_name.startsWith(queryNormalized) || airport.search_city.startsWith(queryNormalized)) {
    score = Math.max(score, 115);
  } else if (
    airport.search_name.includes(queryNormalized) ||
    airport.search_city.includes(queryNormalized)
  ) {
    score = Math.max(score, 100);
  } else if (airport.search_all.includes(queryNormalized)) {
    score = Math.max(score, 90);
  }

  if (queryCompact && isSubsequence(queryCompact, airport.compact_all)) {
    score = Math.max(score, 75);
  }

  return score;
}

function formatAirportLabel(airport) {
  const cityPart = airport.municipality ? ` - ${airport.municipality}` : "";
  return `${airport.name}${cityPart}`;
}

function renderAirportChips() {
  if (!airportChipsEl) return;

  airportChipsEl.innerHTML = selectedAirports
    .map(
      (airport) => `
      <span class="airport-chip">
        ${airport.iata_code}
        <button type="button" class="remove-airport-btn" data-iata="${airport.iata_code}" aria-label="Remove ${airport.iata_code}">×</button>
      </span>
    `
    )
    .join("");
}

function renderAirportSuggestions() {
  if (!airportSuggestionsEl) return;

  if (airportMatches.length === 0) {
    airportSuggestionsEl.innerHTML = "";
    airportSuggestionsEl.classList.add("hidden");
    return;
  }

  airportSuggestionsEl.innerHTML = airportMatches
    .map(
      (airport, index) => `
      <li class="airport-suggestion ${index === highlightedAirportIndex ? "active" : ""}" data-iata="${airport.iata_code}" data-index="${index}">
        <span class="airport-suggestion-code">${airport.iata_code}</span>
        <span class="airport-suggestion-text">${formatAirportLabel(airport)}</span>
      </li>
    `
    )
    .join("");

  airportSuggestionsEl.classList.remove("hidden");
}

function updateAirportMatches() {
  if (!airportInputEl) return;

  const queryNormalized = normalizeSearchText(airportInputEl.value);
  if (!queryNormalized) {
    airportMatches = [];
    renderAirportSuggestions();
    return;
  }

  const selectedIataSet = new Set(selectedAirports.map((airport) => airport.iata_code));
  const queryCompact = queryNormalized.replace(/\s+/g, "");

  airportMatches = airportCatalog
    .filter((airport) => !selectedIataSet.has(airport.iata_code))
    .map((airport) => ({
      airport,
      score: scoreAirportMatch(airport, queryNormalized, queryCompact),
    }))
    .filter((item) => item.score > 0)
    .sort(
      (a, b) =>
        b.score - a.score ||
        a.airport.name.localeCompare(b.airport.name, undefined, { sensitivity: "base" })
    )
    .slice(0, 8)
    .map((item) => item.airport);

  highlightedAirportIndex = 0;
  renderAirportSuggestions();
}

function addAirportSelection(airport) {
  if (!airport) return false;
  if (selectedAirports.some((item) => item.iata_code === airport.iata_code)) return false;

  selectedAirports = [...selectedAirports, airport];
  renderAirportChips();
  updatePayloadPreview();
  return true;
}

function selectAirportAndResetInput(airport) {
  const added = addAirportSelection(airport);
  if (!added || !airportInputEl) return false;

  airportInputEl.value = "";
  airportInputEl.focus();
  updateAirportMatches();
  return true;
}

function commitHighlightedAirport() {
  if (airportMatches.length === 0) return false;
  const index = Math.min(highlightedAirportIndex, airportMatches.length - 1);
  const airport = airportMatches[index] || airportMatches[0];
  return selectAirportAndResetInput(airport);
}

function removeSelectedAirport(iataCode) {
  const normalized = String(iataCode || "").toUpperCase().trim();
  if (!normalized) return;

  selectedAirports = selectedAirports.filter((airport) => airport.iata_code !== normalized);
  renderAirportChips();
  updateAirportMatches();
  updatePayloadPreview();
}

async function loadAirportCatalog() {
  if (!airportInputEl) return;

  airportInputEl.disabled = true;
  airportInputEl.placeholder = "Loading airports...";

  try {
    const data = await callApi("/airports");
    const rows = Array.isArray(data?.results) ? data.results : [];

    airportCatalog = rows
      .map(makeAirportRecord)
      .filter((airport) => airport.iata_code && airport.name);

    airportInputEl.disabled = false;
    airportInputEl.placeholder = airportCatalog.length
      ? "Type airport, IATA, or city..."
      : "No airports available";
  } catch (error) {
    airportCatalog = [];
    airportInputEl.disabled = true;
    airportInputEl.placeholder = "Airport list unavailable";
    console.error("Unable to load airports:", error);
  }
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
    departure_date: departureDateEl?.value || null,
    return_date: returnDateEl?.value || null,
    airports: selectedAirports.map((airport) => airport.iata_code),
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

departureDateEl?.addEventListener("input", () => {
  updatePayloadPreview();
});

returnDateEl?.addEventListener("input", () => {
  updatePayloadPreview();
});

airportInputEl?.addEventListener("input", () => {
  updateAirportMatches();
});

airportInputEl?.addEventListener("focus", () => {
  updateAirportMatches();
});

airportInputEl?.addEventListener("blur", () => {
  window.setTimeout(() => {
    if (airportSuggestionsEl) {
      airportSuggestionsEl.classList.add("hidden");
    }
  }, 120);
});

airportInputEl?.addEventListener("keydown", (event) => {
  if (event.key === "ArrowDown") {
    if (airportMatches.length > 0) {
      highlightedAirportIndex = (highlightedAirportIndex + 1) % airportMatches.length;
      renderAirportSuggestions();
    }
    event.preventDefault();
    return;
  }

  if (event.key === "ArrowUp") {
    if (airportMatches.length > 0) {
      highlightedAirportIndex =
        (highlightedAirportIndex - 1 + airportMatches.length) % airportMatches.length;
      renderAirportSuggestions();
    }
    event.preventDefault();
    return;
  }

  if (event.key === "Backspace" && !airportInputEl.value && selectedAirports.length > 0) {
    removeSelectedAirport(selectedAirports[selectedAirports.length - 1].iata_code);
    event.preventDefault();
    return;
  }

  if (AIRPORT_COMMIT_KEYS.has(event.key)) {
    const accepted = commitHighlightedAirport();
    if (accepted) {
      event.preventDefault();
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();
    }
  }
});

airportSuggestionsEl?.addEventListener("mousedown", (event) => {
  event.preventDefault();
});

airportSuggestionsEl?.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;

  const row = target.closest(".airport-suggestion");
  if (!row) return;

  const iataCode = row.getAttribute("data-iata");
  if (!iataCode) return;

  const airport = airportCatalog.find((item) => item.iata_code === iataCode);
  if (!airport) return;

  selectAirportAndResetInput(airport);
});

airportChipsEl?.addEventListener("click", (event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;

  const button = target.closest(".remove-airport-btn");
  if (!button) return;

  const iataCode = button.getAttribute("data-iata");
  removeSelectedAirport(iataCode);
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
loadAirportCatalog();
