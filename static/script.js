const state = {
  games: [],
  currentGameId: null,
  players: [],
  board: [],
  currentPlayerId: null,
  turnActive: false,
  purchaseHighlightIndex: null,
  pendingPollId: null,
  tokenColors: ["#e11d48", "#2563eb", "#16a34a", "#f59e0b", "#7c3aed", "#0ea5e9"],
};

const ICON = {
  dice: "/icons/dice-svgrepo-com.svg",
  house: "/icons/house-svgrepo-com.svg",
  hotel: "/icons/hotel-svgrepo-com.svg",
  mortgage: "/icons/mortgage-insurance-svgrepo-com.svg",
  stats: "/icons/stats-1370-svgrepo-com.svg",
  trade: "/icons/swap-svgrepo-com.svg",
};

const el = {
  gameSelect: document.getElementById("gameSelect"),
  newGameBtn: document.getElementById("newGameBtn"),
  playerSelect: document.getElementById("playerSelect"),
  turnHint: document.getElementById("turnHint"),
  boardFrame: document.getElementById("boardFrame"),
  board: document.getElementById("board"),
  ownedPanel: document.getElementById("ownedPanel"),
  logBox: document.getElementById("logBox"),
  refreshBtn: document.getElementById("refreshBtn"),
  startTurnBtn: document.getElementById("startTurnBtn"),
  rollBtn: document.getElementById("rollBtn"),
  statsBtn: document.getElementById("statsBtn"),
  tradeBtn: document.getElementById("tradeBtn"),
  endTurnBtn: document.getElementById("endTurnBtn"),
  viewPlayersBtn: document.getElementById("viewPlayersBtn"),
  openAddPropertyBtn: document.getElementById("openAddPropertyBtn"),
  openAddSpecialBtn: document.getElementById("openAddSpecialBtn"),
  demolishBtn: document.getElementById("demolishBtn"),
  resetBtn: document.getElementById("resetBtn"),
  endGameBtn: document.getElementById("endGameBtn"),
  deleteGameBtn: document.getElementById("deleteGameBtn"),
  modal: document.getElementById("modal"),
  modalTitle: document.getElementById("modalTitle"),
  modalBody: document.getElementById("modalBody"),
  closeModalBtn: document.getElementById("closeModalBtn"),
  modalCard: document.getElementById("modalCard"),
  pendingTradesList: document.getElementById("pendingTradesList"),
  pendingTradesHint: document.getElementById("pendingTradesHint"),
};

function log(msg) {
  console.debug(msg);
}

function escapeHtml(v) {
  return String(v)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function api(url, options = {}) {
  const res = await fetch(url, options);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || data.reason || "Request failed");
  }
  return data;
}

async function loadGames() {
  const data = await api("/api/games/running");
  state.games = data.games || [];
  el.gameSelect.innerHTML = "";
  if (!state.games.length) {
    const o = document.createElement("option");
    o.textContent = "No running games";
    o.value = "";
    el.gameSelect.appendChild(o);
    return;
  }
  state.games.forEach((g) => {
    const o = document.createElement("option");
    o.value = String(g.game_id);
    o.textContent = `Game ${g.game_id}`;
    el.gameSelect.appendChild(o);
  });
  state.currentGameId = Number(el.gameSelect.value);
}

function coordsByIndex(index) {
  if (index <= 10) return [10, 10 - index];
  if (index <= 20) return [20 - index, 0];
  if (index <= 30) return [0, index - 20];
  return [index - 30, 10];
}

function boardMap() {
  const map = Array.from({ length: 11 }, () => Array(11).fill(null));
  for (let idx = 0; idx < 40; idx += 1) {
    const [r, c] = coordsByIndex(idx);
    map[r][c] = idx;
  }
  return map;
}

