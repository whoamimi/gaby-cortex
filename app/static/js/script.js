// static/js/script.js
// Stateless streaming client: reads UTF-8 bytes until the server closes the stream.

let controller = null;

const $ = (sel) => document.querySelector(sel);

const out = $("#out");
const statusEl = $("#status");
const lastIdEl = $("#eid");

const connectBtn = $("#connect");
const disconnectBtn = $("#disconnect");
const clearBtn = $("#clear");

const sidEl = $("#sid");
const filenameEl = $("#filename");
const dataTypeEl = $("#dataType");
const databaseTypeEl = $("#databaseType");
const dataPlatformTypeEl = $("#dataPlatformType");

function setStatus(txt, color = "#444") {
  statusEl.textContent = txt;
  statusEl.style.borderColor = color;
  statusEl.style.color = color;
}

function appendRaw(text) {
  // Append exactly what arrives, without adding extra newlines.
  out.textContent += text;
  out.scrollTop = out.scrollHeight;
}

function buildUrl() {
  const id = (sidEl?.value || "").trim();
  if (!id) return null;

  const params = new URLSearchParams();

  const filename = (filenameEl?.value || "").trim();
  const dataType = (dataTypeEl?.value || "").trim();
  const databaseType = (databaseTypeEl?.value || "").trim();
  const dataPlatformType = (dataPlatformTypeEl?.value || "").trim();

  if (filename) params.set("filename", filename);
  if (dataType) params.set("dataType", dataType);
  if (databaseType) params.set("databaseType", databaseType);
  if (dataPlatformType) params.set("dataPlatformType", dataPlatformType);

  const qs = params.toString();
  return `/stream/${encodeURIComponent(id)}${qs ? `?${qs}` : ""}`;
}

function setConnectedUi(url) {
  setStatus("connected", "#1a7f37");
  connectBtn.disabled = true;
  disconnectBtn.disabled = false;
  // purely informational; no state tracking
  if (lastIdEl) lastIdEl.textContent = "—";
  appendRaw(`// [open] ${url}\n`);
}

function setDisconnectedUi() {
  setStatus("disconnected", "#444");
  connectBtn.disabled = false;
  disconnectBtn.disabled = true;
}

async function connect() {
  // Do not start another stream if one is active.
  if (controller) return;

  const url = buildUrl();
  if (!url) {
    setStatus("missing session id", "#b54708");
    appendRaw("// [warn] Provide a session id.\n");
    return;
  }

  controller = new AbortController();
  setStatus("connecting...", "#915");
  connectBtn.disabled = true;
  disconnectBtn.disabled = false;

  let res;
  try {
    res = await fetch(url, {
      method: "GET",
      signal: controller.signal,
      headers: {
        // Keep this if your backend responds with text/event-stream
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
      },
    });
  } catch (err) {
    setStatus("connection error", "#b54708");
    appendRaw(`// [error] fetch failed: ${err?.message || err}\n`);
    controller = null;
    setDisconnectedUi();
    return;
  }

  if (!res.ok || !res.body) {
    setStatus("connection error", "#b54708");
    appendRaw(`// [error] HTTP ${res.status}\n`);
    controller = null;
    setDisconnectedUi();
    return;
  }

  setConnectedUi(url);

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      // Decode bytes to UTF-8 text and append exactly as received.
      appendRaw(decoder.decode(value, { stream: true }));
    }

    // Flush any remaining decoder buffer.
    appendRaw(decoder.decode());
    appendRaw("\n// [close] server finished\n");
  } catch (err) {
    // Abort is expected on manual disconnect.
    if (controller && controller.signal.aborted) {
      appendRaw("\n// [close] client disconnected\n");
    } else {
      setStatus("stream error", "#b54708");
      appendRaw(`\n// [error] stream read failed: ${err?.message || err}\n`);
    }
  } finally {
    controller = null;
    setDisconnectedUi();
  }
}

function disconnect() {
  if (!controller) return;
  controller.abort();
  // UI will be reset in connect()'s finally block once the read loop unwinds.
}

connectBtn.addEventListener("click", connect);
disconnectBtn.addEventListener("click", disconnect);
clearBtn.addEventListener("click", () => { out.textContent = ""; });
window.addEventListener("beforeunload", disconnect);