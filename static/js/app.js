/* =======================================================================
   Conditional Transaction Engine — app.js
   Vanilla JS SPA, Fetch API, no external dependencies
   ======================================================================= */

'use strict';

/* -----------------------------------------------------------------------
   Helper Utilities
   ----------------------------------------------------------------------- */

/**
 * Format a numeric value as Indian Rupees.
 * @param {number|string} val
 * @returns {string}
 */
function formatCurrency(val) {
  return '₹' + parseFloat(val).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

/**
 * Format an ISO date string to a human-readable locale string.
 * @param {string} str
 * @returns {string}
 */
function formatDate(str) {
  if (!str) return '—';
  return new Date(str).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
}

/**
 * Returns an HTML status badge for a given status string.
 * @param {string} s
 * @returns {string}
 */
function statusBadge(s) {
  const cls = s ? s.toLowerCase() : 'pending';
  return `<span class="badge badge-${cls}">${s || 'PENDING'}</span>`;
}

/**
 * Renders a full HTML table from headers array and rows (array of arrays).
 * @param {string[]} headers
 * @param {Array[]} rows  — each row is an array of HTML strings
 * @param {string} [emptyMsg]
 * @returns {string}  — HTML string
 */
function renderTable(headers, rows, emptyMsg = 'No records found.') {
  if (!rows || rows.length === 0) {
    return `<p class="table-empty">${emptyMsg}</p>`;
  }
  const ths = headers.map(h => `<th>${h}</th>`).join('');
  const trs = rows.map(row => {
    const tds = row.map(cell => `<td>${cell ?? '—'}</td>`).join('');
    return `<tr>${tds}</tr>`;
  }).join('');
  return `
    <div class="table-wrapper">
      <table>
        <thead><tr>${ths}</tr></thead>
        <tbody>${trs}</tbody>
      </table>
    </div>`;
}

/**
 * Show a red error message inside a container element.
 * @param {string} containerId
 * @param {string} msg
 */
function showError(containerId, msg) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.className = 'form-result result-error';
  el.innerHTML = `⚠ ${msg}`;
}

/**
 * Show a green success message inside a container element.
 * @param {string} containerId
 * @param {string} msg
 */
function showSuccess(containerId, msg) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.className = 'form-result result-success';
  el.innerHTML = `✓ ${msg}`;
}

/**
 * Clear the contents of a container element.
 * @param {string} containerId
 */
function clearResult(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.className = 'form-result';
  el.innerHTML = '';
}

/** Render a simple loading spinner inside an element. */
function showLoading(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `<div class="loading-state"><span class="spinner"></span> Loading…</div>`;
}

/* -----------------------------------------------------------------------
   API Helper
   ----------------------------------------------------------------------- */

/**
 * Fetch wrapper for JSON REST calls.
 * @param {string} path   — e.g. '/api/accounts'
 * @param {object} options — fetch options (method, body, etc.)
 * @returns {Promise<any>}
 */
async function api(path, options = {}) {
  const defaults = {
    headers: { 'Content-Type': 'application/json' }
  };
  const res = await fetch(path, { ...defaults, ...options });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || data.message || 'Request failed');
  return data;
}

/* -----------------------------------------------------------------------
   SPA Navigation
   ----------------------------------------------------------------------- */

document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', e => {
    e.preventDefault();
    const page = item.dataset.page;
    if (page) navigateTo(page);
  });
});

/**
 * Switch the visible page and load its data.
 * @param {string} page — matches data-page and id="page-{page}"
 */
function navigateTo(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const pageEl = document.getElementById('page-' + page);
  const navEl  = document.querySelector(`[data-page="${page}"]`);

  if (pageEl) pageEl.classList.add('active');
  if (navEl)  navEl.classList.add('active');

  if (page === 'dashboard') loadDashboard();
  if (page === 'accounts')  loadAccounts();
  if (page === 'contracts') loadContracts();
  if (page === 'transfer')  loadTransferPage();
  if (page === 'history')   loadHistory();
}

