/* ================================================
   Ledgerly — invoices.js
   "Mis facturas" page: list, view PDF, delete
================================================ */

// Auth guard: si no hay token, redirigir a /login
if (!window.Auth || !window.Auth.isAuthenticated()) {
  window.location.href = '/login';
  throw new Error('Not authenticated');
}

// Fallback symbols used until /api/meta resolves (or if it's unreachable).
let CURRENCY_SYMBOLS = { USD: '$', EUR: '€', MXN: '$', GBP: '£', ARS: '$', COP: '$' };

function showToast(msg, type = 'success', duration = 3500) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className = `toast ${type}`;
  requestAnimationFrame(() => t.classList.add('show'));
  setTimeout(() => t.classList.remove('show'), duration);
}

function getCurrencySymbol(currency) {
  return CURRENCY_SYMBOLS[currency] || '$';
}

function setState(state) {
  document.getElementById('invoices-loading').style.display = state === 'loading' ? '' : 'none';
  document.getElementById('invoices-error').style.display = state === 'error' ? '' : 'none';
  document.getElementById('invoices-empty').style.display = state === 'empty' ? '' : 'none';
  document.getElementById('invoices-table').style.display = state === 'table' ? '' : 'none';
}

async function downloadInvoicePdf(invoiceId, docNumber) {
  const res = await fetch(`/invoices/${invoiceId}/pdf`, {
    headers: { ...window.Auth.authHeader() },
  });

  if (res.status === 401) {
    window.Auth.logout();
    return;
  }

  if (!res.ok) {
    showToast('No se pudo descargar el PDF.', 'error');
    return;
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);

  const a = document.createElement('a');
  a.href = url;
  a.download = `${docNumber || invoiceId}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();

  URL.revokeObjectURL(url);
}

async function deleteInvoice(invoiceId, docNumber) {
  if (!confirm(`¿Eliminar la factura ${docNumber}? Esta acción no se puede deshacer.`)) {
    return;
  }

  const res = await fetch(`/invoices/${invoiceId}`, {
    method: 'DELETE',
    headers: { ...window.Auth.authHeader() },
  });

  if (res.status === 401) {
    window.Auth.logout();
    return;
  }

  if (!res.ok) {
    showToast('No se pudo eliminar la factura.', 'error');
    return;
  }

  showToast('Factura eliminada.', 'success');
  loadInvoices();
}

function renderInvoices(invoices) {
  if (invoices.length === 0) {
    setState('empty');
    return;
  }

  const tbody = document.getElementById('invoices-tbody');
  tbody.innerHTML = '';

  invoices.forEach((inv) => {
    const tr = document.createElement('tr');

    const symbol = getCurrencySymbol(inv.currency);
    const total = Number(inv.grand_total);
    const date = new Date(inv.created_at).toLocaleDateString();

    tr.innerHTML = `
      <td>${inv.doc_number ?? ''}</td>
      <td>${inv.client_name ?? ''}</td>
      <td>${date}</td>
      <td>${symbol}${total.toFixed(2)}</td>
      <td class="invoices-actions"></td>
    `;

    const actionsCell = tr.querySelector('.invoices-actions');

    const viewBtn = document.createElement('button');
    viewBtn.type = 'button';
    viewBtn.className = 'btn-row-action';
    viewBtn.textContent = 'Ver';
    viewBtn.addEventListener('click', () => downloadInvoicePdf(inv.id, inv.doc_number));

    const editBtn = document.createElement('a');
    editBtn.href = `/app?id=${inv.id}`;
    editBtn.className = 'btn-row-action';
    editBtn.textContent = 'Editar';

    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'btn-row-action btn-row-danger';
    deleteBtn.textContent = 'Eliminar';
    deleteBtn.addEventListener('click', () => deleteInvoice(inv.id, inv.doc_number));

    actionsCell.append(viewBtn, editBtn, deleteBtn);
    tbody.appendChild(tr);
  });

  setState('table');
}

async function loadInvoices() {
  setState('loading');

  let res;
  try {
    res = await fetch('/invoices', { headers: { ...window.Auth.authHeader() } });
  } catch {
    setState('error');
    return;
  }

  if (res.status === 401) {
    window.Auth.logout();
    return;
  }

  if (!res.ok) {
    setState('error');
    return;
  }

  renderInvoices(await res.json());
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('logout-btn')?.addEventListener('click', () => {
    window.Auth.logout();
  });

  document.getElementById('invoices-retry')?.addEventListener('click', loadInvoices);

  // Load currency symbols from /api/meta (public, no auth needed) before rendering totals.
  fetch('/api/meta')
    .then((res) => res.json())
    .then((meta) => {
      if (meta?.currencies) CURRENCY_SYMBOLS = meta.currencies;
    })
    .catch(() => {
      // /api/meta unreachable — keep default CURRENCY_SYMBOLS.
    })
    .finally(loadInvoices);
});
