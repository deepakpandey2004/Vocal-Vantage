/* Vocal Vantage — shared client helpers */
const VV = (() => {
  const TOKEN_KEY = 'vv_token';
  const GUEST_KEY = 'vv_is_guest';

  function saveToken(token, isGuest) {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(GUEST_KEY, isGuest ? '1' : '0');
  }
  function getToken() { return localStorage.getItem(TOKEN_KEY); }
  function isGuest() { return localStorage.getItem(GUEST_KEY) === '1'; }
  function clearAuth() { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(GUEST_KEY); }

  // Auth header is optional because the server also reads the httpOnly cookie.
  function authHeaders(extra = {}) {
    const h = { ...extra };
    const t = getToken();
    if (t) h['Authorization'] = `Bearer ${t}`;
    return h;
  }

  async function api(path, options = {}) {
    const opts = {
      ...options,
      credentials: 'same-origin',
      headers: authHeaders(options.headers || {}),
    };
    const res = await fetch(path, opts);
    if (res.status === 401) {
      clearAuth();
      if (!location.pathname.startsWith('/login')) location.href = '/login';
      throw new Error('Session expired. Please sign in again.');
    }
    return res;
  }

  async function continueAsGuest() {
    try {
      const res = await fetch('/api/auth/guest', { method: 'POST', credentials: 'same-origin' });
      const data = await res.json();
      saveToken(data.access_token, true);
      location.href = '/dashboard';
    } catch (e) {
      toast('Could not start guest session', 'error');
    }
  }

  async function logout() {
    try { await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' }); } catch {}
    clearAuth();
    location.href = '/';
  }

  let toastTimer;
  function toast(msg, type = '') {
    const el = document.getElementById('toast');
    if (!el) return;
    el.textContent = msg;
    el.className = `toast show ${type}`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.className = 'toast'; }, 3500);
  }

  function escapeHtml(str) {
    return String(str ?? '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  return { saveToken, getToken, isGuest, clearAuth, api, continueAsGuest, logout, toast, escapeHtml };
})();

// Header scroll shadow + mobile nav
document.addEventListener('DOMContentLoaded', () => {
  const header = document.getElementById('siteHeader');
  if (header) {
    const onScroll = () => header.classList.toggle('scrolled', window.scrollY > 8);
    window.addEventListener('scroll', onScroll); onScroll();
  }
  const toggle = document.getElementById('navToggle');
  if (toggle) {
    toggle.addEventListener('click', () => {
      document.getElementById('mainNav')?.classList.toggle('open');
      document.getElementById('headerAuth')?.classList.toggle('open');
    });
  }
});
