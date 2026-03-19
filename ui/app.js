// ===== State =====
const state = {
  recording: false,
  recognition: null,
  transcriptLines: [],
  recordingStart: null,
};

// ===== DOM refs =====
const btnStart        = document.getElementById('btn-start');
const btnStop         = document.getElementById('btn-stop');
const statusDot       = document.getElementById('status-dot');
const statusText      = document.getElementById('status-text');
const transcriptEl    = document.getElementById('transcript');
const actionList      = document.getElementById('action-list');
const participantsGrid = document.getElementById('participants-grid');
const toast           = document.getElementById('toast');

// ===== Speech API Detection =====
const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;

if (!SpeechRecognitionAPI) {
  btnStart.disabled = true;
  statusText.textContent = 'Speech API not supported. Please use Chrome or Edge.';
  statusText.classList.add('status-error');
}

// ===== Timestamp Helper =====
function getElapsedTimestamp() {
  const elapsed = state.recordingStart ? Math.floor((Date.now() - state.recordingStart) / 1000) : 0;
  const h = String(Math.floor(elapsed / 3600)).padStart(2, '0');
  const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
  const s = String(elapsed % 60).padStart(2, '0');
  return `[${h}:${m}:${s}]`;
}

// ===== Transcript Helpers =====
function appendTranscriptLine(text) {
  const line = `${getElapsedTimestamp()} ${text}`;
  state.transcriptLines.push(line);
  transcriptEl.value = state.transcriptLines.join('\n');
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

function updateInterim(interimText) {
  const base = state.transcriptLines.join('\n');
  transcriptEl.value = interimText
    ? base + (base ? '\n' : '') + `… ${interimText}`
    : base;
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

// ===== Action Items =====
// Keywords without trailing spaces; matched as whole words/phrases via regex below.
const ACTION_KEYWORDS = [
  'will', 'should', 'need to', 'needs to', 'have to', 'has to',
  'going to', "i'll", "we'll", "they'll", "let's",
  'action', 'follow up', 'follow-up', 'todo', 'to do', 'must',
];

// Sentences shorter than this are too brief to be meaningful action items.
const MIN_SENTENCE_LENGTH = 8;

function matchesActionKeyword(sentence) {
  const lower = sentence.toLowerCase();
  return ACTION_KEYWORDS.some(kw => {
    const escaped = kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    // Use negative lookbehind/lookahead to avoid partial-word matches.
    return new RegExp('(?<![\\w])' + escaped + '(?![\\w])', 'i').test(lower);
  });
}

function extractActionItems(fullText) {
  // Per spec: always prompt the user to fill in participants since browser
  // cannot detect individual speakers.
  const items = ['Complete the list of participants'];
  const stripped = fullText.replace(/\[\d{2}:\d{2}:\d{2}\]\s*/g, '');
  const sentences = stripped.split(/(?<=[.!?])\s+|\n/).map(s => s.trim()).filter(s => s.length > MIN_SENTENCE_LENGTH);
  sentences.forEach(sentence => {
    if (matchesActionKeyword(sentence)) {
      const cleaned = sentence.charAt(0).toUpperCase() + sentence.slice(1);
      if (!items.includes(cleaned)) items.push(cleaned);
    }
  });
  return items;
}

function renderActionItems(items) {
  actionList.innerHTML = '';
  if (items.length === 0) {
    const li = document.createElement('li');
    li.className = 'placeholder';
    li.innerHTML = '<input type="checkbox" class="action-checkbox" disabled /> No action items detected.';
    actionList.appendChild(li);
    return;
  }
  items.forEach(text => {
    const li = document.createElement('li');
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.className = 'action-checkbox';
    li.appendChild(cb);
    li.appendChild(document.createTextNode('\u00a0' + text));
    actionList.appendChild(li);
  });
}

// ===== Participants =====
function renderParticipants(names) {
  participantsGrid.innerHTML = '';
  if (names.length === 0) {
    const p = document.createElement('p');
    p.className = 'no-participants';
    p.textContent = 'No participants detected — fill in names manually.';
    participantsGrid.appendChild(p);
    return;
  }
  names.forEach(name => {
    const chip = document.createElement('div');
    chip.className = 'participant-chip';
    const avatar = document.createElement('span');
    avatar.className = 'avatar';
    avatar.textContent = name.charAt(0).toUpperCase();
    chip.appendChild(avatar);
    chip.appendChild(document.createTextNode('\u00a0' + name));
    participantsGrid.appendChild(chip);
  });
}

// ===== Recording =====
function startRecording() {
  if (!SpeechRecognitionAPI) return;

  state.recording = true;
  state.transcriptLines = [];
  state.recordingStart = Date.now();
  transcriptEl.value = '';

  btnStart.disabled = true;
  btnStop.disabled  = false;
  statusDot.classList.add('recording');
  statusText.textContent = 'Recording…';
  statusText.classList.remove('status-error');

  renderActionItems([]);
  renderParticipants([]);

  const recognition = new SpeechRecognitionAPI();
  recognition.continuous      = true;
  recognition.interimResults  = true;
  recognition.lang            = 'en-US';

  recognition.onresult = event => {
    let interim = '';
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i];
      if (result.isFinal) {
        appendTranscriptLine(result[0].transcript.trim());
      } else {
        interim += result[0].transcript;
      }
    }
    updateInterim(interim);
  };

  recognition.onerror = event => {
    if (event.error === 'not-allowed') {
      showToast('❌ Microphone permission denied');
      stopRecording();
    } else if (event.error === 'no-speech') {
      // 'no-speech' fires when the API times out waiting for input;
      // it is non-fatal and the onend handler will restart recognition.
    } else {
      showToast(`❌ Speech error: ${event.error}`);
    }
  };

  recognition.onend = () => {
    if (state.recording) recognition.start();
  };

  state.recognition = recognition;
  recognition.start();
  showToast('🎙️ Recording started');
}

function stopRecording() {
  if (!state.recording) return;
  state.recording = false;

  btnStart.disabled = false;
  btnStop.disabled  = true;
  statusDot.classList.remove('recording');
  statusText.textContent = 'Not recording';

  if (state.recognition) {
    state.recognition.onend = null;
    state.recognition.stop();
    state.recognition = null;
  }

  transcriptEl.value = state.transcriptLines.join('\n');

  const items = extractActionItems(transcriptEl.value);
  renderActionItems(items);

  showToast('⏹️ Recording stopped');
}

btnStart.addEventListener('click', startRecording);
btnStop.addEventListener('click', stopRecording);

// ===== Send Summary =====
document.getElementById('btn-send').addEventListener('click', () => {
  showToast('📧 Summary email sent (placeholder)');
});

// ===== Toast Helper =====
let toastTimer = null;
function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 3000);
}

// ===== Initial render =====
renderParticipants([]);
renderActionItems([]);
