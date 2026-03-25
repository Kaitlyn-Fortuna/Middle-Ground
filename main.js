const API_BASE = "http://127.0.0.1:5001/api";

const outputEl = document.getElementById("output");
const healthBtn = document.getElementById("healthBtn");
const computeBtn = document.getElementById("computeBtn");
const valueInput = document.getElementById("valueInput");

function setOutput(data) {
  outputEl.textContent = JSON.stringify(data, null, 2);
}

async function callApi(path) {
  const res = await fetch(`${API_BASE}${path}`);
  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.error || "Request failed");
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

computeBtn.addEventListener("click", async () => {
  const value = Number(valueInput.value);

  try {
    const data = await callApi(`/compute?value=${encodeURIComponent(value)}`);
    setOutput(data);
  } catch (error) {
    setOutput({ error: error.message });
  }
});