/* -----------------------------------------------------------------------
   Dashboard
   ----------------------------------------------------------------------- */

async function loadDashboard() {
  showLoading('stats-grid');
  showLoading('account-balances');
  showLoading('recent-transactions');

  try {
    // Fetch dashboard summary
    const dash = await api('/api/dashboard');

    // --- Stat Cards ---
    const stats = [
      {
        label: 'Total Accounts',
        value: dash.total_accounts ?? 0,
        cls: 'stat-blue',
        sub: 'Registered accounts'
      },
      {
        label: 'Successful Txns',
        value: dash.successful_transactions ?? 0,
        cls: 'stat-green',
        sub: 'Completed successfully'
      },
      {
        label: 'Rejected Txns',
        value: dash.rejected_transactions ?? 0,
        cls: 'stat-red',
        sub: 'Condition not met'
      },
      {
        label: 'Total Volume',
        value: formatCurrency(dash.total_volume ?? 0),
        cls: 'stat-amber',
        sub: 'Across all transactions'
      }
    ];

    document.getElementById('stats-grid').innerHTML = stats.map(s => `
      <div class="stat-card ${s.cls}">
        <div class="stat-label">${s.label}</div>
        <div class="stat-value">${s.value}</div>
        <div class="stat-sub">${s.sub}</div>
      </div>`).join('');

    // --- Account Balance Cards ---
    const accounts = dash.accounts || [];
    if (accounts.length === 0) {
      document.getElementById('account-balances').innerHTML =
        '<p class="text-muted" style="padding:0.5rem 0">No accounts yet. Create one in the Accounts tab.</p>';
    } else {
      document.getElementById('account-balances').innerHTML =
        accounts.map(a => `
          <div class="balance-card">
            <div class="balance-name">${escHtml(a.account_name)}</div>
            <div class="balance-amount">${formatCurrency(a.balance)}</div>
            <div class="balance-id">ID #${a.account_id}</div>
          </div>`).join('');
    }

    // --- Recent Transactions ---
    const txns = await api('/api/transactions?limit=10');
    const txList = Array.isArray(txns) ? txns : (txns.transactions || []);
    const rows = txList.map(t => [
      `<span class="font-mono">#${t.transaction_id}</span>`,
      escHtml(t.sender_name || t.sender_id),
      escHtml(t.receiver_name || t.receiver_id),
      escHtml(t.contract_name || t.contract_id),
      `<span class="amount-cell">${formatCurrency(t.amount)}</span>`,
      statusBadge(t.status),
      formatDate(t.created_at)
    ]);
    document.getElementById('recent-transactions').innerHTML =
      renderTable(
        ['Txn #', 'Sender', 'Receiver', 'Contract', 'Amount', 'Status', 'Time'],
        rows,
        'No recent transactions.'
      );

  } catch (err) {
    document.getElementById('stats-grid').innerHTML =
      `<p class="form-result result-error" style="grid-column:1/-1">Failed to load dashboard: ${escHtml(err.message)}</p>`;
  }
}

/* -----------------------------------------------------------------------
   Accounts
   ----------------------------------------------------------------------- */

async function loadAccounts() {
  clearResult('account-form-result');
  showLoading('accounts-table');
  try {
    const data = await api('/api/accounts');
    const accounts = Array.isArray(data) ? data : (data.accounts || []);
    const rows = accounts.map(a => [
      `<span class="font-mono">#${a.account_id}</span>`,
      `<strong>${escHtml(a.account_name)}</strong>`,
      `<span class="amount-cell">${formatCurrency(a.balance)}</span>`,
      formatDate(a.created_at)
    ]);
    document.getElementById('accounts-table').innerHTML =
      renderTable(['ID', 'Name', 'Balance', 'Created At'], rows, 'No accounts found.');
  } catch (err) {
    showError('accounts-table', 'Failed to load accounts: ' + err.message);
  }
}

