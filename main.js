const API_BASE = "http://127.0.0.1:5001/api";

const outputEl = document.getElementById("output");
const healthBtn = document.getElementById("healthBtn");
const requestPayloadEl = document.getElementById("requestPayload");
const rankBtn = document.getElementById("rankBtn");
const resetSearchBtn = document.getElementById("resetSearchBtn");
const maxFlightTimeEl = document.getElementById("max-flight-time");
const maxFlightTimeValueEl = document.getElementById("max-flight-time-value");
const maxFlightCostEl = document.getElementById("max-flight-cost");
const maxFlightCostValueEl = document.getElementById("max-flight-cost-value");
const resultsListEl = document.getElementById("resultsList");
const apiKeyInputEl = document.getElementById("apiKeyInput");
const submitBtn = document.getElementById("submitBtn");
const resetBtn = document.getElementById("resetBtn");
const departureDateEl = document.getElementById("departure-date");
const returnDateEl = document.getElementById("return-date");
const airportInputEl = document.getElementById("airport-input");
const airportSuggestionsEl = document.getElementById("airport-suggestions");
const airportChipsEl = document.getElementById("airport-chips");

const WEATHER_OPTIONS = [
  ["weather-hot", "hot"],
  ["weather-warm", "warm"],
  ["weather-mild", "mild"],
  ["weather-cool", "cool"],
  ["weather-cold", "cold"],
];
const CONDITIONS_OPTIONS = [
  ["conditions-sunny", "sunny"],
  ["conditions-dry", "dry"],
  ["conditions-wet", "wet"],
  ["conditions-low-humidity", "low humidity"],
  ["conditions-high-humidity", "high humidity"],
];
const GEOGRAPHY_OPTIONS = [
  ["geography-coastal", "coastal"],
  ["geography-beach", "beach"],
  ["geography-urban", "urban"],
  ["geography-mountainous", "mountainous"],
];
const WEATHER_ID_ORDER = WEATHER_OPTIONS.map(([id]) => id);
const WEATHER_ID_TO_INDEX = new Map(WEATHER_ID_ORDER.map((id, index) => [id, index]));
const FILTER_CHECKBOX_IDS = [...WEATHER_OPTIONS, ...CONDITIONS_OPTIONS, ...GEOGRAPHY_OPTIONS].map(
  ([id]) => id
);

const AIRPORT_COMMIT_KEYS = new Set(["Enter", "Tab", ",", ".", "\"", " "]);
const STORAGE_KEYS = {
  api: "middleground.apiKeyState.v1",
  ui: "middleground.uiState.v1",
  results: "middleground.resultsState.v1",
};
const DEFAULT_OUTPUT_TEXT = "API responses are now logged to the browser console.";
const DEFAULT_RESULTS_HTML =
  '<p class="empty-results">Choose filters and click Optimize Travel to load results.</p>';
const DEFAULT_MAX_FLIGHT_TIME = Number(maxFlightTimeEl?.defaultValue || 6);
const DEFAULT_MAX_FLIGHT_COST = Number(maxFlightCostEl?.defaultValue || 1000);

let submittedApiKey = "";
let hasSubmittedApiKey = false;
let isEditingApiKey = false;

let airportCatalog = [];
let airportMatches = [];
let selectedAirports = [];
let highlightedAirportIndex = 0;

let persistedOutputData = null;
let persistedCombinedData = null;
let isRankingInProgress = false;
const DEFAULT_RANK_BUTTON_TEXT = rankBtn?.textContent?.trim() || "Optimize Travel";

function summarizeHeaders(headersValue) {
  const headers =
    headersValue instanceof Headers
      ? Object.fromEntries(headersValue.entries())
      : headersValue && typeof headersValue === "object"
      ? { ...headersValue }
      : {};

  if (typeof headers["X-API-Key"] === "string") {
    headers["X-API-Key"] = "<submitted-in-ui>";
  }
  return headers;
}

function logFrontend(stage, details = undefined) {
  if (details === undefined) {
    console.log(`[MiddleGround] ${stage}`);
    return;
  }
  console.log(`[MiddleGround] ${stage}`, details);
}

