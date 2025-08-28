// index.js
import fetch from "node-fetch";
import fs from "fs";

const WEBHOOK_URL = process.env.WEBHOOK_URL;
if (!WEBHOOK_URL) {
  console.error("ERROR: Please set WEBHOOK_URL environment variable.");
  process.exit(1);
}

const MESSAGE_ID_FILE = "./message_id.txt";
const LAST_CONTENT_FILE = "./last_content.txt";
const B52_API = "https://dichvuweb.site/toolb52/proxy_api.php";
const SUNWIN_API = "https://dichvuweb.site/toolsunwin/toolsunwin.php";
const INTERVAL_MS = process.env.INTERVAL_MS ? parseInt(process.env.INTERVAL_MS, 10) : 10000; // default 10s

async function getJson(url) {
  try {
    const res = await fetch(url, { timeout: 7000 });
    if (!res.ok) return {};
    return await res.json();
  } catch (e) {
    console.error("API fetch error:", e.message || e);
    return {};
  }
}

function readFileSafe(path) {
  try {
    return fs.existsSync(path) ? fs.readFileSync(path, "utf-8") : null;
  } catch (e) {
    return null;
  }
}

function writeFileSafe(path, data) {
  try {
    fs.writeFileSync(path, data, "utf-8");
  } catch (e) {
    console.error("Write file error:", e);
  }
}

async function sendOrEdit(content) {
  try {
    const messageId = readFileSafe(MESSAGE_ID_FILE);
    const url = messageId ? `${WEBHOOK_URL}/messages/${messageId}` : WEBHOOK_URL;
    const method = messageId ? "PATCH" : "POST";

    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content })
    });

    if (!res.ok) {
      console.error(`Discord webhook responded ${res.status} ${res.statusText}`);
      const txt = await res.text();
      console.error(txt);
      return false;
    }

    const data = await res.json();
    if (!messageId && data.id) {
      writeFileSafe(MESSAGE_ID_FILE, data.id);
      console.log("Saved message id:", data.id);
    }
    return true;
  } catch (e) {
    console.error("sendOrEdit error:", e.message || e);
    return false;
  }
}

async function buildContent() {
  const b52 = await getJson(B52_API);
  const sunwin = await getJson(SUNWIN_API);

  const colorEmoji = b52.color === "red" ? "🔴" : (b52.color === "green" ? "🟢" : "");
  const b52XucXac = (b52.xucxac || []).join(", ");

  const content =
    `**🎲 Dự đoán Tài Xỉu hôm nay**\n\n` +
    `**🔥 Tool B52**\n` +
    `Phiên: ${b52.phienmoi || "N/A"}\n` +
    `Dự đoán: ${b52.dudoan || "N/A"} (${b52.confidence || ""}) ${colorEmoji}\n` +
    `Xúc xắc: ${b52XucXac}\n\n` +
    `**⚡ Tool Sunwin**\n` +
    `Phiên: ${sunwin.phienmoi || "N/A"}\n` +
    `Dự đoán: ${sunwin.dudoan || "N/A"} (${sunwin.tile || ""})`;

  return content;
}

async function tick() {
  try {
    const content = await buildContent();
    const last = readFileSafe(LAST_CONTENT_FILE);

    if (content !== last) {
      console.log(new Date().toISOString(), "-> Content changed, updating Discord...");
      const ok = await sendOrEdit(content);
      if (ok) {
        writeFileSafe(LAST_CONTENT_FILE, content);
        console.log("Update done.");
      } else {
        console.error("Failed to update Discord.");
      }
    } else {
      // no change
      // console.log(new Date().toISOString(), "-> No change.");
    }
  } catch (e) {
    console.error("tick error:", e);
  }
}

// start
console.log("Bot starting. Interval (ms):", INTERVAL_MS);
tick(); // run immediately
setInterval(tick, INTERVAL_MS);
