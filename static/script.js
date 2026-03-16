/* ============================================================
   Hospital AI Assistant — script.js
   Handles: canvas dots, file upload, chat, chart display
   ============================================================ */
let waitingForReply = false;
/* ── Twinkling Dot Canvas ───────────────────────────────── */
(function initCanvas() {
  const canvas = document.getElementById('dotCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  let dots = [];
  const DOT_COUNT = 90;

  function resize() {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  function createDot() {
    return {
      x:       Math.random() * canvas.width,
      y:       Math.random() * canvas.height,
      r:       Math.random() * 1.4 + 0.4,
      alpha:   Math.random(),
      speed:   Math.random() * 0.006 + 0.002,
      phase:   Math.random() * Math.PI * 2,
      drift:   (Math.random() - 0.5) * 0.08,
      driftY:  (Math.random() - 0.5) * 0.04,
    };
  }

  function initDots() {
    dots = Array.from({ length: DOT_COUNT }, createDot);
  }

  function draw(ts) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const t = ts * 0.001;

    dots.forEach(d => {
      d.phase += d.speed;
      d.x += d.drift;
      d.y += d.driftY;

      // Wrap edges
      if (d.x < -4) d.x = canvas.width + 4;
      if (d.x > canvas.width + 4) d.x = -4;
      if (d.y < -4) d.y = canvas.height + 4;
      if (d.y > canvas.height + 4) d.y = -4;

      const alpha = 0.18 + 0.55 * ((Math.sin(d.phase) + 1) / 2);

      ctx.beginPath();
      ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(103, 232, 249, ${alpha})`;
      ctx.fill();
    });

    requestAnimationFrame(draw);
  }

  resize();
  initDots();
  requestAnimationFrame(draw);

  window.addEventListener('resize', () => { resize(); initDots(); });
})();


/* ── State ──────────────────────────────────────────────── */
let datasetUploaded = false;


/* ── Status Pill ────────────────────────────────────────── */
function setStatus(label, state = 'ready') {
  const pill  = document.getElementById('statusPill');
  const span  = pill.querySelector('.status-label');
  span.textContent = label;
  pill.className   = 'status-pill ' + state;
}


/* ── Drag & Drop ────────────────────────────────────────── */
function handleDragOver(e) {
  e.preventDefault();
  document.getElementById('dropZone').classList.add('drag-over');
}

function handleDragLeave(e) {
  document.getElementById('dropZone').classList.remove('drag-over');
}

function handleDrop(e) {
  e.preventDefault();
  document.getElementById('dropZone').classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file && file.name.endsWith('.csv')) {
    uploadFile(file);
  } else {
    showUploadStatus('Please drop a valid .csv file', 'error');
  }
}

function handleFileSelect(e) {
  const file = e.target.files[0];
  if (file) uploadFile(file);
}


/* ── File Upload ────────────────────────────────────────── */
function showUploadStatus(msg, type = '') {
  const el = document.getElementById('uploadStatus');
  el.textContent = msg;
  el.className   = 'upload-status ' + type;
}

async function uploadFile(file) {
  showUploadStatus('Uploading…', 'loading');
  setStatus('Uploading…', 'uploading');

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res  = await fetch('/upload', { method: 'POST', body: formData });
    const data = await res.json();

    if (data.rows && data.columns) {
      datasetUploaded = true;
      showUploadStatus(`✓ ${file.name} uploaded`, 'success');
      setStatus('Dataset loaded', 'ready');
      addMessage(
        'ai',
        `Dataset <strong>${file.name}</strong> loaded successfully!<br>
        Records: <strong>${data.rows}</strong><br>
        Columns: <strong>${data.columns.join(", ")}</strong><br><br>
        You can now ask me to analyze patient vitals or generate bar charts.`
      );
    } else {
      throw new Error(data.error || 'Upload failed');
    }
  } catch (err) {
    showUploadStatus(`✗ ${err.message}`, 'error');
    setStatus('Upload failed', 'error');
    addMessage('ai', `Sorry, there was a problem uploading the file: ${err.message}`);
  }
}


/* ── Chat ───────────────────────────────────────────────── */
function handleEnterKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 140) + 'px';
}

async function sendMessage() {

  if (waitingForReply) return; // prevents multiple messages
  waitingForReply = true;
  const input   = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendBtn');
  const text    = input.value.trim();
  if (!text) {
  waitingForReply = false;
  return;
  }

  // Add user message
  addMessage('user', escapeHtml(text));
  input.value = '';
  input.style.height = 'auto';

  // Disable button + show typing
  sendBtn.disabled = true;
  showTyping(true);
  setStatus('Thinking…', 'uploading');

  try {
    const res  = await fetch('/chat', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ message: text }),
    });

    const data = await res.json();
    showTyping(false);

    if (data.reply !== undefined) {
      addMessage('ai', data.reply);
    } else if (data.plot !== undefined) {
      addMessage('ai', 'Here is the chart based on your dataset:');
      showChart(data.plot);
    } else if (data.error) {
      addMessage('ai', `Error: ${data.error}`);
    } else {
      addMessage('ai', 'I received an unexpected response. Please try again.');
    }

    setStatus('Ready', 'ready');
  } catch (err) {
    showTyping(false);
    addMessage('ai', `Connection error: ${err.message}. Please check your server.`);
    setStatus('Error', 'error');
  } finally {
    sendBtn.disabled = false;
    waitingForReply = false;
    input.focus();
    }
}


/* ── DOM Helpers ────────────────────────────────────────── */
function addMessage(role, html) {
  const container = document.getElementById('chatMessages');

  const wrapper = document.createElement('div');
  wrapper.className = `message message-${role}`;

  if (role === 'ai') {
    wrapper.innerHTML = `
      <div class="message-avatar">
        <svg viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="1.5"/>
          <path d="M12 8v4M12 16h.01" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
      </div>
      <div class="message-bubble">${html}</div>
    `;
  } else {
    wrapper.innerHTML = `<div class="message-bubble">${html}</div>`;
  }

  container.appendChild(wrapper);
  scrollToBottom();
}

function showTyping(visible) {
  const el = document.getElementById('typingIndicator');
  el.style.display = visible ? 'flex' : 'none';
  if (visible) scrollToBottom();
}

function showChart(base64) {
  const card = document.getElementById('chartCard');
  const img  = document.getElementById('chartImage');
  img.src    = `data:image/png;base64,${base64}`;
  card.style.display = 'block';
  card.style.animation = 'fadeSlideUp 0.4s ease both';
  // Smooth scroll into view after brief delay
  setTimeout(() => card.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 100);
}

function scrollToBottom() {
  const container = document.getElementById('chatMessages');
  requestAnimationFrame(() => {
    container.scrollTop = container.scrollHeight;
  });
}

function escapeHtml(str) {
  const map = { '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' };
  return str.replace(/[&<>"']/g, m => map[m]);
}


/* ── Click on drop zone to trigger file picker ──────────── */
document.addEventListener('DOMContentLoaded', () => {
  const dropZone = document.getElementById('dropZone');
  if (dropZone) {
    dropZone.addEventListener('click', () => {
      document.getElementById('fileInput').click();
    });
  }

  // Focus input on load
  const chatInput = document.getElementById('chatInput');
  if (chatInput) chatInput.focus();
});