function renderBoard() {
  const byIndex = new Map(state.board.map((s) => [s.index_no, s]));
  const playerByIndex = new Map();
  state.players.forEach((p, i) => {
    const idx = Number(p.index_no ?? 0);
    if (!playerByIndex.has(idx)) playerByIndex.set(idx, []);
    playerByIndex.get(idx).push({ ...p, color: state.tokenColors[i % state.tokenColors.length] });
  });

  const map = boardMap();
  el.board.innerHTML = "";
  for (let r = 0; r < 11; r += 1) {
    for (let c = 0; c < 11; c += 1) {
      const idx = map[r][c];
      const cell = document.createElement("div");
      if (idx === null) {
        cell.className = "space";
        cell.style.background = "var(--panel-soft)";
        cell.style.border = "none";
        el.board.appendChild(cell);
        continue;
      }
      const space = byIndex.get(idx) || { index_no: idx, name: `Space ${idx}`, type: "blank" };
      const corner = [0, 10, 20, 30].includes(idx) ? "corner" : "";
      cell.className = `space ${space.type} ${corner}`.trim();
      cell.id = `space-${idx}`;
      if (space.propSet) {
        cell.dataset.propset = String(space.propSet).toLowerCase();
      }
      let badgeHtml = "";
      if (space.type === "property") {
        const ps = space.propSet ? String(space.propSet) : "(no propSet)";
        badgeHtml = `<div class="prop-badge" title="Property set">${escapeHtml(ps)}</div>`;
      }
      cell.innerHTML = `<div class="idx">#${idx}</div><div class="name">${escapeHtml(space.name)}</div>${badgeHtml}`;
      if (space.owner_player_id) {
        const ownerIdx = state.players.findIndex((p) => p.player_id === Number(space.owner_player_id));
        if (ownerIdx >= 0) {
          const ownerColor = state.tokenColors[ownerIdx % state.tokenColors.length];
          cell.style.boxShadow = `inset 0 0 0 3px ${ownerColor}`;
        }
      }
      if (state.purchaseHighlightIndex === idx) {
        cell.classList.add("cell-purchase-pulse");
      }
      const tokenWrap = document.createElement("div");
      (playerByIndex.get(idx) || []).forEach((p) => {
        const t = document.createElement("span");
        t.className = "token";
        t.style.background = p.color;
        t.title = `${p.name} (ID ${p.player_id})`;
        tokenWrap.appendChild(t);
      });
      cell.appendChild(tokenWrap);
      el.board.appendChild(cell);
    }
  }
}

function renderPlayers() {
  el.playerSelect.innerHTML = "";
  state.players.forEach((p) => {
    const o = document.createElement("option");
    o.value = String(p.player_id);
    o.textContent = `${p.name} (#${p.player_id})`;
    el.playerSelect.appendChild(o);
  });
  if (state.players.length && !state.currentPlayerId) {
    state.currentPlayerId = state.players[0].player_id;
    el.playerSelect.value = String(state.currentPlayerId);
  }
}

function setPlayerActionState(enabled) {
  [el.rollBtn, el.statsBtn, el.tradeBtn, el.endTurnBtn].forEach((btn) => {
    btn.disabled = !enabled;
  });
  state.turnActive = enabled;
  if (!enabled) {
    document.body.className = "theme-admin";
    el.turnHint.textContent = "Start a player's turn from the Admin Hub.";
    el.ownedPanel.classList.add("hidden");
    el.ownedPanel.innerHTML = "";
    if (state.pendingPollId) {
      clearInterval(state.pendingPollId);
      state.pendingPollId = null;
    }
    el.pendingTradesList.innerHTML = "";
    if (el.pendingTradesHint) el.pendingTradesHint.textContent = "Start a turn to see incoming offers.";
  } else {
    refreshPendingTrades();
    if (!state.pendingPollId) {
      state.pendingPollId = setInterval(refreshPendingTrades, 8000);
    }
  }
}

