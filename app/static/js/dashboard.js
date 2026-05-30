/* Dashboard: upload pipeline + history */
(() => {
  const fileInput = document.getElementById('fileInput');
  const uploadZone = document.getElementById('uploadZone');
  const progressBox = document.getElementById('progressBox');
  const analysisList = document.getElementById('analysisList');

  // Require some session (registered or guest).
  if (!VV.getToken()) { location.href = '/login'; return; }

  if (VV.isGuest()) {
    document.getElementById('guestBadge').style.display = 'inline-block';
    document.getElementById('welcomeLine').textContent =
      'You are in guest mode — analyses are saved to this session only.';
  } else {
    // Try to greet the user by name.
    VV.api('/api/auth/me').then(r => r.ok ? r.json() : null).then(u => {
      if (u) document.getElementById('welcomeLine').textContent =
        `Welcome back, ${u.full_name.split(' ')[0]}! Upload a recording to get started.`;
    }).catch(() => {});
  }

  document.getElementById('logoutBtn').addEventListener('click', () => VV.logout());

  // --- Drag & drop ---
  ['dragenter', 'dragover'].forEach(ev =>
    uploadZone.addEventListener(ev, (e) => { e.preventDefault(); uploadZone.classList.add('drag'); }));
  ['dragleave', 'drop'].forEach(ev =>
    uploadZone.addEventListener(ev, (e) => { e.preventDefault(); uploadZone.classList.remove('drag'); }));
  uploadZone.addEventListener('drop', (e) => {
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleUpload(fileInput.files[0]);
  });

  function setStep(name, state) {
    const el = progressBox.querySelector(`[data-step="${name}"]`);
    if (!el) return;
    el.classList.remove('active', 'done');
    if (state) el.classList.add(state);
    const dot = el.querySelector('.pdot');
    dot.innerHTML = state === 'done' ? '✓' : (state === 'active' ? '<span class="spinner"></span>' : '');
  }

  async function handleUpload(file) {
    if (file.size > 25 * 1024 * 1024) { VV.toast('File exceeds 25 MB limit', 'error'); return; }
    progressBox.classList.add('show');
    ['upload', 'transcribe', 'analyze', 'feedback'].forEach(s => setStep(s, ''));
    setStep('upload', 'active');

    const fd = new FormData();
    fd.append('file', file);

    // Visual staging (real work happens server-side in one request).
    let stageTimers = [
      setTimeout(() => { setStep('upload', 'done'); setStep('transcribe', 'active'); }, 700),
      setTimeout(() => { setStep('transcribe', 'done'); setStep('analyze', 'active'); }, 2200),
      setTimeout(() => { setStep('analyze', 'done'); setStep('feedback', 'active'); }, 3200),
    ];

    try {
      const res = await VV.api('/api/analyses', { method: 'POST', body: fd });
      stageTimers.forEach(clearTimeout);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Analysis failed');
      ['upload', 'transcribe', 'analyze', 'feedback'].forEach(s => setStep(s, 'done'));
      VV.toast('Report ready!', 'success');
      setTimeout(() => { location.href = `/report/${data.id}`; }, 600);
    } catch (err) {
      stageTimers.forEach(clearTimeout);
      progressBox.classList.remove('show');
      VV.toast(err.message, 'error');
    } finally {
      fileInput.value = '';
    }
  }

  // --- History ---
  function scoreColor(score) {
    if (score == null) return 'var(--muted)';
    if (score >= 80) return 'var(--green)';
    if (score >= 60) return 'var(--amber)';
    return 'var(--red)';
  }

  async function loadHistory() {
    try {
      const res = await VV.api('/api/analyses');
      const items = await res.json();
      if (!items.length) {
        analysisList.innerHTML = `<div class="empty-state">No analyses yet. Upload your first recording above to see it here.</div>`;
        return;
      }
      analysisList.innerHTML = items.map(a => {
        const date = new Date(a.created_at).toLocaleString();
        const score = a.fluency_score != null ? a.fluency_score : '—';
        return `
          <a class="analysis-row" href="/report/${a.id}">
            <div class="ar-score" style="color:${scoreColor(a.fluency_score)}">${score}</div>
            <div class="ar-main">
              <h4>${VV.escapeHtml(a.filename)}</h4>
              <p>${a.words_per_minute ? a.words_per_minute + ' WPM · ' : ''}${date} · ${a.status}</p>
            </div>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
          </a>`;
      }).join('');
    } catch (err) {
      analysisList.innerHTML = `<div class="empty-state">Could not load history.</div>`;
    }
  }

  loadHistory();
})();