function readStorageJSON(key) {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return typeof parsed === "object" && parsed !== null ? parsed : null;
  } catch (_error) {
    return null;
  }
}

function writeStorageJSON(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch (_error) {
    // Ignore storage quota/privacy mode errors.
  }
}

function removeStorage(key) {
  try {
    window.localStorage.removeItem(key);
  } catch (_error) {
    // Ignore storage errors.
  }
}

function sanitizeAirportSelection(value) {
  if (!value || typeof value !== "object") return null;
  const iataCode = String(value.iata_code || "")
    .trim()
    .toUpperCase();
  if (!iataCode) return null;
  return {
    iata_code: iataCode,
    name: String(value.name || "").trim(),
    municipality: String(value.municipality || "").trim(),
    iso_region: String(value.iso_region || "").trim(),
  };
}

function saveApiKeyState() {
  writeStorageJSON(STORAGE_KEYS.api, {
    submittedApiKey,
    hasSubmittedApiKey,
  });
}

function loadApiKeyState() {
  const state = readStorageJSON(STORAGE_KEYS.api);
  if (!state) return;

  const loadedKey = typeof state.submittedApiKey === "string" ? state.submittedApiKey.trim() : "";
  const loadedSubmitted = Boolean(state.hasSubmittedApiKey && loadedKey);

  submittedApiKey = loadedKey;
  hasSubmittedApiKey = loadedSubmitted;
  isEditingApiKey = false;

  if (apiKeyInputEl) {
    apiKeyInputEl.value = loadedKey;
  }
}

function saveUiState() {
  const checkedIds = FILTER_CHECKBOX_IDS.filter((id) => {
    const el = document.getElementById(id);
    return Boolean(el?.checked);
  });

  writeStorageJSON(STORAGE_KEYS.ui, {
    departure_date: departureDateEl?.value || "",
    return_date: returnDateEl?.value || "",
    airports: selectedAirports,
    max_flight_time: Number(maxFlightTimeEl?.value || DEFAULT_MAX_FLIGHT_TIME),
    max_flight_cost: Number(maxFlightCostEl?.value || DEFAULT_MAX_FLIGHT_COST),
    checked_ids: checkedIds,
  });
}

function getSelectedWeatherIds() {
  return WEATHER_ID_ORDER.filter((id) => {
    const el = document.getElementById(id);
    return Boolean(el?.checked);
  });
}

function isWeatherSelectionValid(selectedWeatherIds) {
  if (selectedWeatherIds.length > 3) return false;
  if (selectedWeatherIds.length <= 1) return true;

  const selectedIndexes = selectedWeatherIds
    .map((id) => WEATHER_ID_TO_INDEX.get(id))
    .filter((value) => typeof value === "number")
    .sort((a, b) => a - b);

  for (let i = 1; i < selectedIndexes.length; i += 1) {
    if (selectedIndexes[i] !== selectedIndexes[i - 1] + 1) {
      return false;
    }
  }

  return true;
}

function normalizeWeatherSelection() {
  const selectedIndexes = getSelectedWeatherIds()
    .map((id) => WEATHER_ID_TO_INDEX.get(id))
    .filter((value) => typeof value === "number")
    .sort((a, b) => a - b);

  if (selectedIndexes.length === 0) return false;
  if (isWeatherSelectionValid(getSelectedWeatherIds())) return false;

  const runs = [];
  let currentRun = [selectedIndexes[0]];

  for (let i = 1; i < selectedIndexes.length; i += 1) {
    const indexValue = selectedIndexes[i];
    if (indexValue === currentRun[currentRun.length - 1] + 1) {
      currentRun.push(indexValue);
    } else {
      runs.push(currentRun);
      currentRun = [indexValue];
    }
  }
  runs.push(currentRun);

  runs.sort((a, b) => b.length - a.length || a[0] - b[0]);
  const chosen = runs[0].slice(0, 3);
  const chosenSet = new Set(chosen.map((indexValue) => WEATHER_ID_ORDER[indexValue]));

  WEATHER_ID_ORDER.forEach((id) => {
    const checkbox = document.getElementById(id);
    if (checkbox) {
      checkbox.checked = chosenSet.has(id);
    }
  });

  return true;
}

