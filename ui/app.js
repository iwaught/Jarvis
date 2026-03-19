// ===== State =====
const state = {
  recording: false,
};

// ===== DOM refs =====
const btnStart   = document.getElementById('btn-start');
const btnStop    = document.getElementById('btn-stop');
const statusDot  = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const transcript = document.getElementById('transcript');
const toast      = document.getElementById('toast');

// ===== Recording =====
function startRecording() {
  state.recording = true;
  btnStart.disabled = true;
  btnStop.disabled  = false;
  statusDot.classList.add('recording');
  statusText.textContent = 'Recording…';
  transcript.placeholder = 'Transcript will appear here as the meeting progresses…';
  showToast('🎙️ Recording started');
}

function stopRecording() {
  state.recording = false;
  btnStart.disabled = false;
  btnStop.disabled  = true;
  statusDot.classList.remove('recording');
  statusText.textContent = 'Not recording';
  transcript.value = getSampleTranscript();
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

// ===== Sample placeholder content =====
function getSampleTranscript() {
  return `[00:00] Alice: Good morning everyone, let's get started.\n` +
         `[00:05] Bob: Sure. First item — the Q2 roadmap.\n` +
         `[00:42] Alice: We need to finalize priorities by Friday.\n` +
         `[01:10] Unknown: Can someone share the updated spec?\n` +
         `[01:30] Bob: I'll send it right after the call.`;
}
