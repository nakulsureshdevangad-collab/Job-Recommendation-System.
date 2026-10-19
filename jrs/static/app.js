document.addEventListener('click', async (event) => {
  const dismiss = event.target.closest('.dismiss');
  if (dismiss) dismiss.closest('.flash')?.remove();
  const copy = event.target.closest('[data-copy-target]');
  if (copy) {
    const target = document.getElementById(copy.dataset.copyTarget);
    if (target) {
      try { await navigator.clipboard.writeText(target.value); copy.textContent = 'Copied ✓'; }
      catch { target.select(); document.execCommand('copy'); copy.textContent = 'Copied ✓'; }
      setTimeout(() => { copy.textContent = 'Copy text'; }, 1800);
    }
  }
});
document.addEventListener('submit', (event) => {
  const form = event.target.closest('form[data-confirm]');
  if (form && !window.confirm(form.dataset.confirm)) event.preventDefault();
});