async function loadOwnedPropertiesPanel() {
  if (!state.currentGameId || !state.currentPlayerId || !state.turnActive) return;
  const data = await api(
    `/api/game/${state.currentGameId}/player/${state.currentPlayerId}/owned_properties`
  );
  const groups = data.groups || {};
  const groupNames = Object.keys(groups);
  if (!groupNames.length) {
    el.ownedPanel.innerHTML = "<div class='muted'>No owned properties.</div>";
    el.ownedPanel.classList.remove("hidden");
    return;
  }
  let html = "";
  groupNames.forEach((group) => {
    html += `<div class="group-title">${escapeHtml(group)}</div>`;
    groups[group].forEach((p) => {
      const houses = Number(p.houses || 0);
      const mortgaged = Boolean(p.isMortgaged);
      const upIcon = houses >= 4 ? ICON.hotel : ICON.house;
      const mortgageBtn = houses === 0
        ? `<button type="button" class="${mortgaged ? "btn-green" : "btn-red"} mortgage-btn" data-id="${p.property_id}"><img src="${ICON.mortgage}" class="btn-icon" alt=""> ${mortgaged ? "Unmortgage" : "Mortgage"}</button>`
        : `<span class="muted">Mortgage N/A</span>`;
      html += `
        <div class="owned-row">
          <span>${escapeHtml(p.name)} (H:${houses}) R:$${p.effective_rent}</span>
          <button type="button" class="btn-green house-up-btn" data-id="${p.property_id}"><img src="${upIcon}" class="btn-icon" alt=""> +</button>
          <button type="button" class="btn-red house-down-btn" data-id="${p.property_id}"><img src="${ICON.house}" class="btn-icon" alt=""> −</button>
          ${mortgageBtn}
        </div>
      `;
    });
  });
  el.ownedPanel.innerHTML = html;
  el.ownedPanel.classList.remove("hidden");

  el.ownedPanel.querySelectorAll(".house-up-btn").forEach((btn) => {
    btn.addEventListener("click", () => propertyAction("upgrade_house", Number(btn.dataset.id)));
  });
  el.ownedPanel.querySelectorAll(".house-down-btn").forEach((btn) => {
    btn.addEventListener("click", () => propertyAction("downgrade_house", Number(btn.dataset.id)));
  });
  el.ownedPanel.querySelectorAll(".mortgage-btn").forEach((btn) => {
    btn.addEventListener("click", () => propertyAction("toggle_mortgage", Number(btn.dataset.id)));
  });
}

async function propertyAction(action, propertyId) {
  if (!state.currentGameId || !state.currentPlayerId) return;
  try {
    await api(`/api/game/${state.currentGameId}/property/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_id: state.currentPlayerId, property_id: propertyId }),
    });
    await loadGameData(state.currentGameId);
    await loadOwnedPropertiesPanel();
  } catch (err) {
    log(`Property action failed: ${err.message}`);
  }
}

async function loadGameData(gameId) {
  if (!gameId) return;
  const [boardRes, playerRes] = await Promise.all([
    api(`/api/game/${gameId}/board`),
    api(`/api/game/${gameId}/players`),
  ]);
  state.board = boardRes.spaces || [];
  state.players = playerRes.players || [];
  renderPlayers();
  renderBoard();
  await loadGameLog();
}

async function loadGameLog() {
  if (!state.currentGameId) return;
  try {
    const data = await api(`/api/game/${state.currentGameId}/log/recent?limit=40`);
    const lines = (data.entries || [])
      .map(
        (e) =>
          `<div class="log-line"><span class="muted">${escapeHtml(String(e.event_time || ""))}</span> <strong>${escapeHtml(String(e.eventType || ""))}</strong> — ${escapeHtml(String(e.eventDescription || ""))}</div>`
      )
      .join("");
    el.logBox.innerHTML = lines || "<div class='muted'>No log entries yet.</div>";
  } catch {
    /* keep local log if API fails */
  }
}

function setThemeForPlayer(playerId) {
  const idx = Math.max(1, (state.players.findIndex((p) => p.player_id === playerId) % 3) + 1);
  document.body.className = `theme-player-${idx}`;
  el.turnHint.textContent = `Turn in progress for Player ${playerId}.`;
}

function openModal(title, html, options = {}) {
  el.modalTitle.textContent = title;
  el.modalBody.innerHTML = html;
  el.modalCard.classList.toggle("modal-wide", Boolean(options.wide));
  el.modal.classList.remove("hidden");
}

function closeModal() {
  el.modal.classList.add("hidden");
  el.modalCard.classList.remove("modal-wide");
}

async function refreshPendingTrades() {
  if (!state.currentGameId || !state.currentPlayerId || !state.turnActive) {
    el.pendingTradesList.innerHTML = "";
    return;
  }
  try {
    const data = await api(
      `/api/game/${state.currentGameId}/trade/incoming?player_id=${state.currentPlayerId}`
    );
    const trades = data.trades || [];
    if (el.pendingTradesHint) {
      el.pendingTradesHint.textContent = trades.length
        ? `${trades.length} offer(s) waiting.`
        : "No incoming trades.";
    }
    el.pendingTradesList.innerHTML = trades
      .map(
        (t) =>
          `<button type="button" class="pending-trade-chip" data-tid="${t.trade_id}">From ${escapeHtml(t.proposer_name)} · #$${t.trade_id} · $${t.offeredCash} / $${t.requestedCash}</button>`
      )
      .join("");
    el.pendingTradesList.querySelectorAll(".pending-trade-chip").forEach((btn) => {
      btn.addEventListener("click", () => openTradeDetail(Number(btn.dataset.tid)));
    });
  } catch {
    /* ignore */
  }
}

