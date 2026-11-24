(function () {
  "use strict";

  const ticket = document.getElementById("ticket-text");
  const classifyForm = document.getElementById("classify-form");
  const panel = document.getElementById("suggest-panel");
  const form = document.getElementById("suggest-form");
  const button = document.getElementById("suggest-btn");
  const keyInput = document.getElementById("api-key");
  const connection = document.getElementById("conn-settings");
  const result = document.getElementById("suggest-result");
  const status = document.getElementById("suggest-status");
  const draft = document.getElementById("suggest-draft");
  const sources = document.getElementById("suggest-sources");
  const reasons = {
    provider_timeout: "The drafting provider timed out.",
    provider_error: "The drafting provider could not complete the request.",
    invalid_output: "The draft or its sources could not be verified.",
    request_timeout: "The request reached its time limit.",
    retrieval_unavailable: "Document search is temporarily unavailable.",
    interrupted: "The earlier operation was interrupted."
  };
  let busy = false;
  let pending;
  let review;

  function updateButton() {
    button.disabled = busy || !review;
  }

  function clearResult() {
    status.textContent = "";
    draft.textContent = "";
    draft.hidden = true;
    sources.replaceChildren();
    sources.hidden = true;
  }

  function render(payload) {
    if (payload.status === "draft_ready") {
      status.textContent = "Review this draft before using it.";
      draft.textContent = payload.draft;
      draft.hidden = false;
      for (const source of payload.sources) {
        const item = document.createElement("li");
        const label = source.title + " · " + source.section + " (" + source.id + ")";
        if (source.url && source.url.startsWith("https://")) {
          const link = document.createElement("a");
          link.href = source.url;
          link.textContent = label;
          item.append(link);
        } else {
          item.textContent = label;
        }
        sources.append(item);
      }
      sources.hidden = false;
    } else if (payload.status === "in_progress") {
      status.textContent = "The request is still running. Select Suggest resolution again to check.";
    } else {
      status.textContent = reasons[payload.review_reason] ||
        "No sourced draft was found for this ticket.";
    }
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    if (!review || busy) return;
    const requestedReview = review;
    const { text, apiKey } = requestedReview;
    if (!pending || pending.text !== text || pending.apiKey !== apiKey) {
      const bytes = crypto.getRandomValues(new Uint8Array(16));
      const id = Array.from(bytes, byte => byte.toString(16).padStart(2, "0")).join("");
      pending = { text, apiKey, id };
    }
    const headers = { "Content-Type": "application/json", "Idempotency-Key": pending.id };
    if (apiKey) headers["X-API-Key"] = apiKey;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 12000);
    busy = true;
    updateButton();
    clearResult();
    result.setAttribute("aria-busy", "true");
    status.textContent = "Searching support documents…";
    try {
      const response = await fetch("/suggest-resolution", {
        method: "POST", headers, body: JSON.stringify({ text }), signal: controller.signal
      });
      const payload = await response.json();
      if (response.ok && payload.status !== "in_progress") pending = undefined;
      if (review !== requestedReview) return;
      if (response.ok) {
        render(payload);
      } else if (response.status === 401) {
        connection.hidden = false;
        connection.open = true;
        keyInput.focus();
        status.textContent = "Enter a valid API key and try again.";
      } else if (response.status === 503 && typeof payload.detail === "string") {
        status.textContent = payload.detail;
      } else {
        pending = undefined;
        status.textContent = "The resolution request failed (HTTP " + response.status + ").";
      }
    } catch {
      if (review === requestedReview) {
        status.textContent = "Could not get a resolution result. Try again to check the same request.";
      }
    } finally {
      clearTimeout(timer);
      busy = false;
      result.setAttribute("aria-busy", "false");
      updateButton();
    }
  });

  function resetReview() {
    review = undefined;
    panel.hidden = true;
    clearResult();
    updateButton();
  }
  classifyForm.addEventListener("submit", resetReview);
  classifyForm.addEventListener("queuepilot:routing-decision", function (event) {
    if (!event.detail) return;
    review = { text: ticket.value.trim(), apiKey: keyInput.value.trim() };
    panel.hidden = false;
    updateButton();
  });
  ticket.addEventListener("input", resetReview);
  keyInput.addEventListener("input", resetReview);
})();
