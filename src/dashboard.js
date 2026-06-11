import './dashboard.css';
import { db } from './firebase';
import { collection, query, where, orderBy, getDocs, limit } from 'firebase/firestore';
import { onAuthChanged, getCurrentUser } from './auth';
import { sanitizeHtml } from './utils/sanitize';
const showdown = require('showdown');
const converter = new showdown.Converter();

document.addEventListener('DOMContentLoaded', () => {
  setupNavigation();
  loadReport();
  setupExport();

  onAuthChanged((user) => {
    if (user) {
      loadHistory(user.uid);
    }
  });
});

let currentActiveSection = 'overview';

function switchSection(targetId) {
  const navItem = document.querySelector(`.sidebar-nav .nav-item[href="#${targetId}"]`);
  const sections = document.querySelectorAll('.dashboard-section');
  const navItems = document.querySelectorAll('.sidebar-nav .nav-item');

  if (!navItem) return;

  navItems.forEach(i => i.classList.remove('active'));
  navItem.classList.add('active');
  
  sections.forEach(s => {
    s.classList.toggle('section-active', s.id === targetId);
  });
  
  currentActiveSection = targetId;
  const scrollContainer = document.querySelector('.scroll-container');
  if (scrollContainer) scrollContainer.scrollTop = 0;
}

function loadReport() {
  chrome.storage.local.get(['lastReport'], (result) => {
    const data = result.lastReport;
    if (!data) return;

    try {
      renderOverview(data);
      renderDetailedAnalysis(data);
      renderFiles(data);
      
      document.getElementById('header-repo-name').textContent = data.meta?.title || 'Analysis Report';
      
      setTimeout(() => {
        if (window.mermaid) {
          window.mermaid.initialize({ startOnLoad: false, theme: 'dark' });
          window.mermaid.run({ nodes: document.querySelectorAll('.mermaid') });
        }
      }, 500);
    } catch (err) {
      console.error('Error loading initial report:', err);
    }
  });
}

function renderOverview(data) {
  const { meta, markdown, riskScore, timestamp } = data;
  
  // Risk Gauge
  const score = parseInt(riskScore);
  const arcEl = document.getElementById('risk-arc');
  const scoreValEl = document.getElementById('risk-score-val');
  const riskLabelEl = document.getElementById('risk-label');
  
  if (scoreValEl) scoreValEl.textContent = score;
  
  if (arcEl) {
    const circumference = 339.29; // 2 * PI * 54
    const filled = (score / 100) * circumference;
    arcEl.style.strokeDasharray = `${filled} ${circumference}`;
    
    let color = '#34d399';
    let label = 'Low Risk';
    if (score >= 70) { color = '#f87171'; label = 'Critical Risk'; }
    else if (score >= 45) { color = '#fb923c'; label = 'High Risk'; }
    else if (score >= 20) { color = '#fbbf24'; label = 'Medium Risk'; }
    
    arcEl.style.stroke = color;
    if (riskLabelEl) {
      riskLabelEl.textContent = label;
      riskLabelEl.style.color = color;
      riskLabelEl.style.borderColor = color + '44';
      riskLabelEl.style.backgroundColor = color + '11';
    }
  }

  // Stats
  document.getElementById('total-additions').textContent = `+${meta.totalAdditions}`;
  document.getElementById('total-deletions').textContent = `-${meta.totalDeletions}`;
  document.getElementById('files-count').textContent = meta.files.length;

  // Meta
  const urlEl = document.getElementById('meta-url');
  urlEl.href = meta.url;
  urlEl.textContent = meta.url;
  document.getElementById('meta-mode').textContent = meta.mode === 'pr' ? 'Pull Request Review' : 'Repository Scan';
  document.getElementById('meta-time').textContent = new Date(timestamp).toLocaleString();

  // Summary (extract from markdown)
  const summaryMatch = markdown.match(/## Summary([\s\S]*?)(?=##|$)/i);
  const summaryMd = summaryMatch ? summaryMatch[1].trim() : "No executive summary found in the report.";
  document.getElementById('summary-content').innerHTML = sanitizeHtml(converter.makeHtml(summaryMd));
}

function renderDetailedAnalysis(data) {
  const contentEl = document.getElementById('report-content');
  let html = converter.makeHtml(data.markdown);
  
  // Inject badges
  html = html
    .replace(/\[COMMIT BLOCKER\]/g, '<span class="badge" style="background:rgba(248,113,113,0.15); color:#f87171; border:1px solid rgba(248,113,113,0.3);">Commit Blocker</span>')
    .replace(/\[BLOCKER\]/g, '<span class="badge" style="background:rgba(248,113,113,0.15); color:#f87171; border:1px solid rgba(248,113,113,0.3);">Blocker</span>')
    .replace(/\[CRITICAL\]/g, '<span class="badge" style="background:rgba(248,113,113,0.15); color:#f87171; border:1px solid rgba(248,113,113,0.3);">Critical</span>')
    .replace(/\[NEEDS MAJOR REVISION\]/g, '<span class="badge" style="background:rgba(251,191,36,0.15); color:#fbbf24; border:1px solid rgba(251,191,36,0.3);">Major Revision</span>')
    .replace(/\[ACCEPTABLE\]/g, '<span class="badge" style="background:rgba(52,211,153,0.15); color:#34d399; border:1px solid rgba(52,211,153,0.3);">Acceptable</span>');

  contentEl.innerHTML = sanitizeHtml(html);

  // Handle mermaid
  contentEl.querySelectorAll('pre code.language-mermaid, pre code.mermaid').forEach(el => {
    const pre = el.parentElement;
    const div = document.createElement('div');
    div.className = 'mermaid';
    div.textContent = el.textContent;
    pre.replaceWith(div);
  });
}

function renderFiles(data) {
  const tbody = document.getElementById('files-table-body');
  if (!tbody) return;
  tbody.innerHTML = '';
  
  data.meta.files.forEach(file => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><span class="file-path">${file.path}</span></td>
      <td>
        <span style="color:var(--green)">+${file.additions}</span> 
        <span style="color:var(--border); margin:0 4px;">/</span> 
        <span style="color:var(--red)">-${file.deletions}</span>
      </td>
      <td><span class="badge" style="background:rgba(255,255,255,0.05); color:var(--text-dim);">Analyzed</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function setupNavigation() {
  const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
  
  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = item.getAttribute('href').substring(1);
      switchSection(targetId);
    });
  });
}