// Create account form handler
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('create-account-form');
  if (form) {
    form.addEventListener('submit', async e => {
      e.preventDefault();
      clearResult('account-form-result');
      const name    = document.getElementById('new-account-name').value.trim();
      const balance = parseFloat(document.getElementById('new-account-balance').value) || 0;

      if (!name) { showError('account-form-result', 'Account name is required.'); return; }

      try {
        const res = await api('/api/accounts', {
          method: 'POST',
          body: JSON.stringify({ account_name: name, initial_balance: balance })
        });
        showSuccess('account-form-result', `Account "${name}" created with balance ${formatCurrency(res.balance ?? balance)} (ID #${res.account_id ?? res.id}).`);
        form.reset();
        loadAccounts();
        loadAccountsDropdowns();
      } catch (err) {
        showError('account-form-result', err.message);
      }
    });
  }
});

/* -----------------------------------------------------------------------
   Contracts
   ----------------------------------------------------------------------- */

async function loadContracts() {
  clearResult('contract-form-result');
  showLoading('contracts-table');
  try {
    const data = await api('/api/contracts');
    const contracts = Array.isArray(data) ? data : (data.contracts || []);

    const rows = contracts.map(c => {
      const isActive = c.is_active === true || c.is_active === 1;
      const badgeCls = isActive ? 'badge-active' : 'badge-inactive';
      const badgeTxt = isActive ? 'Active' : 'Inactive';
      const btnCls   = isActive ? 'btn-danger btn-sm' : 'btn-success btn-sm';
      const btnTxt   = isActive ? 'Deactivate' : 'Activate';
      return [
        `<span class="font-mono">#${c.contract_id}</span>`,
        `<strong>${escHtml(c.contract_name)}</strong>`,
        escHtml(c.description || '—'),
        formatCurrency(c.min_sender_balance ?? 0),
        formatCurrency(c.max_transfer_amount),
        `<span class="badge ${badgeCls}">${badgeTxt}</span>`,
        `<div class="action-btn-group">
           <button class="btn ${btnCls}" onclick="toggleContract(${c.contract_id}, ${!isActive})">
             ${btnTxt}
           </button>
         </div>`
      ];
    });

    document.getElementById('contracts-table').innerHTML =
      renderTable(
        ['ID', 'Name', 'Description', 'Min Balance', 'Max Amount', 'Status', 'Actions'],
        rows,
        'No contracts found.'
      );
  } catch (err) {
    document.getElementById('contracts-table').innerHTML =
      `<p class="form-result result-error">Failed to load contracts: ${escHtml(err.message)}</p>`;
  }
}

/**
 * Toggle a contract's active status.
 * @param {number} contractId
 * @param {boolean} newStatus
 */
async function toggleContract(contractId, newStatus) {
  try {
    await api(`/api/contracts/${contractId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: newStatus })
    });
    loadContracts();
  } catch (err) {
    alert('Failed to update contract: ' + err.message);
  }
}

// Create contract form handler
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('create-contract-form');
  if (form) {
    form.addEventListener('submit', async e => {
      e.preventDefault();
      clearResult('contract-form-result');

      const name       = document.getElementById('new-contract-name').value.trim();
      const desc       = document.getElementById('new-contract-desc').value.trim();
      const minBalance = parseFloat(document.getElementById('new-contract-min-balance').value) || 0;
      const maxAmount  = parseFloat(document.getElementById('new-contract-max-amount').value);

      if (!name)        { showError('contract-form-result', 'Contract name is required.'); return; }
      if (!maxAmount)   { showError('contract-form-result', 'Max transfer amount is required.'); return; }

      try {
        const res = await api('/api/contracts', {
          method: 'POST',
          body: JSON.stringify({
            contract_name: name,
            description: desc,
            min_sender_balance: minBalance,
            max_transfer_amount: maxAmount
          })
        });
        showSuccess('contract-form-result', `Contract "${name}" created (ID #${res.contract_id ?? res.id}).`);
        form.reset();
        loadContracts();
      } catch (err) {
        showError('contract-form-result', err.message);
      }
    });
  }
});

