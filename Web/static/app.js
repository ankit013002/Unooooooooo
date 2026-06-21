const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const ui = {
  home: $("#home-view"),
  lobby: $("#lobby-view"),
  game: $("#game-view"),
  createForm: $("#create-form"),
  joinForm: $("#join-form"),
  createName: $("#create-name"),
  joinName: $("#join-name"),
  roomInput: $("#room-code"),
  humanSeats: $("#human-seats"),
  botSeats: $("#bot-seats"),
  lobbyCode: $("#lobby-code"),
  copyRoom: $("#copy-room"),
  lobbyPlayers: $("#lobby-players"),
  seatCount: $("#seat-count"),
  readyButton: $("#ready-button"),
  readyHint: $("#ready-hint"),
  connectionLabel: $("#connection-label"),
  seatTop: $("#seat-top"),
  seatLeft: $("#seat-left"),
  seatRight: $("#seat-right"),
  handZone: $("#hand-zone"),
  turnBanner: $("#turn-banner"),
  pausedBanner: $("#paused-banner"),
  gameRoomCode: $("#game-room-code"),
  drawPile: $("#draw-pile"),
  deckCount: $("#deck-count"),
  discardCard: $("#discard-card"),
  playerHand: $("#player-hand"),
  handCount: $("#hand-count"),
  unoButton: $("#uno-button"),
  colorModal: $("#color-modal"),
  winnerModal: $("#winner-modal"),
  winnerTitle: $("#winner-title"),
  winnerCopy: $("#winner-copy"),
  rematchButton: $("#rematch-button"),
  toast: $("#toast"),
};

let socket = null;
let roomCode = "";
let playerName = "";
let state = null;
let intentionalClose = false;
let reconnectAttempts = 0;
let reconnectTimer = null;
let toastTimer = null;

function showView(name) {
  ui.home.classList.toggle("hidden", name !== "home");
  ui.lobby.classList.toggle("hidden", name !== "lobby");
  ui.game.classList.toggle("hidden", name !== "game");
}

function tokenKey(code) {
  return `uno-token-${code}`;
}

function saveName(name) {
  localStorage.setItem("uno-player-name", name);
}

function normalizeCode(value) {
  return value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 4);
}

function cardUrl(card) {
  return `/assets/cards/${encodeURIComponent(card || "Uno Back")}.png`;
}

function initials(name) {
  return name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

function toast(message) {
  clearTimeout(toastTimer);
  ui.toast.textContent = message;
  ui.toast.classList.remove("hidden");
  toastTimer = setTimeout(() => ui.toast.classList.add("hidden"), 3200);
}

async function createRoom(event) {
  event.preventDefault();
  playerName = ui.createName.value.trim();
  if (!playerName) return;
  const humanSeats = Number(ui.humanSeats.value);
  const botSeats = Number(ui.botSeats.value);
  try {
    const response = await fetch("/api/rooms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ humanSeats, botSeats }),
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Could not create the room");
    saveName(playerName);
    connect(body.code, playerName);
  } catch (error) {
    toast(error.message);
  }
}

function joinRoom(event) {
  event.preventDefault();
  playerName = ui.joinName.value.trim();
  const code = normalizeCode(ui.roomInput.value);
  if (!playerName || code.length !== 4) {
    toast("Enter your name and the four-letter room code.");
    return;
  }
  saveName(playerName);
  connect(code, playerName);
}

function connect(code, name, isReconnect = false) {
  clearTimeout(reconnectTimer);
  intentionalClose = false;
  roomCode = normalizeCode(code);
  playerName = name;
  const token = sessionStorage.getItem(tokenKey(roomCode)) || "";
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const url = `${protocol}://${location.host}/ws/${roomCode}?name=${encodeURIComponent(playerName)}&token=${encodeURIComponent(token)}`;

  if (socket && socket.readyState < WebSocket.CLOSING) socket.close();
  socket = new WebSocket(url);
  location.hash = roomCode;
  ui.lobbyCode.textContent = roomCode;
  ui.gameRoomCode.textContent = `ROOM ${roomCode}`;
  ui.connectionLabel.textContent = isReconnect ? "Reconnecting…" : "Connecting…";
  showView(state?.phase === "game" ? "game" : "lobby");

  socket.addEventListener("open", () => {
    if (socket.url !== url) return;
    reconnectAttempts = 0;
    ui.connectionLabel.textContent = "Connected";
  });

  socket.addEventListener("message", (event) => {
    if (event.currentTarget !== socket) return;
    const message = JSON.parse(event.data);
    if (message.type === "welcome") {
      sessionStorage.setItem(tokenKey(roomCode), message.token);
    } else if (message.type === "state") {
      state = message;
      render();
    } else if (message.type === "error") {
      toast(message.message);
    }
  });

  socket.addEventListener("close", (event) => {
    if (event.currentTarget !== socket) return;
    ui.connectionLabel.textContent = "Disconnected";
    if (intentionalClose) return;
    if (event.code === 4404 || event.code === 4409) {
      toast(event.reason || "That room is unavailable.");
      showView("home");
      return;
    }
    reconnectAttempts += 1;
    const delay = Math.min(1000 * 2 ** (reconnectAttempts - 1), 10000);
    reconnectTimer = setTimeout(() => connect(roomCode, playerName, true), delay);
  });

  socket.addEventListener("error", () => {
    ui.connectionLabel.textContent = "Connection trouble";
  });
}

function send(action, extras = {}) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    toast("Still reconnecting to the table.");
    return;
  }
  socket.send(JSON.stringify({ action, ...extras }));
}