async function openTradeDetail(tradeId) {
  if (!state.currentGameId || !state.currentPlayerId) return;
  const data = await api(`/api/game/${state.currentGameId}/trade/${tradeId}`);
  const t = data.trade;
  const offers = data.offer_properties || [];
  const reqs = data.request_properties || [];
  const recvCash = Number(t.offeredCash || 0);
  const giveCash = Number(t.requestedCash || 0);
  const recvProps = offers.map((p) => `"${p.name}" (${p.propSet})`).join(", ") || "—";
  const giveProps = reqs.map((p) => `"${p.name}" (${p.propSet})`).join(", ") || "—";

  openModal(
    `Trade #${tradeId}`,
    `
    <p class="muted">From <strong>${escapeHtml(t.proposer_name)}</strong> to you.</p>
    <div style="margin-top:12px;line-height:1.5">
      <p><strong>You receive:</strong> $${recvCash} ${recvProps !== "—" ? "+ " + recvProps : ""}</p>
      <p><strong>You give:</strong> $${giveCash} ${giveProps !== "—" ? "+ " + giveProps : ""}</p>
    </div>
    <div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap;justify-content:center">
      <button type="button" id="tradeAcceptBtn" class="btn-green">Accept</button>
      <button type="button" id="tradeDeclineBtn" class="btn-red">Decline</button>
      <button type="button" id="tradeCloseBtn" class="btn-gold">Close</button>
    </div>
    `,
    { wide: false }
  );
  document.getElementById("tradeCloseBtn").addEventListener("click", closeModal);
  document.getElementById("tradeAcceptBtn").addEventListener("click", async () => {
    try {
      await api(`/api/game/${state.currentGameId}/trade/${tradeId}/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: state.currentPlayerId, accept: true }),
      });
      closeModal();
      await loadGameData(state.currentGameId);
      await refreshPendingTrades();
    } catch (err) {
      alert(err.message);
    }
  });
  document.getElementById("tradeDeclineBtn").addEventListener("click", async () => {
    try {
      await api(`/api/game/${state.currentGameId}/trade/${tradeId}/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_id: state.currentPlayerId, accept: false }),
      });
      closeModal();
      await loadGameData(state.currentGameId);
      await refreshPendingTrades();
    } catch (err) {
      alert(err.message);
    }
  });
}

