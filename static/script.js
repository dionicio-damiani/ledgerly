/* ═══════════════════════════════════════════════
   Smart Invoice Generator — script.js
═══════════════════════════════════════════════ */

// ── State ────────────────────────────────────
let docType = 'Invoice';
let items = [{ description: '', quantity: 1, unit_price: 0 }];
let pdfBlobUrl = null;
let pdfFilename = '';
let senderLogoDataUrl = null;
let signatureImageDataUrl = null;

const MAX_IMAGE_BYTES = 1024 * 1024; // 1MB

// Fallback symbols used until /api/meta resolves (or if it's unreachable).
let CURRENCY_SYMBOLS = { USD: '$', EUR: '€', MXN: '$', GBP: '£', ARS: '$', COP: '$' };

// ── Helpers ──────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function val(id) {
  const el = document.getElementById(id);
  return el ? el.value.trim() : '';
}

function numVal(id, fallback = 0) {
  const v = parseFloat(val(id));
  return isNaN(v) ? fallback : v;
}

function fmt(n, symbol) {
  return `${symbol}${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function getCurrencySymbol() {
  return CURRENCY_SYMBOLS[val('currency')] || '$';
}

function today() {
  return new Date().toISOString().slice(0, 10);
}

function addDays(dateStr, days) {
  const d = new Date(dateStr);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

// ── Toast ─────────────────────────────────────
function showToast(msg, type = 'success', duration = 3500) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast ${type}`;
  requestAnimationFrame(() => t.classList.add('show'));
  setTimeout(() => t.classList.remove('show'), duration);
}

// ── Status badge ───────────────────────────────
function setStatus(state) {
  const label = document.getElementById('doc-status-label');
  const dot = document.querySelector('.status-dot');
  if (!label || !dot) return;

  if (state === 'generated') {
    label.textContent = 'Generated';
    dot.classList.add('is-generated');
  } else {
    label.textContent = 'Draft';
    dot.classList.remove('is-generated');
  }
}

// ── Doc type toggle ───────────────────────────
function setDocType(type) {
  docType = type;
  $$('.toggle-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.type === type);
  });
  document.getElementById('doc-type-label').textContent =
    type === 'Invoice' ? 'Invoice #' : 'Quote #';
  document.getElementById('due-date-row').style.display =
    type === 'Invoice' ? '' : 'none';
  document.getElementById('btn-generate').querySelector('.btn-label').textContent =
    `Download ${type} PDF`;

  const summaryDocType = document.getElementById('summary-doctype');
  if (summaryDocType) summaryDocType.textContent = type;
}

// ── Items ─────────────────────────────────────
function renderItems() {
  const container = document.getElementById('items-container');
  container.innerHTML = '';

  items.forEach((item, idx) => {
    const row = document.createElement('div');
    row.className = 'item-row';

    const total = (item.quantity || 0) * (item.unit_price || 0);
    const symbol = getCurrencySymbol();

    row.innerHTML = `
      <input
        type="text"
        placeholder="e.g. Web design (3 pages)"
        value="${escHtml(item.description)}"
        onchange="updateItem(${idx}, 'description', this.value)"
        oninput="updateItem(${idx}, 'description', this.value)"
      />
      <input
        type="number"
        min="0.01"
        step="0.01"
        value="${item.quantity}"
        onchange="updateItem(${idx}, 'quantity', Math.max(0.01, parseFloat(this.value) || 0.01))"
        oninput="updateItem(${idx}, 'quantity', Math.max(0.01, parseFloat(this.value) || 0.01))"
      />
      <input
        type="number"
        min="0"
        step="0.01"
        placeholder="0.00"
        value="${item.unit_price || ''}"
        onchange="updateItem(${idx}, 'unit_price', parseFloat(this.value) || 0)"
        oninput="updateItem(${idx}, 'unit_price', parseFloat(this.value) || 0)"
      />
      <div class="item-total">${fmt(total, symbol)}</div>
      <button class="btn-remove" onclick="removeItem(${idx})" title="Remove item">×</button>
    `;
    container.appendChild(row);
  });

  updateTotals();
}

function updateItem(idx, field, value) {
  items[idx][field] = value;
  updateTotals();
  // Update only the total cell of this row (avoid full re-render for smooth UX)
  const rows = document.querySelectorAll('.item-row');
  if (rows[idx]) {
    const totalEl = rows[idx].querySelector('.item-total');
    if (totalEl) {
      const t = (items[idx].quantity || 0) * (items[idx].unit_price || 0);
      totalEl.textContent = fmt(t, getCurrencySymbol());
    }
  }
}

