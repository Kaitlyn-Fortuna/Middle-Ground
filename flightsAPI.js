import axios from "axios";
const API_KEY = (process.argv[2] || "").trim();
const BASE_URL = "http://api.aviationstack.com/v1";

async function testFlight() {
  if (!API_KEY) {
    console.error("Missing API key. Usage: node flightsAPI.js <AVIATIONSTACK_KEY>");
    return;
  }

  try {
    const res = await axios.get(`${BASE_URL}/flights`, {
      params: { access_key: API_KEY, limit: 1 }
    });
    console.log("Flight:", res.data.data[0]); // show just one flight
  } catch (err) {
    console.error("Error:", err.response?.data || err.message);
  }
}

testFlight();
