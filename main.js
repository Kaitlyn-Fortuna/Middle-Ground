const API_BASE = "http://127.0.0.1:5001/api";

const outputEl = document.getElementById("output");
const healthBtn = document.getElementById("healthBtn");
const requestPayloadEl = document.getElementById("requestPayload");
const buildPayloadBtn = document.getElementById("buildPayloadBtn");
const rankBtn = document.getElementById("rankBtn");

function setOutput(data) {
  outputEl.textContent = JSON.stringify(data, null, 2);
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

rankBtn.addEventListener("click", async () => {
  const payload = buildFiltersPayload();
  updatePayloadPreview();

  try {
    const data = await callApi("/rank?limit=25", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    setOutput(data);
  } catch (error) {
    setOutput({ error: error.message });
  }
});

updatePayloadPreview();
