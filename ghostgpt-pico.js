#!/usr/bin/env node

require("dotenv").config();
const fetch = require("node-fetch");
const fs = require("fs");
const path = require("path");

const PK = process.env.PICO_PK;

if (!PK) {
  console.error("❌ Missing PICO_PK in .env");
  process.exit(1);
}

const API_URL = `https://backend.buildpicoapps.com/aero/run/llm-api?pk=${PK}`;
const PERSONA_PATH = path.join(__dirname, "persona.txt");

/**
 * Load persona from file
 */
function loadPersona() {
  try {
    if (!fs.existsSync(PERSONA_PATH)) {
      console.warn("⚠️ persona.txt not found. Using empty persona.");
      return "";
    }

    return fs.readFileSync(PERSONA_PATH, "utf8").trim();
  } catch (err) {
    console.error("❌ Failed to read persona.txt");
    throw err;
  }
}

/**
 * Inject persona into prompt
 */
function injectPersona(userInput) {
  const persona = loadPersona();

  if (!persona) return userInput;

  return `${persona}\n\nUser:\n${userInput}`;
}

async function ghostGPT(userInput) {
  if (!userInput || typeof userInput !== "string") {
    throw new Error("Input must be a non-empty string.");
  }

  const payload = {
    prompt: injectPersona(userInput)
  };

  const response = await fetch(API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  const raw = await response.text();

  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    throw new Error("Invalid JSON response:\n" + raw);
  }

  if (!response.ok || data.status === "inputValidationError") {
    throw new Error(
      `API Error\nStatus: ${response.status}\nBody: ${JSON.stringify(data, null, 2)}`
    );
  }

  return data;
}

// CLI Mode
if (require.main === module) {
  const input = process.argv.slice(2).join(" ");

  if (!input) {
    console.log('Usage: node ghostgpt-pico.js "your message"');
    process.exit(0);
  }

  (async () => {
    try {
      console.log("👻 Sending to Pico...\n");
      const result = await ghostGPT(input);

      console.log("👻 GhostGPT:\n");
      console.log(
        result.response ||
        result.output ||
        JSON.stringify(result, null, 2)
      );
    } catch (err) {
      console.error("\n❌ FULL ERROR STACK:");
      console.error(err);
    }
  })();
}

module.exports = ghostGPT;
