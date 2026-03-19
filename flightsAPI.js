import axios from "axios";
import dotenv from "dotenv";
dotenv.config();

const API_KEY = process.env.FLIGHTS_API_KEY;
const BASE_URL = "http://api.aviationstack.com/v1";

async function testFlight() {
  try {
    const res = await axios.get("http://api.aviationstack.com/v1/flights", {
      params: { access_key: API_KEY, limit: 1 }
    });
    console.log("Flight:", res.data.data[0]); // show just one flight
  } catch (err) {
    console.error("Error:", err.response?.data || err.message);
  }
}

testFlight();