function enforceWeatherSelectionRules(changedId = null) {
  const selectedIds = getSelectedWeatherIds();
  if (isWeatherSelectionValid(selectedIds)) return false;

  if (changedId) {
    const changedCheckbox = document.getElementById(changedId);
    if (changedCheckbox?.checked) {
      changedCheckbox.checked = false;
      return true;
    }
  }

  return normalizeWeatherSelection();
}

function loadUiState() {
  const state = readStorageJSON(STORAGE_KEYS.ui);
  if (!state) return;

  if (departureDateEl && typeof state.departure_date === "string") {
    departureDateEl.value = state.departure_date;
  }

  if (returnDateEl && typeof state.return_date === "string") {
    returnDateEl.value = state.return_date;
  }

  if (maxFlightTimeEl && Number.isFinite(Number(state.max_flight_time))) {
    maxFlightTimeEl.value = String(Number(state.max_flight_time));
  }

  if (maxFlightCostEl && Number.isFinite(Number(state.max_flight_cost))) {
    maxFlightCostEl.value = String(Number(state.max_flight_cost));
  }

  const checkedSet = new Set(Array.isArray(state.checked_ids) ? state.checked_ids : []);
  FILTER_CHECKBOX_IDS.forEach((id) => {
    const checkbox = document.getElementById(id);
    if (checkbox) {
      checkbox.checked = checkedSet.has(id);
    }
  });

  const loadedAirports = Array.isArray(state.airports)
    ? state.airports.map(sanitizeAirportSelection).filter(Boolean)
    : [];
  selectedAirports = loadedAirports;
  normalizeWeatherSelection();
  renderAirportChips();
}

function saveResultsState() {
  writeStorageJSON(STORAGE_KEYS.results, {
    output_data: persistedOutputData,
    combined_data: persistedCombinedData,
  });
}