async function openTradeWizard() {
  if (!state.currentGameId || !state.currentPlayerId || !state.turnActive) return;
  const active = await api(`/api/game/${state.currentGameId}/players/active`);
  const others = (active.players || []).filter((p) => p.player_id !== state.currentPlayerId);
  if (!others.length) {
    alert("No other players to trade with.");
    return;
  }
  openModal(
    "Create trade",
    `<p class="muted">Choose a player to trade with:</p>
     <div class="trade-player-pick" id="tradePlayerPick"></div>`,
    { wide: false }
  );
  const pick = document.getElementById("tradePlayerPick");
  others.forEach((p) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "btn-gold";
    b.textContent = `${p.name} (#${p.player_id})`;
    b.addEventListener("click", () => openTradeBuilder(p.player_id, p.name));
    pick.appendChild(b);
  });
}

async function openTradeBuilder(targetId, targetName) {
  const mine = await api(
    `/api/game/${state.currentGameId}/player/${state.currentPlayerId}/owned_properties`
  );
  const theirs = await api(`/api/game/${state.currentGameId}/player/${targetId}/owned_properties`);
  const myProps = mine.properties || [];
  const theirProps = theirs.properties || [];
  const me = state.players.find((p) => p.player_id === state.currentPlayerId);
  const them = state.players.find((p) => p.player_id === targetId);
  const myBal = me ? Number(me.balance || 0) : 0;
  const theirBal = them ? Number(them.balance || 0) : 0;

  const offerChecks = myProps
    .map(
      (p) =>
        `<label><input type="checkbox" name="offer" value="${p.property_id}"> ${escapeHtml(p.name)} (${escapeHtml(p.propSet || "")})</label>`
    )
    .join("<br>");
  const reqChecks = theirProps
    .map(
      (p) =>
        `<label><input type="checkbox" name="req" value="${p.property_id}"> ${escapeHtml(p.name)} (${escapeHtml(p.propSet || "")})</label>`
    )
    .join("<br>");

  openModal(
    `Trade with ${escapeHtml(targetName)}`,
    `
    <div class="trade-split">
      <div class="trade-pane">
        <h4>You offer</h4>
        <div class="small">${offerChecks || "<span class='muted'>No properties</span>"}</div>
        <div class="trade-cash">
          <label>Cash offered ($0–$${myBal})</label>
          <input type="range" id="offerCash" min="0" max="${myBal}" value="0">
          <span id="offerCashVal">0</span>
        </div>
      </div>
      <div class="trade-pane">
        <h4>You request</h4>
        <div class="small">${reqChecks || "<span class='muted'>No properties</span>"}</div>
        <div class="trade-cash">
          <label>Cash requested ($0–$${theirBal})</label>
          <input type="range" id="reqCash" min="0" max="${theirBal}" value="0">
          <span id="reqCashVal">0</span>
        </div>
      </div>
    </div>
    <div class="trade-footer">
      <button type="button" id="sendTradeBtn" class="btn-gold">Send trade</button>
    </div>
    `,
    { wide: true }
  );
  const oEl = document.getElementById("offerCash");
  const rEl = document.getElementById("reqCash");
  const oV = document.getElementById("offerCashVal");
  const rV = document.getElementById("reqCashVal");
  oEl.addEventListener("input", () => {
    oV.textContent = oEl.value;
  });
  rEl.addEventListener("input", () => {
    rV.textContent = rEl.value;
  });
  document.getElementById("sendTradeBtn").addEventListener("click", async () => {
    const offerIds = Array.from(
      document.querySelectorAll('input[name="offer"]:checked')
    ).map((x) => Number(x.value));
    const reqIds = Array.from(document.querySelectorAll('input[name="req"]:checked')).map((x) =>
      Number(x.value)
    );
    try {
      await api(`/api/game/${state.currentGameId}/trade/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          proposer_id: state.currentPlayerId,
          receiver_id: targetId,
          offered_cash: Number(oEl.value),
          requested_cash: Number(rEl.value),
          offer_property_ids: offerIds,
          request_property_ids: reqIds,
        }),
      });
      closeModal();
      await loadGameData(state.currentGameId);
    } catch (err) {
      alert(err.message);
    }
  });
}

async function init() {
  try {
    await loadGames();
    if (state.games.length) {
      await loadGameData(state.currentGameId);
    }
    setPlayerActionState(false);
  } catch (err) {
    console.error(err);
    alert(`Startup error: ${err.message}`);
  }
}

el.refreshBtn.addEventListener("click", async () => {
  await loadGames();
  if (state.currentGameId) await loadGameData(state.currentGameId);
});

el.gameSelect.addEventListener("change", async (e) => {
  state.currentGameId = Number(e.target.value);
  state.currentPlayerId = null;
  await loadGameData(state.currentGameId);
});

el.playerSelect.addEventListener("change", (e) => {
  state.currentPlayerId = Number(e.target.value);
});

el.startTurnBtn.addEventListener("click", () => {
  if (!state.currentPlayerId || !state.currentGameId) return;
  api(`/api/game/${state.currentGameId}/turn/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ player_id: state.currentPlayerId }),
  })
    .then(() => {
      setThemeForPlayer(state.currentPlayerId);
      setPlayerActionState(true);
      log(`Turn started for Player ${state.currentPlayerId}.`);
      loadOwnedPropertiesPanel().catch((err) => log(`Could not load properties: ${err.message}`));
    })
    .catch((err) => log(`Could not start turn: ${err.message}`));
});

