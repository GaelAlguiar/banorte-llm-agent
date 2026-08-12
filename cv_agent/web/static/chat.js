(() => {
  "use strict";
  const STORAGE_KEY = "aiguiar_conversations_v1";
  const $ = (selector) => document.querySelector(selector);
  const elements = { sidebar: $("#sidebar"), backdrop: $("#backdrop"), list: $("#conversation-list"), search: $("#chat-search"), welcome: $("#welcome"), messages: $("#messages"), form: $("#message-form"), input: $("#message-input"), send: $("#send-button") };
  let conversations = load();
  let activeId = conversations[0]?.id || createConversation();
  let busy = false;

  function load() { try { const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"); return Array.isArray(value) ? value : []; } catch { return []; } }
  function save() { localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations.slice(0, 30))); }
  function createConversation() { const id = crypto.randomUUID ? crypto.randomUUID() : String(Date.now()); conversations.unshift({ id, title: "Nueva conversación", updatedAt: Date.now(), messages: [] }); save(); return id; }
  function current() { return conversations.find((item) => item.id === activeId); }
  function renderList(filter = "") { elements.list.replaceChildren(); conversations.filter((item) => item.title.toLowerCase().includes(filter.toLowerCase())).forEach((item) => { const button = document.createElement("button"); button.type = "button"; button.className = `conversation-item${item.id === activeId ? " active" : ""}`; button.textContent = item.title; button.addEventListener("click", () => { activeId = item.id; render(); closeMenu(); }); elements.list.append(button); }); }
  function evidenceDetails(items) { if (!Array.isArray(items) || !items.length) return null; const details = document.createElement("details"); details.className = "evidence"; const summary = document.createElement("summary"); summary.textContent = "Evidencia"; details.append(summary); const list = document.createElement("ul"); items.slice(0, 3).forEach((item) => { const entry = document.createElement("li"); entry.textContent = `${[item.title, item.section].filter(Boolean).join(" · ")} (${item.confidence || "contextual"})`; list.append(entry); }); details.append(list); return details; }
  function splitUsageFooter(content) { const match = content.match(/^(.*)\n\n([\d,]+ tokens · \d+(?:\.\d)?% disponible)$/s); return match ? { text: match[1], footer: match[2] } : { text: content, footer: null }; }
  function makeMessage(message, loading = false) { const row = document.createElement("article"); row.className = `message ${message.role}`; if (message.role === "assistant") { const avatar = document.createElement("span"); avatar.className = "message-avatar"; avatar.textContent = "A"; row.append(avatar); } const wrap = document.createElement("div"); const bubble = document.createElement("div"); bubble.className = "bubble"; let usageLine = null; if (loading) { bubble.innerHTML = '<span class="typing" aria-label="AIguiar AI está escribiendo"><i></i><i></i><i></i></span>'; } else { const display = splitUsageFooter(message.content || ""); bubble.textContent = display.text; if (display.footer) { usageLine = document.createElement("p"); usageLine.className = "message-usage"; usageLine.textContent = display.footer; usageLine.setAttribute("aria-label", `Uso de la respuesta: ${display.footer}`); wrap.append(usageLine); } } wrap.append(bubble); if (usageLine) wrap.append(usageLine); if (message.role === "assistant" && !loading) { const details = evidenceDetails(message.evidence); if (details) wrap.append(details); const copy = document.createElement("button"); copy.type = "button"; copy.className = "copy-button"; copy.textContent = "Copiar respuesta"; copy.addEventListener("click", async () => { await navigator.clipboard.writeText(message.content); copy.textContent = "Copiada"; setTimeout(() => copy.textContent = "Copiar respuesta", 1500); }); wrap.append(copy); } row.append(wrap); return row; }
  function renderMessages() { const chat = current(); elements.messages.replaceChildren(); const hasMessages = Boolean(chat?.messages.length); elements.welcome.hidden = hasMessages; elements.messages.classList.toggle("active", hasMessages); chat?.messages.forEach((message) => elements.messages.append(makeMessage(message))); renderList(elements.search.value); requestAnimationFrame(() => { const stage = $(".chat-stage"); stage.scrollTop = stage.scrollHeight; }); }
  function render() { renderMessages(); }
  function add(role, content, evidence = [], usage = null, budget = null) { const chat = current(); chat.messages.push({ role, content, evidence, usage, budget }); if (chat.messages.length === 1) chat.title = content.slice(0, 46) + (content.length > 46 ? "…" : ""); chat.updatedAt = Date.now(); conversations.sort((a, b) => b.updatedAt - a.updatedAt); save(); render(); }
  function setBusy(value) { busy = value; elements.send.disabled = value; elements.input.disabled = value; }
  async function send(message) { const clean = message.trim(); if (!clean || busy) return; add("user", clean); elements.input.value = ""; resize(); setBusy(true); elements.messages.append(makeMessage({ role: "assistant", content: "" }, true)); try { const response = await fetch("/chat/api/messages", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message: clean }) }); const data = await response.json(); if (!response.ok) throw new Error(data?.error?.message || "No fue posible procesar el mensaje."); add("assistant", data.response, data.evidence, data.usage, data.budget); } catch (error) { add("assistant", `No pude responder en este momento. ${error.message} Intenta nuevamente.`); } finally { setBusy(false); elements.input.focus(); } }
  function resize() { elements.input.style.height = "auto"; elements.input.style.height = `${Math.min(elements.input.scrollHeight, 160)}px`; }
  function closeMenu() { elements.sidebar.classList.remove("open"); elements.backdrop.hidden = true; }
  $("#menu-button").addEventListener("click", () => { elements.sidebar.classList.add("open"); elements.backdrop.hidden = false; });
  elements.backdrop.addEventListener("click", closeMenu);
  $("#new-chat").addEventListener("click", () => { activeId = createConversation(); render(); closeMenu(); elements.input.focus(); });
  $("#clear-chat").addEventListener("click", () => { const chat = current(); if (chat) { chat.messages = []; chat.title = "Nueva conversación"; save(); render(); } });
  elements.search.addEventListener("input", () => renderList(elements.search.value));
  elements.input.addEventListener("input", resize);
  elements.input.addEventListener("keydown", (event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); elements.form.requestSubmit(); } });
  elements.form.addEventListener("submit", (event) => { event.preventDefault(); send(elements.input.value); });
  document.querySelectorAll(".suggestion").forEach((button) => button.addEventListener("click", () => send(button.textContent)));
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeMenu(); });
  render();
})();