function loadResultsState() {
  const state = readStorageJSON(STORAGE_KEYS.results);
  if (!state) {
    if (outputEl) {
      outputEl.textContent = DEFAULT_OUTPUT_TEXT;
    }
    resultsListEl.innerHTML = DEFAULT_RESULTS_HTML;
    return;
  }

  if (state.output_data !== undefined && state.output_data !== null) {
    setOutput(state.output_data, { persist: false });
    persistedOutputData = state.output_data;
  } else {
    if (outputEl) {
      outputEl.textContent = DEFAULT_OUTPUT_TEXT;
    }
  }

  if (state.combined_data && Array.isArray(state.combined_data.results)) {
    renderCombinedResults(state.combined_data, { persist: false });
    persistedCombinedData = state.combined_data;
  } else {
    resultsListEl.innerHTML = DEFAULT_RESULTS_HTML;
  }
}

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
  } catch (_error) {
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
  saveApiKeyState();
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
  saveApiKeyState();
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

function setOutput(data, { persist = true } = {}) {
  if (outputEl) {
    outputEl.textContent = JSON.stringify(data, null, 2);
  }
  console.log("[MiddleGround API Response]", data);
  if (!persist) return;

  persistedOutputData = data;
  saveResultsState();
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
      <li class="airport-suggestion ${index === highlightedAirportIndex ? "active" : ""}" data-iata="${airport.iata_code}">
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

  selectedAirports = [...selectedAirports, sanitizeAirportSelection(airport)].filter(Boolean);
  renderAirportChips();
  saveUiState();
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
  saveUiState();
  updatePayloadPreview();
}

async function loadAirportCatalog() {
  if (!airportInputEl) return;

  airportInputEl.disabled = true;
  airportInputEl.placeholder = "Loading airports...";
  logFrontend("Loading airport catalog");

  try {
    const data = await callApi("/airports");
    const rows = Array.isArray(data?.results) ? data.results : [];

    airportCatalog = rows
      .map(makeAirportRecord)
      .filter((airport) => airport.iata_code && airport.name);

    const airportsByIata = new Map(airportCatalog.map((airport) => [airport.iata_code, airport]));
    selectedAirports = selectedAirports
      .map((airport) => airportsByIata.get(airport.iata_code) || airport)
      .map(sanitizeAirportSelection)
      .filter(Boolean);
    renderAirportChips();
    saveUiState();
    updatePayloadPreview();

    airportInputEl.disabled = false;
    airportInputEl.placeholder = airportCatalog.length
      ? "Type airport, IATA, or city..."
      : "No airports available";
    logFrontend("Airport catalog loaded", { count: airportCatalog.length });
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

const USD_FORMATTER = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

function toMoney(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "N/A";
  return USD_FORMATTER.format(Math.round(value));
}

function scoreToneLevel(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "na";
  if (value >= 0.85) return "high";
  if (value >= 0.65) return "mid";
  return "low";
}

function scoreToneClass(value) {
  const level = scoreToneLevel(value);
  return level === "na" ? "score-na" : `score-${level}`;
}

function toneClass(value) {
  const level = scoreToneLevel(value);
  return level === "na" ? "tone-na" : `tone-${level}`;
}

function formatDateTime(value) {
  if (!value || typeof value !== "string") return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

function formatDurationHours(value) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) return "";
  const totalMinutes = Math.round(value * 60);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours > 0 && minutes > 0) {
    return `${hours} hour${hours === 1 ? "" : "s"} ${minutes} minute${minutes === 1 ? "" : "s"}`;
  }
  if (hours > 0) {
    return `${hours} hour${hours === 1 ? "" : "s"}`;
  }
  return `${minutes} minute${minutes === 1 ? "" : "s"}`;
}

function formatHoursLabel(value) {
  if (value === null || value === undefined) return "";
  const num = Number(value);
  if (!Number.isFinite(num)) return "";
  return `${num} hour${num === 1 ? "" : "s"}`;
}

function toDisplayText(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value.trim();
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return String(value);
}

function renderDetailRow(label, value, extraClass = "") {
  const text = toDisplayText(value);
  if (!text) return "";
  return `
    <div class="flight-kv ${extraClass}">
      <span class="flight-k">${label}</span>
      <span class="flight-v">${text}</span>
    </div>
  `;
}

function renderFlightScoreCard(title, filterValue, actualValue, scoreValue) {
  const filterText = toDisplayText(filterValue);
  const actualText = toDisplayText(actualValue);
  const hasScore = typeof scoreValue === "number" && Number.isFinite(scoreValue);
  if (!filterText && !actualText && !hasScore) return "";

  return `
    <div class="flight-kv flight-score-card">
      <div class="flight-score-head">
        <span class="flight-score-title">${title}</span>
        ${hasScore ? `<span class="airport-breakdown-score ${scoreToneClass(scoreValue)}">${toPercent(scoreValue)}</span>` : ""}
      </div>
      ${filterText ? `<div class="airport-breakdown-meta"><strong>Filter:</strong> ${filterText}</div>` : ""}
      ${actualText ? `<div class="airport-breakdown-meta"><strong>Actual:</strong> ${actualText}</div>` : ""}
    </div>
  `;
}

function renderLoadingState(message = "Optimizing travel...") {
  if (!resultsListEl) return;
  resultsListEl.innerHTML = `
    <div class="loading-results" role="status" aria-live="polite">
      <span class="loading-spinner" aria-hidden="true"></span>
      <span>${message}</span>
    </div>
  `;
}

function setRankButtonLoading(isLoading) {
  if (!rankBtn) return;
  isRankingInProgress = Boolean(isLoading);
  rankBtn.disabled = isRankingInProgress;
  rankBtn.classList.toggle("is-loading", isRankingInProgress);
  rankBtn.setAttribute("aria-busy", isRankingInProgress ? "true" : "false");
  rankBtn.textContent = isRankingInProgress ? "Optimizing..." : DEFAULT_RANK_BUTTON_TEXT;
}

function renderCombinedResults(data, { persist = true } = {}) {
  const rows = Array.isArray(data?.results) ? data.results : [];
  const flightFilterContext = data?.diagnostics?.flight_filter_context || {};
  const selectedOrigins = Array.isArray(data?.diagnostics?.selected_origin_airports)
    ? data.diagnostics.selected_origin_airports
    : [];
  const flightLabel = selectedOrigins.length === 1 ? "Flight" : "Flights";
  const responseStatus = String(data?.status || "").toLowerCase();
  const hasExplicitError = responseStatus === "error" || Boolean(data?.error);
  const resolvedMessage = toDisplayText(data?.message);

  if (hasExplicitError) {
    const errorMessage = resolvedMessage || toDisplayText(data?.error) || "Unable to optimize travel. Please retry.";
    resultsListEl.innerHTML = `<p class="empty-results">Error: ${errorMessage}</p>`;
    if (persist) {
      persistedCombinedData = null;
      saveResultsState();
    }
    return;
  }

  if (rows.length === 0) {
    const emptyMessage =
      resolvedMessage || "There isn't an airport that has all selected origin airports in common.";
    logFrontend("No ranked results returned", {
      message: emptyMessage,
      diagnostics: data?.diagnostics || null,
    });
    resultsListEl.innerHTML = `<p class="empty-results">${emptyMessage}</p>`;
  } else {
    const firstRow = rows[0] || {};
    const isDestinationCombinedResult =
      Object.prototype.hasOwnProperty.call(firstRow, "destination_iata") &&
      Object.prototype.hasOwnProperty.call(firstRow, "combined_score");
    const isAirportOnlyResult = Object.prototype.hasOwnProperty.call(firstRow, "iata_code");

    resultsListEl.innerHTML = isDestinationCombinedResult
      ? rows
          .map((row) => {
            const flights = Array.isArray(row.flights)
              ? [...row.flights].sort((a, b) =>
                  String(a?.departure_iata || "").localeCompare(String(b?.departure_iata || ""))
                )
              : [];
            const cardToneClass = toneClass(row.combined_score);
            const airportBreakdownRows = Array.isArray(row.airport_breakdown)
              ? row.airport_breakdown
              : [];
            const airportBreakdownHtml = airportBreakdownRows.length
              ? `
                <details class="airport-breakdown">
                  <summary class="airport-breakdown-summary">Airport Score Breakdown</summary>
                  <div class="airport-breakdown-grid">
                    ${airportBreakdownRows
                      .map((item) => {
                        const scoreClass = scoreToneClass(item.score);
                        const filterText = toDisplayText(item.target);
                        const actualText = toDisplayText(item.actual);
                        return `
                          <div class="airport-breakdown-item">
                            <div class="airport-breakdown-head">
                              <span class="airport-breakdown-label">${toDisplayText(item.label) || "Metric"}</span>
                              <span class="airport-breakdown-score ${scoreClass}">${toPercent(item.score)}</span>
                            </div>
                            ${filterText ? `<div class="airport-breakdown-meta"><strong>Filter:</strong> ${filterText}</div>` : ""}
                            ${actualText ? `<div class="airport-breakdown-meta"><strong>Actual:</strong> ${actualText}</div>` : ""}
                          </div>
                        `;
                      })
                      .join("")}
                  </div>
                </details>
              `
              : "";
            const flightsHtml = flights.length
              ? flights
                  .map(
                    (flight) => {
                      const flightScoreMap = flight?.scores && typeof flight.scores === "object" ? flight.scores : {};
                      const detailRows = [];
                      const airlineLabel =
                        flight.airline_name && flight.airline_iata
                          ? `${flight.airline_name} (${flight.airline_iata})`
                          : flight.airline_name || flight.airline_iata;
                      detailRows.push(renderDetailRow("Airline", airlineLabel));
                      detailRows.push(renderDetailRow("Flight Code", flight.flight_iata));
                      detailRows.push(renderDetailRow("Departure", formatDateTime(flight.departure_scheduled)));
                      detailRows.push(renderDetailRow("Arrival", formatDateTime(flight.arrival_scheduled)));

                      const maxTime =
                        typeof flightFilterContext.max_flight_time === "number"
                          ? flightFilterContext.max_flight_time
                          : null;
                      const maxCost =
                        typeof flightFilterContext.max_flight_cost === "number"
                          ? flightFilterContext.max_flight_cost
                          : null;
                      const timeScore =
                        typeof flightScoreMap.flight_time === "number" ? flightScoreMap.flight_time : null;
                      const costScore =
                        typeof flightScoreMap.flight_cost === "number" ? flightScoreMap.flight_cost : null;

                      detailRows.push(
                        renderFlightScoreCard(
                          "Time",
                          maxTime !== null ? `≤ ${formatHoursLabel(maxTime)}` : "",
                          formatDurationHours(flight.duration_hours),
                          timeScore
                        )
                      );
                      detailRows.push(
                        renderFlightScoreCard(
                          "Cost",
                          maxCost !== null ? `≤ ${toMoney(maxCost)}` : "",
                          toMoney(flight.estimated_cost_usd),
                          costScore
                        )
                      );
                      const expandedHtml = detailRows.filter(Boolean).join("");

                      return `
                <details class="flight-row ${toneClass(flight.percent_match)}">
                  <summary class="flight-summary">
                    <span class="flight-route-wrap">
                      <span class="flight-caret">▸</span>
                      <span class="flight-route">${flight.departure_iata || "N/A"} → ${flight.arrival_iata || "N/A"}</span>
                    </span>
                    <span class="flight-score-pill ${scoreToneClass(flight.percent_match)}">FS ${toPercent(flight.percent_match)}</span>
                  </summary>
                  <div class="flight-expanded">
                    ${expandedHtml || '<div class="flight-meta">No extra data available.</div>'}
                  </div>
                </details>
              `
                    }
                  )
                  .join("")
              : '<div class="flight-row"><div class="flight-meta">No flight rows for this destination.</div></div>';

            return `
          <article class="result-card ${cardToneClass}">
            <div class="result-head">
              <div class="route">#${row.rank} ${row.destination_iata}${row.destination_name ? ` - ${row.destination_name}` : ""}</div>
              <div class="score-pill ${scoreToneClass(row.combined_score)}">${toPercent(row.combined_score)} Match</div>
            </div>
            <div class="score-breakdown compact">
              <span class="metric-chip metric-airport ${scoreToneClass(row.airport_score)}">Airport #${row.airport_rank ?? "N/A"} | ${toPercent(row.airport_score)}</span>
              <span class="metric-chip metric-flight ${scoreToneClass(row.flight_score)}">${flightLabel} #${row.flight_rank ?? "N/A"} | ${toPercent(row.flight_score)}</span>
              <span class="metric-chip metric-price">All-in ${toMoney(row.combined_price_usd)}</span>
            </div>
            ${airportBreakdownHtml}
            <div class="flight-list">
              ${flightsHtml}
            </div>
          </article>
        `;
          })
          .join("")
      : isAirportOnlyResult
      ? rows
          .map(
            (row) => `
          <article class="result-card">
            <div class="result-head">
              <div class="route">#${row.rank} ${row.iata_code}${row.airport_name ? ` - ${row.airport_name}` : ""}</div>
              <div class="score-total">Match: ${toPercent(row.percent_match)}</div>
            </div>
            <div class="score-breakdown">
              <span>Airport Match: <strong>${toPercent(row.percent_match)}</strong></span>
            </div>
          </article>
        `
          )
          .join("")
      : rows
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

  if (!persist) return;
  persistedCombinedData = data;
  saveResultsState();
}

function clearResultsView() {
  if (outputEl) {
    outputEl.textContent = DEFAULT_OUTPUT_TEXT;
  }
  resultsListEl.innerHTML = DEFAULT_RESULTS_HTML;
  persistedOutputData = null;
  persistedCombinedData = null;
  removeStorage(STORAGE_KEYS.results);
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
  enforceWeatherSelectionRules();
  return {
    departure_date: departureDateEl?.value || null,
    return_date: returnDateEl?.value || null,
    airports: selectedAirports.map((airport) => airport.iata_code),
    weather_preferences: getCheckedValues(WEATHER_OPTIONS),
    conditions_preferences: getCheckedValues(CONDITIONS_OPTIONS),
    geography_preferences: getCheckedValues(GEOGRAPHY_OPTIONS),
    max_flight_time: Number(maxFlightTimeEl.value),
    max_flight_cost: Number(maxFlightCostEl.value),
  };
}

function updatePayloadPreview() {
  const payload = buildFiltersPayload();
  if (requestPayloadEl) {
    requestPayloadEl.textContent = JSON.stringify(payload, null, 2);
  }
}

function handleUiStateChanged() {
  updatePayloadPreview();
  saveUiState();
}

function resetTripFiltersAndResults() {
  if (departureDateEl) departureDateEl.value = "";
  if (returnDateEl) returnDateEl.value = "";

  selectedAirports = [];
  airportMatches = [];
  highlightedAirportIndex = 0;
  if (airportInputEl) airportInputEl.value = "";
  renderAirportChips();
  renderAirportSuggestions();

  FILTER_CHECKBOX_IDS.forEach((id) => {
    const checkbox = document.getElementById(id);
    if (checkbox) {
      checkbox.checked = false;
    }
  });

  if (maxFlightTimeEl) {
    maxFlightTimeEl.value = String(DEFAULT_MAX_FLIGHT_TIME);
  }
  if (maxFlightTimeValueEl) {
    maxFlightTimeValueEl.textContent = formatHoursLabel(maxFlightTimeEl.value);
  }

  if (maxFlightCostEl) {
    maxFlightCostEl.value = String(DEFAULT_MAX_FLIGHT_COST);
  }
  if (maxFlightCostValueEl) {
    maxFlightCostValueEl.textContent = `$${maxFlightCostEl.value}`;
  }

  removeStorage(STORAGE_KEYS.ui);
  clearResultsView();
  updatePayloadPreview();
}

async function callApi(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const method = options.method || "GET";
  logFrontend("API request start", {
    method,
    path,
    headers: summarizeHeaders(options.headers),
    body: typeof options.body === "string" ? options.body : options.body,
  });

  const res = await fetch(url, options);
  const rawBody = await res.text();
  let data = {};
  try {
    data = rawBody ? JSON.parse(rawBody) : {};
  } catch (_error) {
    data = { message: rawBody || "Request failed" };
  }

  logFrontend("API response received", {
    method,
    path,
    status: res.status,
    ok: res.ok,
    data,
  });

  if (!res.ok) {
    logFrontend("API request failed", {
      method,
      path,
      status: res.status,
      data,
    });
    throw new Error(data.message || data.error || "Request failed");
  }

  return data;
}

healthBtn.addEventListener("click", async () => {
  logFrontend("Health check requested");
  try {
    const data = await callApi("/health");
    setOutput(data);
  } catch (error) {
    setOutput({ error: error.message });
  }
});

departureDateEl?.addEventListener("input", handleUiStateChanged);
returnDateEl?.addEventListener("input", handleUiStateChanged);

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
  maxFlightTimeValueEl.textContent = formatHoursLabel(maxFlightTimeEl.value);
  handleUiStateChanged();
});

