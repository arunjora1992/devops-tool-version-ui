'use strict';

const API_BASE = '/api';

let allTools = [];
let activeCategory = 'All';
let sortCol = 'name';
let sortDir = 'asc';
let fetchedAt = '';

// ── Bootstrap ─────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  renderSkeletons(10);
  loadVersions(false);
});

// ── Data loading ──────────────────────────────────────────────────────────────

async function loadVersions(force) {
  setRefreshing(true);
  try {
    const url = force ? `${API_BASE}/versions/refresh` : `${API_BASE}/versions`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    allTools = data.tools || [];
    fetchedAt = data.fetched_at || '';
    document.getElementById('last-updated').textContent =
      fetchedAt ? `Last fetched: ${formatDate(fetchedAt)}` : 'Data loaded';
    buildCategoryPills();
    applyFilters();
    renderStats();
  } catch (err) {
    document.getElementById('table-body').innerHTML =
      `<tr><td colspan="7" class="text-center py-10 text-red-400"><i class="fas fa-exclamation-triangle mr-2"></i>Failed to load: ${err.message}</td></tr>`;
  } finally {
    setRefreshing(false);
  }
}

function refreshData() { loadVersions(true); }

// ── Rendering ─────────────────────────────────────────────────────────────────

function applyFilters() {
  const query = document.getElementById('search-input').value.toLowerCase();
  let filtered = allTools;

  if (activeCategory !== 'All') {
    filtered = filtered.filter(t => t.category === activeCategory);
  }
  if (query) {
    filtered = filtered.filter(t =>
      t.name.toLowerCase().includes(query) ||
      t.category.toLowerCase().includes(query) ||
      (t.latest?.version || '').toLowerCase().includes(query)
    );
  }

  filtered = sortTools(filtered);
  renderTable(filtered);
  document.getElementById('footer-count').textContent =
    `Showing ${filtered.length} of ${allTools.length} tools`;
}

function renderTable(tools) {
  const tbody = document.getElementById('table-body');
  if (!tools.length) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center py-10 text-slate-400">No tools match your filter.</td></tr>`;
    return;
  }
  tbody.innerHTML = tools.map(renderRow).join('');
}

function renderRow(t) {
  const latestBadge = t.latest
    ? `<span class="ver-badge ver-latest">${esc(t.latest.version)}</span>`
    : `<span class="ver-badge ver-na">N/A</span>`;

  const prevBadge = t.previous
    ? `<span class="ver-badge ver-prev">${esc(t.previous.version)}</span>`
    : `<span class="ver-badge ver-na">—</span>`;

  const latestDate = t.latest?.date ? `<span class="text-slate-400 text-xs">${t.latest.date}</span>` : '';
  const prevDate   = t.previous?.date ? `<span class="text-slate-400 text-xs">${t.previous.date}</span>` : '';

  const statusDot = t.status === 'error'
    ? `<span class="status-dot status-error"></span>`
    : t.source === 'static'
      ? `<span class="status-dot status-static"></span>`
      : `<span class="status-dot status-ok"></span>`;

  const sourceLink = t.homepage
    ? `<a href="${esc(t.homepage)}" target="_blank" rel="noopener" class="text-blue-400 hover:text-blue-300 text-xs"><i class="fas fa-external-link-alt"></i></a>`
    : '';

  const nameCell = t.homepage
    ? `<a href="${esc(t.homepage)}" target="_blank" rel="noopener" class="tool-link">${esc(t.icon)} ${esc(t.name)}</a>`
    : `<span>${esc(t.icon)} ${esc(t.name)}</span>`;

  const errorNote = t.status === 'error'
    ? `<br/><span class="text-red-400 text-xs">⚠ ${esc(t.error || 'fetch error')}</span>`
    : '';

  return `
    <tr>
      <td class="px-4 py-2.5">${nameCell}${errorNote}</td>
      <td class="px-4 py-2.5 text-slate-300 text-xs">${esc(t.category)}</td>
      <td class="px-4 py-2.5">${latestBadge}</td>
      <td class="px-4 py-2.5">${latestDate}</td>
      <td class="px-4 py-2.5">${prevBadge}</td>
      <td class="px-4 py-2.5">${prevDate}</td>
      <td class="px-4 py-2.5">${statusDot}${sourceLink}</td>
    </tr>`;
}

function renderSkeletons(n) {
  const tbody = document.getElementById('table-body');
  tbody.innerHTML = Array.from({ length: n }, () => `
    <tr>
      ${Array.from({ length: 7 }, () =>
        `<td class="px-4 py-3"><span class="skeleton" style="width:${40 + Math.random() * 40}%"></span></td>`
      ).join('')}
    </tr>`
  ).join('');
}

// ── Category pills ─────────────────────────────────────────────────────────────

function buildCategoryPills() {
  const categories = ['All', ...new Set(allTools.map(t => t.category).sort())];
  const container = document.getElementById('category-pills');
  container.innerHTML = categories.map(cat => `
    <button class="cat-pill ${cat === activeCategory ? 'active' : ''}"
      onclick="selectCategory('${esc(cat)}')">${esc(cat)}</button>
  `).join('');
}

function selectCategory(cat) {
  activeCategory = cat;
  buildCategoryPills();
  applyFilters();
}

// ── Stats ─────────────────────────────────────────────────────────────────────

function renderStats() {
  const total = allTools.length;
  const ok = allTools.filter(t => t.status === 'ok').length;
  const errors = allTools.filter(t => t.status === 'error').length;
  const cats = new Set(allTools.map(t => t.category)).size;

  document.getElementById('stats-row').innerHTML = `
    <span><i class="fas fa-cubes mr-1 text-blue-400"></i>${total} tools</span>
    <span><i class="fas fa-tags mr-1 text-purple-400"></i>${cats} categories</span>
    <span><i class="fas fa-check-circle mr-1 text-green-400"></i>${ok} fetched</span>
    ${errors ? `<span><i class="fas fa-exclamation-circle mr-1 text-red-400"></i>${errors} errors</span>` : ''}
  `;
}

// ── Sorting ───────────────────────────────────────────────────────────────────

document.querySelectorAll('th.sortable').forEach(th => {
  th.addEventListener('click', () => {
    const col = th.dataset.col;
    if (sortCol === col) {
      sortDir = sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      sortCol = col;
      sortDir = 'asc';
    }
    document.querySelectorAll('th.sortable').forEach(h => {
      h.classList.remove('sort-asc', 'sort-desc');
    });
    th.classList.add(sortDir === 'asc' ? 'sort-asc' : 'sort-desc');
    applyFilters();
  });
});

function sortTools(tools) {
  return [...tools].sort((a, b) => {
    let va = '', vb = '';
    if (sortCol === 'name')     { va = a.name; vb = b.name; }
    if (sortCol === 'category') { va = a.category; vb = b.category; }
    const cmp = va.localeCompare(vb);
    return sortDir === 'asc' ? cmp : -cmp;
  });
}

// ── Export ────────────────────────────────────────────────────────────────────

function exportFile(type) {
  window.location.href = `${API_BASE}/export/${type}`;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function setRefreshing(on) {
  const icon = document.getElementById('refresh-icon');
  const btn  = document.getElementById('btn-refresh');
  if (on) {
    icon.classList.add('spin');
    btn.disabled = true;
  } else {
    icon.classList.remove('spin');
    btn.disabled = false;
  }
}

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
  } catch { return iso; }
}

function esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
