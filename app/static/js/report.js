/* Report page: fetch one analysis and render the full report card */
(() => {
  const root = document.querySelector('.report');
  const id = root.dataset.analysisId;
  const body = document.getElementById('reportBody');
  let currentReport = null;

  if (!VV.getToken()) { location.href = '/login'; return; }

  function ring(score) {
    const r = 65, c = 2 * Math.PI * r;
    const offset = c - (score / 100) * c;
    return `
      <div class="score-ring" style="width:150px;height:150px">
        <svg width="150" height="150">
          <circle cx="75" cy="75" r="${r}" stroke="rgba(255,255,255,.08)" stroke-width="10" fill="none"/>
          <circle cx="75" cy="75" r="${r}" stroke="url(#rg)" stroke-width="10" fill="none"
            stroke-dasharray="${c}" stroke-dashoffset="${offset}" stroke-linecap="round"/>
          <defs><linearGradient id="rg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#8b5cf6"/><stop offset="1" stop-color="#d946ef"/></linearGradient></defs>
        </svg>
        <div class="ring-val"><b>${score}</b><span>/ 100 fluency</span></div>
      </div>`;
  }

  function list(items, cls, icon) {
    if (!items || !items.length) return '<p style="color:var(--muted)">—</p>';
    return `<ul class="insight-list ${cls}">${items.map(t =>
      `<li><span class="ic">${icon}</span><span>${VV.escapeHtml(t)}</span></li>`).join('')}</ul>`;
  }

  function highlightFillers(transcript, breakdown) {
    let html = VV.escapeHtml(transcript || '');
    (breakdown || []).forEach(b => {
      const re = new RegExp(`\\b(${b.word.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})\\b`, 'gi');
      html = html.replace(re, '<mark>$1</mark>');
    });
    return html;
  }

  function render(a) {
    const rep = a.report || {};
    const metrics = rep.metrics || {};
    const insights = rep.ai_insights || {};
    const breakdown = rep.filler_breakdown || [];
    const score = a.fluency_score ?? rep?.scores?.fluency_score ?? 0;
    const maxFiller = Math.max(1, ...breakdown.map(b => b.count));
    currentReport = rep;

    document.getElementById('reportTitle').textContent = a.filename;
    const conf = (insights.confidence_estimate || 'medium').toLowerCase();
    document.getElementById('reportMeta').innerHTML =
      `${new Date(a.created_at).toLocaleString()} · ${(metrics.duration_seconds || 0).toFixed(0)}s ` +
      `· <span class="pill ${conf}">${conf} confidence</span>` +
      `${insights.generated_by ? ` · insights by ${VV.escapeHtml(insights.generated_by)}` : ''}`;

    const check = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>';
    const arrow = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 19V5M5 12l7-7 7 7"/></svg>';
    const bulb = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z"/></svg>';

    body.innerHTML = `
      <div class="report-grid">
        <div style="display:grid;gap:24px">
          <div class="card big-score">
            <h3>Fluency score</h3>
            ${ring(score)}
            <p style="color:var(--muted);font-size:.9rem;margin-top:8px">${VV.escapeHtml(insights.summary || '')}</p>
          </div>
          <div class="card">
            <h3>Linguistic metrics</h3>
            <div class="metric-rows">
              <div class="mr"><span class="label">Words per minute</span><span class="val">${metrics.words_per_minute ?? '—'}</span></div>
              <div class="mr"><span class="label">Total words</span><span class="val">${metrics.word_count ?? '—'}</span></div>
              <div class="mr"><span class="label">Filler words</span><span class="val">${metrics.filler_count ?? 0}</span></div>
              <div class="mr"><span class="label">Filler rate</span><span class="val">${metrics.filler_rate_per_min ?? 0}/min</span></div>
              <div class="mr"><span class="label">Vocabulary diversity</span><span class="val">${metrics.vocabulary_diversity ?? '—'}</span></div>
              <div class="mr"><span class="label">Duration</span><span class="val">${(metrics.duration_seconds || 0).toFixed(1)}s</span></div>
            </div>
          </div>
        </div>

        <div style="display:grid;gap:24px">
          <div class="card">
            <h3>Filler word breakdown</h3>
            ${breakdown.length ? `<div class="filler-bars">${breakdown.map(b => `
              <div class="filler-bar">
                <div class="fb-top"><span>"${VV.escapeHtml(b.word)}"</span><span>${b.count}×</span></div>
                <div class="track"><div class="fill" style="width:${(b.count / maxFiller) * 100}%"></div></div>
              </div>`).join('')}</div>` : '<p style="color:var(--green)">No filler words detected — excellent!</p>'}
          </div>

          <div class="card">
            <h3>AI coaching insights</h3>
            <h4 style="color:var(--green);font-size:.9rem;margin:4px 0 10px">Strengths</h4>
            ${list(insights.strengths, 'strengths', check)}
            <h4 style="color:var(--amber);font-size:.9rem;margin:18px 0 10px">Areas to improve</h4>
            ${list(insights.improvements, 'improve', arrow)}
            <h4 style="color:var(--accent);font-size:.9rem;margin:18px 0 10px">Actionable tips</h4>
            ${list(insights.actionable_tips, 'tips', bulb)}
          </div>

          <div class="card">
            <h3>Transcript <span style="font-weight:400;color:var(--muted);font-size:.82rem">(fillers highlighted)</span></h3>
            <div class="transcript-box">${highlightFillers(rep.transcript || a.transcript, breakdown)}</div>
          </div>
        </div>
      </div>`;
  }

  async function load() {
    try {
      const res = await VV.api(`/api/analyses/${id}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Not found');
      if (data.status === 'failed') {
        body.innerHTML = `<div class="card"><h3>Analysis failed</h3><p style="color:var(--muted)">${VV.escapeHtml(data.error_message || 'Unknown error')}</p></div>`;
        document.getElementById('reportMeta').textContent = 'Failed';
        return;
      }
      render(data);
    } catch (err) {
      body.innerHTML = `<div class="card"><h3>Could not load report</h3><p style="color:var(--muted)">${VV.escapeHtml(err.message)}</p></div>`;
    }
  }

  document.getElementById('downloadJson').addEventListener('click', () => {
    if (!currentReport) return;
    const blob = new Blob([JSON.stringify(currentReport, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `vocal-vantage-report-${id}.json`; a.click();
    URL.revokeObjectURL(url);
  });

  load();
})();