function addItem() {
  items.push({ description: '', quantity: 1, unit_price: 0 });
  renderItems();
  // Focus the last description input
  requestAnimationFrame(() => {
    const inputs = document.querySelectorAll('.item-row input[type="text"]');
    if (inputs.length) inputs[inputs.length - 1].focus();
  });
}

function removeItem(idx) {
  if (items.length === 1) {
    showToast('At least one line item is required.', 'error');
    return;
  }
  items.splice(idx, 1);
  renderItems();
}

function updateTotals() {
  const symbol = getCurrencySymbol();
  const taxRate = numVal('tax_rate');
  const discountPct = numVal('discount_percent');

  const subtotal = Math.round(items.reduce((sum, i) => sum + (i.quantity || 0) * (i.unit_price || 0), 0) * 100) / 100;
  const discountAmount = Math.round(subtotal * discountPct / 100 * 100) / 100;
  const taxable = Math.round((subtotal - discountAmount) * 100) / 100;
  const taxAmount = Math.round(taxable * taxRate / 100 * 100) / 100;
  const grand = Math.round((taxable + taxAmount) * 100) / 100;

  document.getElementById('t-subtotal').textContent = fmt(subtotal, symbol);

  const discRow = document.getElementById('discount-row');
  if (discountPct > 0) {
    discRow.style.display = '';
    document.getElementById('t-discount').textContent = `- ${fmt(discountAmount, symbol)}`;
    document.getElementById('t-discount-label').textContent = `Discount (${discountPct.toFixed(1)}%)`;
  } else {
    discRow.style.display = 'none';
  }

  const taxRow = document.getElementById('tax-row');
  if (taxRate > 0) {
    taxRow.style.display = '';
    document.getElementById('t-tax').textContent = fmt(taxAmount, symbol);
    document.getElementById('t-tax-label').textContent = `Tax (${taxRate.toFixed(1)}%)`;
  } else {
    taxRow.style.display = 'none';
  }

  document.getElementById('t-grand').textContent = fmt(grand, symbol);
  document.getElementById('t-currency').textContent = val('currency') || 'USD';

  const currencyBadge = document.getElementById('items-currency-badge');
  if (currencyBadge) currencyBadge.textContent = val('currency') || 'USD';
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Image uploads (logo / signature) ──────────
function handleImageUpload(input, previewEl, onLoaded) {
  const file = input.files && input.files[0];

  if (!file) {
    if (previewEl) previewEl.style.display = 'none';
    onLoaded(null);
    return;
  }

  if (file.size > MAX_IMAGE_BYTES) {
    showToast('Image too large. Max 1MB.', 'error');
    input.value = '';
    if (previewEl) previewEl.style.display = 'none';
    onLoaded(null);
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    const dataUrl = reader.result;
    if (previewEl) {
      previewEl.src = dataUrl;
      previewEl.style.display = '';
    }
    onLoaded(dataUrl);
  };
  reader.readAsDataURL(file);
}

// ── Generate PDF ──────────────────────────────
async function generatePDF() {
  // Validate required fields
  const required = [
    ['doc_number', 'Document number'],
    ['sender_name', 'Your name / company'],
    ['client_name', 'Client name'],
  ];

  for (const [id, label] of required) {
    if (!val(id)) {
      showToast(`${label} is required.`, 'error');
      document.getElementById(id).focus();
      return;
    }
  }

  // Validate items
  const hasEmpty = items.some(i => !i.description.trim());
  if (hasEmpty) {
    showToast('All line items must have a description.', 'error');
    return;
  }

  const payload = {
    doc_type: docType,
    doc_number: val('doc_number'),
    issue_date: val('issue_date') || today(),
    due_date: docType === 'Invoice' ? (val('due_date') || null) : null,
    currency: val('currency') || 'USD',

    sender_name: val('sender_name'),
    sender_email: val('sender_email') || null,
    sender_phone: val('sender_phone') || null,
    sender_address: val('sender_address') || null,
    sender_logo: senderLogoDataUrl,

    client_name: val('client_name'),
    client_email: val('client_email') || null,
    client_address: val('client_address') || null,
    client_company: val('client_company') || null,

    items: items.map(i => ({
      description: i.description,
      quantity: Math.max(0.01, i.quantity || 0.01),
      unit_price: i.unit_price || 0,
    })),

    tax_rate: numVal('tax_rate'),
    discount_percent: numVal('discount_percent'),
    notes: val('notes') || null,

    signature_image: signatureImageDataUrl,
    signature_text: signatureImageDataUrl ? null : (val('signature_text') || null),
  };

  const btn = document.getElementById('btn-generate');
  btn.disabled = true;
  btn.classList.add('loading');

  try {
    const res = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = err?.detail;
      let msg;
      if (Array.isArray(detail)) {
        msg = detail.map(e => e?.msg || JSON.stringify(e)).join('; ');
      } else {
        msg = detail || `Server error ${res.status}`;
      }
      throw new Error(msg);
    }

    // Build the blob URL and show it in the preview modal
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const filename = `${docType.toLowerCase()}-${payload.doc_number.replace(/[^\w-]/g, '-')}.pdf`;

    openPdfModal(url, filename, docType);

    showToast(`✓ ${docType} generated successfully!`, 'success');
    setStatus('generated');
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error', 5000);
  } finally {
    btn.disabled = false;
    btn.classList.remove('loading');
  }
}

