#!/usr/bin/env node

const fetch = global.fetch || require("node-fetch");

const API_KEY = process.env.PICO_KEY;
const ENDPOINT = "https://backend.buildpicoapps.com/aero/run/llm-api";

if (!API_KEY) {
  console.error("❌ Missing PICO_KEY environment variable.");
  process.exit(1);
}

const DEBUG = true; // 🔥 Toggle this ON/OFF

async function ghostGPT(input) {
  try {
    const response = await fetch(`${ENDPOINT}?pk=${API_KEY}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        messages: [
          { role: "system", content: "You are GhostGPT." },
          { role: "user", content: input }
        ],
        max_tokens: 500
      })
    });

    const rawText = await response.text();

    if (DEBUG) {
      console.log("\n=== DEBUG INFO ===");
      console.log("Status:", response.status);
      console.log("Status Text:", response.statusText);
      console.log("Headers:", Object.fromEntries(response.headers.entries()));
      console.log("Raw Body:", rawText);
      console.log("==================\n");
    }

    // Try parsing JSON
    let data;
    try {
      data = JSON.parse(rawText);
    } catch (parseErr) {
      throw new Error("Response is not valid JSON:\n" + rawText);
    }

    if (data.status !== "success") {
      throw new Error("API returned non-success:\n" + JSON.stringify(data, null, 2));
    }

    return data.text;

  } catch (err) {
    console.error("\n❌ FULL ERROR STACK:");
    console.error(err.stack);
    return "Request failed.";
  }
}

if (require.main === module) {
  const userInput = process.argv.slice(2).join(" ");

  if (!userInput) {
    console.log("Usage: node ghostgpt-debug.js \"Your prompt here\"");
    process.exit(0);
  }

  ghostGPT(userInput).then(res => {
    console.log("\n👻 GhostGPT:\n");
    console.log(res);
  });
}

module.exports = ghostGPT;

