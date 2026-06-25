// ── MODAL ─────────────────────────────────────────────────────────────────
function toggleModal(id) {
  const el = document.getElementById(id);
  el.style.display = el.style.display === 'none' ? 'flex' : 'none';
}

// Close modal when clicking overlay
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.style.display = 'none';
  }
});

// ── TOAST ─────────────────────────────────────────────────────────────────
function showToast(msg, type = 'success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className   = `toast${type === 'error' ? ' error' : ''} show`;
  setTimeout(() => { t.className = 'toast'; }, 3000);
}

// ── SCORE BARS ────────────────────────────────────────────────────────────
// Animate on page load
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.score-bar').forEach(bar => {
    const target = bar.style.width;
    bar.style.width = '0%';
    setTimeout(() => { bar.style.width = target; }, 100);
  });
});