// ── PDF preview modal ─────────────────────────
function openPdfModal(url, filename, docTypeLabel) {
  pdfBlobUrl = url;
  pdfFilename = filename;

  const iframe = document.getElementById('pdf-preview-iframe');
  iframe.src = url;

  const title = document.getElementById('pdf-modal-title');
  if (title) title.textContent = `${docTypeLabel} Preview`;

  document.getElementById('pdf-modal-overlay').style.display = 'flex';
}

function closePdfModal() {
  document.getElementById('pdf-modal-overlay').style.display = 'none';

  const iframe = document.getElementById('pdf-preview-iframe');
  iframe.src = '';

  if (pdfBlobUrl) {
    URL.revokeObjectURL(pdfBlobUrl);
    pdfBlobUrl = null;
  }
}

function downloadPdfFromModal() {
  if (!pdfBlobUrl) return;
  const a = document.createElement('a');
  a.href = pdfBlobUrl;
  a.download = pdfFilename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  showToast(`✓ ${docType} downloaded successfully!`, 'success');
}

// ── Init ──────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  // Load supported currencies from the API (falls back to the defaults above).
  try {
    const meta = await fetch('/api/meta').then(res => res.json());
    if (meta?.currencies) CURRENCY_SYMBOLS = meta.currencies;
  } catch {
    // /api/meta unreachable — keep default CURRENCY_SYMBOLS.
  }

  // Set default dates
  const todayStr = today();
  const issueDateEl = document.getElementById('issue_date');
  const dueDateEl = document.getElementById('due_date');
  if (issueDateEl) issueDateEl.value = todayStr;
  if (dueDateEl) dueDateEl.value = addDays(todayStr, 30);

  // Generate default doc number
  const docNumEl = document.getElementById('doc_number');
  if (docNumEl && !docNumEl.value) {
    const ts = new Date();
    const y = ts.getFullYear();
    const m = String(ts.getMonth() + 1).padStart(2, '0');
    docNumEl.value = `${y}${m}-001`;
  }

  // Hook currency change to re-render
  const currencyEl = document.getElementById('currency');
  if (currencyEl) currencyEl.addEventListener('change', () => renderItems());

  // Hook tax/discount to update totals
  ['tax_rate', 'discount_percent'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', updateTotals);
      el.addEventListener('change', updateTotals);
    }
  });

  // Any edit after a successful generation reverts the status badge to "Draft"
  document.addEventListener('input', () => setStatus('draft'));
  document.addEventListener('change', () => setStatus('draft'));

  // Logo / signature uploads
  const logoInput = document.getElementById('sender_logo');
  const logoPreview = document.getElementById('sender-logo-preview');
  if (logoInput) {
    logoInput.addEventListener('change', () => {
      handleImageUpload(logoInput, logoPreview, (dataUrl) => { senderLogoDataUrl = dataUrl; });
    });
  }

  const signatureInput = document.getElementById('signature_image');
  const signaturePreview = document.getElementById('signature-image-preview');
  if (signatureInput) {
    signatureInput.addEventListener('change', () => {
      handleImageUpload(signatureInput, signaturePreview, (dataUrl) => { signatureImageDataUrl = dataUrl; });
    });
  }

  // PDF preview modal controls
  const overlay = document.getElementById('pdf-modal-overlay');
  document.getElementById('pdf-modal-close').addEventListener('click', closePdfModal);
  document.getElementById('pdf-modal-close-footer').addEventListener('click', closePdfModal);
  document.getElementById('pdf-modal-download').addEventListener('click', downloadPdfFromModal);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closePdfModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && overlay.style.display !== 'none') closePdfModal();
  });

  renderItems();
  setDocType('Invoice');
});