el.rollBtn.addEventListener("click", async () => {
  if (!state.currentGameId || !state.currentPlayerId) return;
  try {
    const data = await api(`/api/game/${state.currentGameId}/roll`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_id: state.currentPlayerId }),
    });
    const d = data.dice;
    const p = state.players.find((x) => x.player_id === state.currentPlayerId);
    if (p) p.index_no = data.new_index;
    renderBoard();
    await loadOwnedPropertiesPanel();
    await loadGameLog();
    if (data.card_result && data.card_result.description) {
      openModal(
        data.destination && data.destination.type === "chance" ? "Chance" : "Community Chest",
        `<p>${escapeHtml(data.card_result.description)}</p><button type="button" id="cardOkBtn" class="btn-gold">OK</button>`,
        { wide: false }
      );
      document.getElementById("cardOkBtn").addEventListener("click", closeModal);
    }
    if (data.action_required && data.action_required.type === "buy_property") {
      const a = data.action_required;
      openModal(
        "Buy Property",
        `
        <p>Buy <strong>${escapeHtml(a.name)}</strong> for <strong>$${a.cost}</strong>?</p>
        <button type="button" id="buyYesBtn" class="btn-gold">Buy</button>
        <button type="button" id="buyNoBtn" class="btn-gold">Skip</button>
        `
      );
      document.getElementById("buyYesBtn").addEventListener("click", () => resolveBuy(true));
      document.getElementById("buyNoBtn").addEventListener("click", () => resolveBuy(false));
    }
  } catch (err) {
    alert(`Roll failed: ${err.message}`);
  }
});