/* -----------------------------------------------------------------------
   Transfer Page
   ----------------------------------------------------------------------- */

/** Track whether dropdowns have been registered to avoid double-binding. */
let _transferFormBound = false;

async function loadTransferPage() {
  // Populate account dropdowns
  try {
    const data = await api('/api/accounts');
    const accounts = Array.isArray(data) ? data : (data.accounts || []);

    const makeOption = a =>
      `<option value="${a.account_id}">${escHtml(a.account_name)} — ${formatCurrency(a.balance)}</option>`;
    const opts = accounts.map(makeOption).join('');

    document.getElementById('transfer-sender').innerHTML   = opts;
    document.getElementById('transfer-receiver').innerHTML = opts;
  } catch (err) {
    console.error('Failed to load accounts for transfer:', err);
  }

  // Populate active contracts dropdown
  try {
    const data = await api('/api/contracts');
    const contracts = Array.isArray(data) ? data : (data.contracts || []);
    const active = contracts.filter(c => c.is_active === true || c.is_active === 1);

    document.getElementById('transfer-contract').innerHTML = active.length
      ? active.map(c =>
          `<option value="${c.contract_id}">${escHtml(c.contract_name)} (max ${formatCurrency(c.max_transfer_amount)})</option>`
        ).join('')
      : '<option value="">— No active contracts —</option>';

    // Contract rules reference table
    const rows = contracts.map(c => {
      const isActive = c.is_active === true || c.is_active === 1;
      return [
        `<span class="font-mono">#${c.contract_id}</span>`,
        escHtml(c.contract_name),
        escHtml(c.description || '—'),
        formatCurrency(c.min_sender_balance ?? 0),
        formatCurrency(c.max_transfer_amount),
        `<span class="badge ${isActive ? 'badge-active' : 'badge-inactive'}">${isActive ? 'Active' : 'Inactive'}</span>`
      ];
    });

    document.getElementById('contract-rules-ref').innerHTML =
      renderTable(
        ['ID', 'Name', 'Description', 'Min Sender Balance', 'Max Transfer', 'Status'],
        rows,
        'No contracts defined.'
      );

  } catch (err) {
    console.error('Failed to load contracts for transfer:', err);
  }

  // Bind form handler once
  if (!_transferFormBound) {
    _transferFormBound = true;
    const form = document.getElementById('transfer-form');
    if (form) {
      form.addEventListener('submit', handleTransfer);
    }
  }

  // Reset result
  const resultEl = document.getElementById('transfer-result');
  if (resultEl) {
    resultEl.className = 'transfer-result hidden';
    resultEl.innerHTML = '';
  }
}

