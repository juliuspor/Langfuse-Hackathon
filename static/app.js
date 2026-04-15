const form = document.querySelector("#debate-form");
const startButton = document.querySelector("#start-button");
const statusText = document.querySelector("#status-text");
const liveDot = document.querySelector("#live-dot");
const conversationId = document.querySelector("#conversation-id");
const turnList = document.querySelector("#turn-list");
const player = document.querySelector("#turn-player");

const speakerNames = {
  agent_1: "Lanz",
  agent_2: "Precht",
};

let source = null;
let audioQueue = [];
let currentTurn = null;
let isAudioBusy = false;
let streamDone = false;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await startLiveDebate(new FormData(form));
});

player.addEventListener("ended", () => {
  finishCurrentAudio("gespielt");
});

player.addEventListener("error", () => {
  finishCurrentAudio("uebersprungen");
});

async function startLiveDebate(formData) {
  if (source) {
    source.close();
  }

  audioQueue = [];
  currentTurn = null;
  isAudioBusy = false;
  streamDone = false;
  player.removeAttribute("src");
  player.load();
  turnList.replaceChildren();
  conversationId.textContent = "";
  setStatus("Verbindung steht. Die erste Stimme kommt gleich.", true);
  startButton.disabled = true;
  startButton.textContent = "Live...";
  await primeAudio();

  const params = new URLSearchParams({
    topic: formData.get("topic"),
    turns: formData.get("turns"),
    language: "de",
    include_audio: "true",
  });

  source = new EventSource(`/api/debate/live?${params.toString()}`);

  source.addEventListener("connected", () => {
    setStatus("Sendung wird vorbereitet.", true);
  });

  source.addEventListener("conversation", (event) => {
    const data = JSON.parse(event.data);
    conversationId.textContent = data.conversation_id;
    setStatus("On air.", true);
  });

  source.addEventListener("turn", (event) => {
    const turn = JSON.parse(event.data);
    renderTurn(turn);
    enqueueAudio(turn);
  });

  source.addEventListener("completed", () => {
    streamDone = true;
    closeSource();
    setDoneStatus();
  });

  source.addEventListener("error", (event) => {
    if (event.data) {
      const data = JSON.parse(event.data);
      setStatus(data.message || "Die Live-Verbindung ist abgebrochen.", false);
    } else if (!streamDone) {
      setStatus("Die Live-Verbindung ist abgebrochen.", false);
    }
    closeSource();
    startButton.disabled = false;
    startButton.textContent = "Live starten";
  });
}

async function primeAudio() {
  const silence = new Audio(
    "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAA="
  );
  try {
    await silence.play();
    silence.pause();
  } catch (error) {
    // The visible player still lets the user continue if the browser blocks autoplay.
  }
}

function renderTurn(turn) {
  const item = document.createElement("li");
  item.className = `turn-card ${turn.speaker}`;
  item.dataset.turnIndex = turn.turn_index;

  const speaker = document.createElement("p");
  speaker.className = "speaker";
  speaker.textContent = `${speakerNames[turn.speaker] || turn.speaker} - Turn ${turn.turn_index}`;

  const text = document.createElement("p");
  text.className = "turn-text";
  text.textContent = turn.text;

  const audioState = document.createElement("p");
  audioState.className = "audio-state";
  audioState.textContent = turn.audio_url ? "Audio bereit." : "Nur Text.";

  item.append(speaker, text, audioState);
  turnList.append(item);
  item.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function enqueueAudio(turn) {
  if (!turn.audio_url) {
    return;
  }
  audioQueue.push(turn);
  playNextTurn();
}

async function playNextTurn() {
  if (isAudioBusy || audioQueue.length === 0) {
    setDoneStatus();
    return;
  }

  isAudioBusy = true;
  currentTurn = audioQueue.shift();
  markTurn(currentTurn.turn_index, "spielt");
  setStatus(`${speakerNames[currentTurn.speaker] || currentTurn.speaker} spricht.`, true);

  player.src = currentTurn.audio_url;
  player.load();

  try {
    await player.play();
  } catch (error) {
    markTurn(currentTurn.turn_index, "bereit");
    setStatus("Audio ist bereit. Druecke Play im Player.", true);
  }
}

function finishCurrentAudio(label) {
  if (currentTurn) {
    markTurn(currentTurn.turn_index, label);
  }
  currentTurn = null;
  isAudioBusy = false;
  playNextTurn();
}

function markTurn(turnIndex, label) {
  const item = turnList.querySelector(`[data-turn-index="${turnIndex}"]`);
  if (!item) {
    return;
  }
  const state = item.querySelector(".audio-state");
  state.textContent = `Audio ${label}.`;
  item.classList.toggle("is-playing", label === "spielt");
}

function setDoneStatus() {
  if (!streamDone) {
    return;
  }
  if (isAudioBusy || audioQueue.length > 0) {
    setStatus("Alle Turns sind da. Audio laeuft weiter.", true);
    return;
  }
  setStatus("Debatte beendet.", false);
  startButton.disabled = false;
  startButton.textContent = "Live starten";
}

function setStatus(message, isLive) {
  statusText.textContent = message;
  liveDot.classList.toggle("is-live", isLive);
}

function closeSource() {
  if (source) {
    source.close();
    source = null;
  }
}