async function resolveBuy(accept) {
  if (!state.currentGameId || !state.currentPlayerId) return;
  try {
    const out = await api(`/api/game/${state.currentGameId}/buy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_id: state.currentPlayerId, accept }),
    });
    closeModal();
    state.purchaseHighlightIndex = null;
    if (out.ok && out.accepted && out.space_index != null) {
      state.purchaseHighlightIndex = out.space_index;
      setTimeout(() => {
        state.purchaseHighlightIndex = null;
        renderBoard();
      }, 3500);
    }
    await loadGameData(state.currentGameId);
    await loadGameLog();
  } catch (err) {
    alert(`Buy action failed: ${err.message}`);
  }
}

el.statsBtn.addEventListener("click", async () => {
  if (!state.currentGameId || !state.currentPlayerId) return;
  try {
    const data = await api(`/api/game/${state.currentGameId}/player/${state.currentPlayerId}/stats`);
    const p = data.player;
    const props = data.properties || [];
    const propHtml = props.length
      ? `<ul>${props.map((x) => `<li>${x.name} (${x.propSet})</li>`).join("")}</ul>`
      : "<p>No properties owned.</p>";
    openModal(
      `${p.name} - Stats`,
      `<p>Balance: $${p.balance}</p><p>Position: ${p.index_no ?? 0}</p><h4>Properties</h4>${propHtml}`
    );
  } catch (err) {
    log(`Stats failed: ${err.message}`);
  }
});

el.tradeBtn.addEventListener("click", () => {
  openTradeWizard().catch((err) => alert(err.message));
});

el.endTurnBtn.addEventListener("click", async () => {
  if (!state.currentGameId || !state.currentPlayerId) return;
  try {
    await api(`/api/game/${state.currentGameId}/turn/end`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_id: state.currentPlayerId }),
    });
    setPlayerActionState(false);
    await loadGameData(state.currentGameId);
    await loadGameLog();
  } catch (err) {
    alert(`End turn failed: ${err.message}`);
  }
});

el.newGameBtn.addEventListener("click", async () => {
  try {
    const out = await api("/api/admin/start_game", { method: "POST" });
    await loadGames();
    state.currentGameId = out.game_id;
    el.gameSelect.value = String(out.game_id);
    state.currentPlayerId = null;
    await loadGameData(state.currentGameId);
    log(`Created Game ${out.game_id}.`);
  } catch (err) {
    log(`Could not create game: ${err.message}`);
  }
});

function confirmPrompt(message, onYes) {
  openModal(
    "Confirm",
    `<p>${escapeHtml(message)}</p><button type="button" id="confirmYesBtn" class="btn-gold">Confirm</button> <button type="button" id="confirmNoBtn" class="btn-gold">Cancel</button>`
  );
  document.getElementById("confirmYesBtn").addEventListener("click", () => {
    closeModal();
    onYes();
  });
  document.getElementById("confirmNoBtn").addEventListener("click", closeModal);
}

async function showPlayersOverlay() {
  if (!state.currentGameId) return;
  const data = await api(`/api/game/${state.currentGameId}/players/active`);
  const rows = (data.players || [])
    .map(
      (p) => `<tr>
      <td>${p.player_id}</td>
      <td>${escapeHtml(p.name)}</td>
      <td>$${p.balance}</td>
      <td>${p.index_no ?? 0}</td>
      <td><button class="remove-player-btn" data-id="${p.player_id}">-</button></td>
    </tr>`
    )
    .join("");
  openModal(
    "Active Players",
    `<div><button id="addPlayerBtn">+ Add Player Mid-Game</button></div>
     <table class="table">
       <thead><tr><th>ID</th><th>Name</th><th>Balance</th><th>Index</th><th>Action</th></tr></thead>
       <tbody>${rows}</tbody>
     </table>`
  );
  document.getElementById("addPlayerBtn").addEventListener("click", () => {
    const name = prompt("Enter new player name:");
    if (!name || !name.trim()) return;
    api("/api/admin/register_player", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ game_id: state.currentGameId, name: name.trim() }),
    })
      .then(async () => {
        await loadGameData(state.currentGameId);
        await showPlayersOverlay();
      })
      .catch((err) => log(`Add player failed: ${err.message}`));
  });
  document.querySelectorAll(".remove-player-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const pid = Number(btn.dataset.id);
      confirmPrompt(`Eliminate Player ${pid}?`, async () => {
        try {
          await api("/api/admin/eliminate_player", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ game_id: state.currentGameId, player_id: pid }),
          });
          await loadGameData(state.currentGameId);
          await showPlayersOverlay();
        } catch (err) {
          log(`Eliminate failed: ${err.message}`);
        }
      });
    });
  });
}

el.viewPlayersBtn.addEventListener("click", () => {
  showPlayersOverlay().catch((err) => log(`Could not load players: ${err.message}`));
});

el.openAddPropertyBtn.addEventListener("click", () => {
  openModal(
    "Add New Property Space",
    `
    <label>Index <input id="propIndex" type="number" min="0" max="39"></label><br><br>
    <label>Name <input id="propName" type="text"></label><br><br>
    <label>Set <input id="propSet" type="text"></label><br><br>
    <label>Cost <input id="propCost" type="number" min="0"></label><br><br>
    <label>Rent <input id="propRent" type="number" min="0"></label><br><br>
    <button id="savePropertyBtn">Save Property</button>
    `
  );
  document.getElementById("savePropertyBtn").addEventListener("click", async () => {
    try {
      await api("/api/admin/add_property", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          game_id: state.currentGameId,
          index_no: Number(document.getElementById("propIndex").value),
          name: document.getElementById("propName").value,
          prop_set: document.getElementById("propSet").value,
          cost: Number(document.getElementById("propCost").value),
          rent: Number(document.getElementById("propRent").value),
        }),
      });
      closeModal();
      await loadGameData(state.currentGameId);
      log("Property space saved.");
    } catch (err) {
      log(`Add property failed: ${err.message}`);
    }
  });
});

el.openAddSpecialBtn.addEventListener("click", () => {
  openModal(
    "Add New Action Boardspace",
    `
    <label>Index <input id="spIndex" type="number" min="0" max="39"></label><br><br>
    <label>Type
      <select id="spType">
        <option value="tax">tax</option>
        <option value="chance">chance</option>
        <option value="chest">chest</option>
        <option value="jail">jail</option>
        <option value="free">free</option>
      </select>
    </label><br><br>
    <label>Name <input id="spName" type="text"></label><br><br>
    <label>Tax Amount (optional) <input id="spTax" type="number" min="0" value="0"></label><br><br>
    <button id="saveSpecialBtn">Save Space</button>
    `
  );
  document.getElementById("saveSpecialBtn").addEventListener("click", async () => {
    try {
      await api("/api/admin/add_special_space", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          game_id: state.currentGameId,
          index_no: Number(document.getElementById("spIndex").value),
          type: document.getElementById("spType").value,
          name: document.getElementById("spName").value,
          tax_amount: Number(document.getElementById("spTax").value || 0),
        }),
      });
      closeModal();
      await loadGameData(state.currentGameId);
      log("Action boardspace saved.");
    } catch (err) {
      log(`Add action boardspace failed: ${err.message}`);
    }
  });
});

el.demolishBtn.addEventListener("click", () => {
  const spaceIdRaw = prompt("Enter Space ID to demolish:");
  if (!spaceIdRaw) return;
  const spaceId = Number(spaceIdRaw);
  confirmPrompt(`Demolish property at Space ID ${spaceId}?`, async () => {
    try {
      await api("/api/admin/demolish_property", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ game_id: state.currentGameId, space_id: spaceId }),
      });
      await loadGameData(state.currentGameId);
      log(`Space ${spaceId} demolished.`);
    } catch (err) {
      log(`Demolish failed: ${err.message}`);
    }
  });
});

el.resetBtn.addEventListener("click", () => {
  confirmPrompt("Reset this game to initial state?", async () => {
    try {
      await api("/api/admin/reset_game", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ game_id: state.currentGameId }),
      });
      setPlayerActionState(false);
      await loadGameData(state.currentGameId);
      log("Game reset.");
    } catch (err) {
      log(`Reset failed: ${err.message}`);
    }
  });
});

el.endGameBtn.addEventListener("click", () => {
  confirmPrompt("End this game? No more turns should be allowed.", async () => {
    try {
      await api("/api/admin/end_game", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ game_id: state.currentGameId }),
      });
      log("Game ended.");
      await loadGames();
    } catch (err) {
      log(`End game failed: ${err.message}`);
    }
  });
});

el.deleteGameBtn.addEventListener("click", () => {
  confirmPrompt("Permanently delete this game and all its data?", async () => {
    try {
      await api("/api/admin/delete_game", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ game_id: state.currentGameId }),
      });
      setPlayerActionState(false);
      await loadGames();
      if (state.currentGameId) await loadGameData(state.currentGameId);
      log("Game data erased.");
    } catch (err) {
      log(`Delete game failed: ${err.message}`);
    }
  });
});

el.closeModalBtn.addEventListener("click", closeModal);
el.modal.addEventListener("click", (e) => {
  if (e.target === el.modal) closeModal();
});

init();