async function handleTransfer(e) {
  e.preventDefault();

  const btn = document.getElementById('transfer-btn');
  const resultEl = document.getElementById('transfer-result');

  const senderId    = parseInt(document.getElementById('transfer-sender').value);
  const receiverId  = parseInt(document.getElementById('transfer-receiver').value);
  const contractId  = parseInt(document.getElementById('transfer-contract').value);
  const amount      = parseFloat(document.getElementById('transfer-amount').value);

  // Basic validation
  if (senderId === receiverId) {
    resultEl.className = 'transfer-result rejected';
    resultEl.innerHTML = `
      <div class="result-title">⛔ Invalid Transfer</div>
      <div class="result-detail">Sender and receiver must be different accounts.</div>`;
    resultEl.classList.remove('hidden');
    return;
  }

  // Disable button while processing
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner spinner-sm"></span> Processing…';
  resultEl.className = 'transfer-result hidden';
  resultEl.innerHTML = '';

  try {
    const res = await api('/api/transactions', {
      method: 'POST',
      body: JSON.stringify({
        sender_id:   senderId,
        receiver_id: receiverId,
        contract_id: contractId,
        amount:      amount
      })
    });

    const status   = (res.status || 'PENDING').toUpperCase();
    const message  = res.message || '';
    const txId     = res.transaction_id || res.id || '';

    let icon, cls;
    if (status === 'SUCCESS') {
      icon = '✅'; cls = 'success';
    } else if (status === 'REJECTED') {
      icon = '❌'; cls = 'rejected';
    } else {
      icon = '⏳'; cls = 'pending';
    }

    resultEl.className = `transfer-result ${cls}`;
    resultEl.innerHTML = `
      <div class="result-title">${icon} Transaction ${status}${txId ? ` &nbsp;·&nbsp; <span class="font-mono">#${txId}</span>` : ''}</div>
      <div class="result-detail">${escHtml(message || 'Transaction processed.')}</div>`;
    resultEl.classList.remove('hidden');

    // Silently refresh dashboard data in background on success
    if (status === 'SUCCESS') {
      api('/api/dashboard').catch(() => {});
    }

  } catch (err) {
    resultEl.className = 'transfer-result rejected';
    resultEl.innerHTML = `
      <div class="result-title">⛔ Error</div>
      <div class="result-detail">${escHtml(err.message)}</div>`;
    resultEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Execute Transaction';
  }
}

/* -----------------------------------------------------------------------
   History
   ----------------------------------------------------------------------- */

let _historyAccountsLoaded = false;

async function loadHistory() {
  showLoading('history-table');

  // Populate filter-account dropdown once
  if (!_historyAccountsLoaded) {
    _historyAccountsLoaded = true;
    loadAccountsDropdowns();
  }

  // Build query string from filters
  const statusVal  = document.getElementById('filter-status')?.value  || '';
  const accountVal = document.getElementById('filter-account')?.value || '';

  const params = new URLSearchParams();
  if (statusVal)  params.set('status',     statusVal);
  if (accountVal) params.set('account_id', accountVal);

  const qs = params.toString() ? '?' + params.toString() : '';

  try {
    const data = await api('/api/transactions' + qs);
    const txns = Array.isArray(data) ? data : (data.transactions || []);

    const rows = txns.map(t => [
      `<span class="font-mono">#${t.transaction_id}</span>`,
      escHtml(t.sender_name   || String(t.sender_id)),
      escHtml(t.receiver_name || String(t.receiver_id)),
      escHtml(t.contract_name || String(t.contract_id)),
      `<span class="amount-cell">${formatCurrency(t.amount)}</span>`,
      statusBadge(t.status),
      `<span class="text-muted">${escHtml(t.message || '—')}</span>`,
      formatDate(t.created_at)
    ]);

    document.getElementById('history-table').innerHTML =
      renderTable(
        ['Txn #', 'Sender', 'Receiver', 'Contract', 'Amount', 'Status', 'Message', 'Time'],
        rows,
        'No transactions match the selected filters.'
      );

  } catch (err) {
    document.getElementById('history-table').innerHTML =
      `<p class="form-result result-error">Failed to load history: ${escHtml(err.message)}</p>`;
  }
}

/**
 * Populate the history filter-account dropdown from /api/accounts.
 */
async function loadAccountsDropdowns() {
  try {
    const data = await api('/api/accounts');
    const accounts = Array.isArray(data) ? data : (data.accounts || []);

    const sel = document.getElementById('filter-account');
    if (!sel) return;

    // Keep the "All" option, replace the rest
    sel.innerHTML = '<option value="">All</option>' +
      accounts.map(a =>
        `<option value="${a.account_id}">${escHtml(a.account_name)}</option>`
      ).join('');
  } catch (err) {
    console.warn('Could not preload account list for filter:', err);
  }
}

/* -----------------------------------------------------------------------
   XSS Guard
   ----------------------------------------------------------------------- */

/**
 * Escape HTML special characters to prevent XSS.
 * @param {any} str
 * @returns {string}
 */
function escHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/* -----------------------------------------------------------------------
   Init
   ----------------------------------------------------------------------- */

document.addEventListener('DOMContentLoaded', () => {
  loadDashboard();
  loadAccountsDropdowns(); // pre-load for history filter
});