function render() {
  if (!state) return;
  if (state.phase === "lobby") {
    showView("lobby");
    renderLobby();
  } else {
    showView("game");
    renderGame();
  }
}

function renderLobby() {
  const totalSeats = state.players.length + Math.max(0, state.humanSeats - state.players.filter((p) => !p.bot).length);
  ui.seatCount.textContent = `${state.connectedHumans + state.players.filter((p) => p.bot).length} / ${totalSeats}`;
  ui.lobbyPlayers.replaceChildren();

  for (let playerId = 0; playerId < state.humanSeats; playerId += 1) {
    const player = state.players.find((candidate) => candidate.id === playerId);
    ui.lobbyPlayers.append(playerRow(player, false));
  }
  for (const player of state.players.filter((candidate) => candidate.bot)) {
    ui.lobbyPlayers.append(playerRow(player, true));
  }

  ui.readyButton.disabled = state.ready || state.connectedHumans < state.humanSeats;
  ui.readyButton.textContent = state.ready ? "Ready ✓" : "I’m ready";
  ui.readyButton.classList.toggle("ready-confirmed", state.ready);
  ui.readyHint.textContent = state.connectedHumans < state.humanSeats
    ? `Waiting for ${state.humanSeats - state.connectedHumans} more human player${state.humanSeats - state.connectedHumans === 1 ? "" : "s"}.`
    : "The game begins when every human is ready.";
}

function playerRow(player, bot) {
  const row = document.createElement("div");
  row.className = "player-row";
  if (!player) {
    row.innerHTML = `<div class="avatar">?</div><div><strong>Open human seat</strong><small>Share the room code</small></div><span class="seat-status waiting">Waiting</span>`;
    return row;
  }
  const me = player.id === state.playerId ? " (you)" : "";
  row.innerHTML = `
    <div class="avatar ${bot ? "bot" : ""}">${bot ? "🦙" : initials(player.name)}</div>
    <div><strong>${escapeHtml(player.name)}${me}</strong><small>${bot ? "Llama-powered player" : player.connected ? "At the table" : "Reconnecting"}</small></div>
    <span class="seat-status ${player.ready || bot ? "" : "waiting"}">${player.ready || bot ? "Ready" : "Not ready"}</span>`;
  return row;
}