async function loadHistory(uid) {
  const tbody = document.getElementById('history-table-body');
  if (!tbody) return;

  try {
    const q = query(
      collection(db, 'scan_history'),
      where('uid', '==', uid),
      limit(20)
    );

    const querySnapshot = await getDocs(q);
    if (querySnapshot.empty) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:40px; color:var(--text-dim);">No history found. Perform a scan to see records here.</td></tr>';
      return;
    }

    // Sort locally to avoid index requirement
    const docs = [];
    querySnapshot.forEach(doc => docs.push({ id: doc.id, ...doc.data() }));
    docs.sort((a, b) => {
      const dateA = a.createdAt?.toDate ? a.createdAt.toDate() : new Date(a.timestamp || 0);
      const dateB = b.createdAt?.toDate ? b.createdAt.toDate() : new Date(b.timestamp || 0);
      return dateB - dateA;
    });

    tbody.innerHTML = '';
    docs.forEach((data) => {
      const date = data.createdAt?.toDate ? data.createdAt.toDate() : new Date(data.timestamp || Date.now());
      const tr = document.createElement('tr');
      const riskColor = data.riskScore >= 70 ? 'var(--red)' : data.riskScore >= 45 ? 'var(--orange)' : 'var(--green)';
      
      tr.classList.add('history-row');
      tr.innerHTML = `
        <td>
          <div class="repo-cell">
            <span class="repo-name">${data.repoTitle || 'Unnamed Repo'}</span>
            <span class="repo-url">${data.repoUrl || ''}</span>
          </div>
        </td>
        <td><span class="badge">${data.mode === 'repo' ? 'Repository' : 'Pull Request'}</span></td>
        <td><span class="history-risk" style="color:${riskColor}">${data.riskScore}/100</span></td>
        <td><span class="history-date">${date.toLocaleDateString()} ${date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span></td>
      `;

      tr.style.cursor = 'pointer';
      tr.addEventListener('click', (e) => {
        e.preventDefault();
        renderReportFromData(data);
        switchSection('overview');
      });

      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading history:', err);
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:40px; color:var(--red);">Failed to load history: ${err.message}</td></tr>`;
  }
}

function renderReportFromData(data) {
  const reportData = {
    meta: data.meta,
    markdown: data.markdown,
    riskScore: data.riskScore,
    timestamp: data.timestamp || (data.createdAt?.toDate ? data.createdAt.toDate().getTime() : Date.now())
  };

  renderOverview(reportData);
  renderDetailedAnalysis(reportData);
  renderFiles(reportData);
  
  document.getElementById('header-repo-name').textContent = reportData.meta.title || 'Analysis Report';
  
  // Re-run mermaid
  setTimeout(() => {
    if (window.mermaid) {
      window.mermaid.run({ nodes: document.querySelectorAll('.mermaid') });
    }
  }, 300);
}

function setupExport() {
  const exportBtn = document.getElementById('export-html-btn');
  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      window.print();
    });
  }
}