maxFlightCostEl.addEventListener("input", () => {
  maxFlightCostValueEl.textContent = `$${maxFlightCostEl.value}`;
  handleUiStateChanged();
});

WEATHER_ID_ORDER.forEach((id) => {
  const checkbox = document.getElementById(id);
  checkbox?.addEventListener("change", () => {
    enforceWeatherSelectionRules(id);
    handleUiStateChanged();
  });
});

[...CONDITIONS_OPTIONS, ...GEOGRAPHY_OPTIONS].forEach(([id]) => {
  const checkbox = document.getElementById(id);
  checkbox?.addEventListener("change", handleUiStateChanged);
});

rankBtn.addEventListener("click", async () => {
  if (isRankingInProgress) {
    return;
  }
  if (!hasSubmittedApiKey || !submittedApiKey) {
    const errorMessage = "Please submit an API key before optimizing travel.";
    setOutput({ error: errorMessage });
    resultsListEl.innerHTML = `<p class="empty-results">Error: ${errorMessage}</p>`;
    persistedCombinedData = null;
    saveResultsState();
    return;
  }

  if (selectedAirports.length === 0) {
    const errorMessage = "Please choose at least one origin airport before optimizing travel.";
    setOutput({ error: errorMessage });
    resultsListEl.innerHTML = `<p class="empty-results">Error: ${errorMessage}</p>`;
    persistedCombinedData = null;
    saveResultsState();
    return;
  }

  if (!(departureDateEl?.value || "").trim()) {
    const errorMessage = "Please choose a departure date before optimizing travel.";
    setOutput({ error: errorMessage });
    resultsListEl.innerHTML = `<p class="empty-results">Error: ${errorMessage}</p>`;
    persistedCombinedData = null;
    saveResultsState();
    return;
  }

  if (!(returnDateEl?.value || "").trim()) {
    const errorMessage = "Please choose a return date before optimizing travel.";
    setOutput({ error: errorMessage });
    resultsListEl.innerHTML = `<p class="empty-results">Error: ${errorMessage}</p>`;
    persistedCombinedData = null;
    saveResultsState();
    return;
  }

  const payload = buildFiltersPayload();
  logFrontend("Optimize Travel requested", {
    selected_airports: selectedAirports.map((airport) => airport.iata_code),
    departure_date: payload.departure_date,
    return_date: payload.return_date,
    weather_preferences: payload.weather_preferences,
    conditions_preferences: payload.conditions_preferences,
    geography_preferences: payload.geography_preferences,
    max_flight_time: payload.max_flight_time,
    max_flight_cost: payload.max_flight_cost,
  });
  console.log("[MiddleGround Request Payload]", payload);
  updatePayloadPreview();
  saveUiState();
  setRankButtonLoading(true);
  renderLoadingState();
  logFrontend("Optimize Travel loading state shown");

  try {
    const data = await callApi("/rank-combined?limit=10", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": submittedApiKey,
      },
      body: JSON.stringify(payload),
    });
    setOutput(data);
    logFrontend("Optimize Travel results received", {
      count: Array.isArray(data?.results) ? data.results.length : 0,
      message: data?.message || null,
      diagnostics: data?.diagnostics || null,
    });
    renderCombinedResults(data);
    logFrontend("Optimize Travel results rendered");
  } catch (error) {
    logFrontend("Optimize Travel failed", { error: error.message });
    setOutput({ error: error.message });
    resultsListEl.innerHTML = `<p class="empty-results">Error: ${error.message}</p>`;
    persistedCombinedData = null;
    saveResultsState();
  } finally {
    setRankButtonLoading(false);
    logFrontend("Optimize Travel loading state cleared");
  }
});

apiKeyInputEl?.addEventListener("input", () => {
  updateApiKeyButtonText();
});

apiKeyInputEl?.addEventListener("keydown", async (event) => {
  if (event.key !== "Enter") return;
  event.preventDefault();
  await handleApiKeySubmitButtonClick();
});

submitBtn?.addEventListener("click", async () => {
  await handleApiKeySubmitButtonClick();
});

resetBtn?.addEventListener("click", () => {
  resetApiKeyState();
});

resetSearchBtn?.addEventListener("click", () => {
  resetTripFiltersAndResults();
});

loadApiKeyState();
syncApiKeyUI();

loadUiState();
maxFlightTimeValueEl.textContent = formatHoursLabel(maxFlightTimeEl.value);
maxFlightCostValueEl.textContent = `$${maxFlightCostEl.value}`;
updatePayloadPreview();

loadResultsState();
loadAirportCatalog();