function renderGame() {
  const current = state.players.find((player) => player.id === state.currentTurn);
  const myTurn = state.currentTurn === state.playerId && !state.paused;
  ui.turnBanner.textContent = state.paused
    ? "Waiting for reconnection"
    : state.botThinking !== null
      ? `${state.players.find((p) => p.id === state.botThinking)?.name || "Llama"} is thinking…`
      : myTurn
        ? "Your turn"
        : `${current?.name || "Player"}’s turn`;
  ui.turnBanner.classList.toggle("yours", myTurn);
  ui.handZone.classList.toggle("your-turn", myTurn);
  ui.pausedBanner.classList.toggle("hidden", !state.paused);
  ui.gameRoomCode.textContent = `ROOM ${state.roomCode}`;

  ui.seatTop.replaceChildren();
  ui.seatLeft.replaceChildren();
  ui.seatRight.replaceChildren();

  const opponents = state.players.filter((p) => p.id !== state.playerId);

  function seatPlayerEl(player) {
    const el = document.createElement("div");
    el.className = `seat-player ${player.id === state.currentTurn ? "active" : ""}`;
    const maxCards = Math.min(player.cardCount || 0, 7);
    const fanCards = Array.from({ length: maxCards }, (_, i) =>
      `<img class="fan-card" src="${cardUrl(null)}" alt="" style="--i:${i}">`
    ).join("");
    el.innerHTML = `
      <div class="seat-player-cards">${fanCards}</div>
      <div class="seat-player-info">
        <div class="avatar ${player.bot ? "bot" : ""}">${player.bot ? "🦙" : initials(player.name)}</div>
        <div><strong>${escapeHtml(player.name)}</strong><small>${player.cardCount} card${player.cardCount === 1 ? "" : "s"}${player.connected ? "" : " · offline"}</small></div>
      </div>
      ${state.botThinking === player.id ? '<span class="thinking-dot">THINKING</span>' : ""}`;
    return el;
  }

  if (opponents.length === 1) {
    ui.seatTop.append(seatPlayerEl(opponents[0]));
  } else if (opponents.length === 2) {
    ui.seatLeft.append(seatPlayerEl(opponents[0]));
    ui.seatRight.append(seatPlayerEl(opponents[1]));
  } else {
    ui.seatLeft.append(seatPlayerEl(opponents[0]));
    ui.seatTop.append(seatPlayerEl(opponents[1]));
    ui.seatRight.append(seatPlayerEl(opponents[2]));
  }

  ui.deckCount.textContent = `${state.deckCount} cards`;
  ui.drawPile.disabled = !myTurn || state.pendingColor;
  ui.discardCard.src = cardUrl(state.topCard);
  ui.discardCard.alt = state.topCard || "Top discard";
  ui.handCount.textContent = `${state.hand.length} card${state.hand.length === 1 ? "" : "s"}`;

  ui.playerHand.replaceChildren();
  state.hand.forEach((card, index) => {
    const playable = myTurn && state.legalCards.includes(card) && !state.pendingColor;
    const button = document.createElement("button");
    button.className = `hand-card ${playable ? "playable" : ""}`;
    button.type = "button";
    button.disabled = !playable;
    button.title = playable ? `Play ${card}` : card;
    button.setAttribute("aria-label", playable ? `Play ${card}` : card);
    button.innerHTML = `<img src="${cardUrl(card)}" alt="${escapeHtml(card)}" draggable="false" />`;
    if (playable) button.addEventListener("click", () => send("play", { card, index }));
    ui.playerHand.append(button);
  });

  ui.unoButton.classList.toggle("hidden", !(myTurn && state.hand.length === 2 && state.legalCards.length));
  ui.colorModal.classList.toggle("hidden", !state.pendingColor);

  const finished = state.phase === "finished";
  ui.winnerModal.classList.toggle("hidden", !finished);
  if (finished) {
    const won = state.winnerId === state.playerId;
    ui.winnerTitle.textContent = won ? "You won!" : `${state.winnerName} wins!`;
    ui.winnerCopy.textContent = won
      ? "Clean, decisive, and definitely not suspicious."
      : state.players.find((player) => player.id === state.winnerId)?.bot
        ? "The llama requests that you respect its superior card sense."
        : "A rematch seems like the only reasonable response.";
    ui.rematchButton.disabled = state.ready;
    ui.rematchButton.textContent = state.ready ? "Ready — waiting…" : "Ready for a rematch";
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function copyInvite() {
  const invite = `${location.origin}/#${roomCode}`;
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(invite).then(
      () => toast("Invite link copied."),
      () => fallbackCopy(invite),
    );
  } else {
    fallbackCopy(invite);
  }
}

function fallbackCopy(value) {
  const field = document.createElement("textarea");
  field.value = value;
  field.style.position = "fixed";
  field.style.opacity = "0";
  document.body.append(field);
  field.select();
  const copied = document.execCommand("copy");
  field.remove();
  toast(copied ? "Invite link copied." : `Share this room code: ${roomCode}`);
}

function leaveRoom() {
  intentionalClose = true;
  clearTimeout(reconnectTimer);
  ui.winnerModal.classList.add("hidden");
  ui.colorModal.classList.add("hidden");
  const departingSocket = socket;
  if (departingSocket?.readyState === WebSocket.OPEN) {
    departingSocket.send(JSON.stringify({ action: "leave" }));
    setTimeout(() => departingSocket.close(), 80);
  } else if (departingSocket) {
    departingSocket.close();
  }
  socket = null;
  state = null;
  history.replaceState(null, "", location.pathname);
  showView("home");
}

ui.createForm.addEventListener("submit", createRoom);
ui.joinForm.addEventListener("submit", joinRoom);
ui.roomInput.addEventListener("input", () => { ui.roomInput.value = normalizeCode(ui.roomInput.value); });
ui.readyButton.addEventListener("click", () => send("ready"));
ui.drawPile.addEventListener("click", () => send("draw"));
ui.unoButton.addEventListener("click", () => send("uno"));
ui.rematchButton.addEventListener("click", () => send("rematch"));
ui.copyRoom.addEventListener("click", copyInvite);
ui.gameRoomCode.addEventListener("click", copyInvite);
$$('[data-color]').forEach((button) => button.addEventListener("click", () => send("color", { color: button.dataset.color })));
$$('[data-leave]').forEach((button) => button.addEventListener("click", leaveRoom));

const rememberedName = localStorage.getItem("uno-player-name") || "";
ui.createName.value = rememberedName;
ui.joinName.value = rememberedName;
const linkedCode = normalizeCode(location.hash.slice(1));
if (linkedCode.length === 4) {
  ui.roomInput.value = linkedCode;
  const token = sessionStorage.getItem(tokenKey(linkedCode));
  if (token && rememberedName) connect(linkedCode, rememberedName, true);
  else ui.joinName.focus();
}
