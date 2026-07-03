/**
 * script.js — MaskGuard Analytics Dashboard
 *
 * Polls /stats every second and /previous-session on load + every 30s.
 * Uses canvas snapshot polling at /frame every 100ms for the live feed.
 */

"use strict";

// ── Element cache ─────────────────────────────────────────
const el = {
  clock:          document.getElementById("clock"),
  statusPill:     document.getElementById("statusPill"),
  statusLabel:    document.getElementById("statusLabel"),

  person:         document.getElementById("stat-person"),
  clear_face:     document.getElementById("stat-clear_face"),
  head:           document.getElementById("stat-head"),
  masked_face:    document.getElementById("stat-masked_face"),
  not_sure:       document.getElementById("stat-not_sure"),

  compliance:     document.getElementById("stat-compliance"),
  complianceBar:  document.getElementById("complianceBar"),

  prevContent:    document.getElementById("prevContent"),
  feedOverlay:    document.getElementById("feedOverlay"),
};

// ── Clock ─────────────────────────────────────────────────
function updateClock() {
  const now = new Date();
  const pad = n => String(n).padStart(2, "0");
  el.clock.textContent =
    `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}
updateClock();
setInterval(updateClock, 1000);

// ── Helpers ───────────────────────────────────────────────

function setOnline(online) {
  if (online) {
    el.statusPill.classList.add("online");
    el.statusLabel.textContent = "Detector Online";
  } else {
    el.statusPill.classList.remove("online");
    el.statusLabel.textContent = "Detector Offline";
  }
}

function bump(element) {
  element.classList.remove("bumping");
  void element.offsetWidth;
  element.classList.add("bumping");
  element.addEventListener("animationend", () => element.classList.remove("bumping"), { once: true });
}

function setStatValue(element, newValue) {
  if (element.textContent !== newValue) {
    element.textContent = newValue;
    bump(element);
  }
}

// ── /stats polling ────────────────────────────────────────

async function fetchStats() {
  try {
    const res = await fetch("/stats", { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    setOnline(true);

    setStatValue(el.person,      String(data.person      ?? 0));
    setStatValue(el.clear_face,  String(data.clear_face  ?? 0));
    setStatValue(el.head,        String(data.head        ?? 0));
    setStatValue(el.masked_face, String(data.masked_face ?? 0));
    setStatValue(el.not_sure,    String(data.not_sure    ?? 0));

    const comp = typeof data.compliance === "number" ? data.compliance : 0;
    const compStr = `${comp.toFixed(2)}%`;

    if (el.compliance.textContent !== compStr) {
      el.compliance.textContent = compStr;
      bump(el.compliance);
    }

    el.complianceBar.style.width = `${Math.min(comp, 100)}%`;
    if (comp < 50) {
      el.complianceBar.classList.add("low");
    } else {
      el.complianceBar.classList.remove("low");
    }

  } catch (err) {
    setOnline(false);
    console.warn("[stats]", err.message);
  }
}

// ── /previous-session fetch ───────────────────────────────

function formatDateTime(str) {
  if (!str) return "—";
  return str.replace("T", " ").slice(0, 19);
}

function buildPrevHTML(s) {
  const comp = typeof s.compliance === "number" ? s.compliance.toFixed(2) : "0.00";
  return `
    <div class="prev-compliance">
      <span class="prev-compliance__label">Mask Compliance</span>
      <span class="prev-compliance__val">${comp}%</span>
    </div>

    <div class="prev-grid">
      <div class="prev-row">
        <span class="prev-row__label">Person</span>
        <span class="prev-row__val">${s.person_count ?? 0}</span>
      </div>
      <div class="prev-row">
        <span class="prev-row__label">Clear Face</span>
        <span class="prev-row__val">${s.clear_face_count ?? 0}</span>
      </div>
      <div class="prev-row">
        <span class="prev-row__label">Head</span>
        <span class="prev-row__val">${s.head_count ?? 0}</span>
      </div>
      <div class="prev-row">
        <span class="prev-row__label">Masked Face</span>
        <span class="prev-row__val">${s.masked_face_count ?? 0}</span>
      </div>
      <div class="prev-row">
        <span class="prev-row__label">Not Sure</span>
        <span class="prev-row__val">${s.not_sure_count ?? 0}</span>
      </div>
    </div>

    <div class="prev-times">
      <div class="prev-time-row">
        <span class="prev-time-row__label">Start</span>
        <span class="prev-time-row__val">${formatDateTime(s.start_time)}</span>
      </div>
      <div class="prev-time-row">
        <span class="prev-time-row__label">End</span>
        <span class="prev-time-row__val">${formatDateTime(s.end_time)}</span>
      </div>
    </div>
  `;
}

async function fetchPreviousSession() {
  try {
    const res = await fetch("/previous-session", { cache: "no-store" });
    if (res.status === 404) {
      el.prevContent.innerHTML = '<p class="prev-empty">No previous session recorded yet.</p>';
      return;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const s = await res.json();
    el.prevContent.innerHTML = buildPrevHTML(s);
  } catch (err) {
    console.warn("[previous-session]", err.message);
  }
}

// ── Feed overlay ──────────────────────────────────────────

function hideFeedOverlay() {
  el.feedOverlay.classList.add("hidden");
}

// ── Snapshot poller ───────────────────────────────────────
// Fetches a single JPEG from /frame every 100ms and draws to canvas.
// Avoids all MJPEG browser compatibility issues.

async function startFramePoller() {
  const canvas = document.getElementById("feedImg");
  const ctx    = canvas.getContext("2d");
  canvas.width  = 640;
  canvas.height = 480;

  async function fetchFrame() {
    try {
      const res = await fetch(`/frame?t=${Date.now()}`, { cache: "no-store" });
      if (res.status === 204) return;  // detector not ready yet
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const img  = new Image();
      img.onload = () => {
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        URL.revokeObjectURL(url);
        hideFeedOverlay();
      };
      img.src = url;
    } catch (e) {
      console.warn("[frame]", e.message);
    }
  }

  setInterval(fetchFrame, 100);  // ~10 fps
}

// ── Bootstrap ─────────────────────────────────────────────

fetchStats();
fetchPreviousSession();

setInterval(fetchStats,           1_000);
setInterval(fetchPreviousSession, 30_000);

startFramePoller();