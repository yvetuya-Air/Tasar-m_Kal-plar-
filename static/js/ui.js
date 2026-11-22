(() => {
  const root = document.documentElement;
  function setPreference(key, value) {
    let saved = true;
    try { localStorage.setItem(`library-${key}`, value); } catch (_) { saved = false; }
    if (key === 'theme') {
      root.dataset.themePreference = value;
      root.dataset.theme = value === 'dark' || (value === 'system' && matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
    } else { root.dataset.density = value; }
    updateThemeUI();
    const status = document.getElementById('preference-status');
    if (status) status.textContent = saved ? 'Görünüm tercihiniz bu tarayıcıda kaydedildi.' : 'Tarayıcı depolaması kapalı; tercih yalnızca bu sayfada uygulandı.';
  }
  function updateThemeUI() {
    document.querySelectorAll('.theme-toggle').forEach(button => button.setAttribute('aria-label', root.dataset.theme === 'dark' ? 'Açık temaya geç' : 'Koyu temaya geç'));
    document.querySelectorAll('[data-theme-choice]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.themeChoice === root.dataset.themePreference)));
    document.querySelectorAll('[data-density-choice]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.densityChoice === root.dataset.density)));
  }
  document.querySelectorAll('.theme-toggle').forEach(button => button.addEventListener('click', () => setPreference('theme', root.dataset.theme === 'dark' ? 'light' : 'dark')));
  document.querySelectorAll('[data-theme-choice]').forEach(button => button.addEventListener('click', () => setPreference('theme', button.dataset.themeChoice)));
  document.querySelectorAll('[data-density-choice]').forEach(button => button.addEventListener('click', () => setPreference('density', button.dataset.densityChoice)));
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { if (root.dataset.themePreference === 'system') { root.dataset.theme = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'; updateThemeUI(); } });
  updateThemeUI();
  const menu = document.getElementById('menu-toggle');
  const backdrop = document.getElementById('sidebar-backdrop');
  const collapse = document.getElementById('sidebar-collapse');
  function updateSidebar() {
    const expanded = root.dataset.sidebar !== 'collapsed';
    collapse?.setAttribute('aria-expanded', String(expanded));
    collapse?.setAttribute('aria-label', expanded ? 'Kenar menüsünü daralt' : 'Kenar menüsünü genişlet');
  }
  collapse?.addEventListener('click', () => {
    root.dataset.sidebar = root.dataset.sidebar === 'collapsed' ? 'expanded' : 'collapsed';
    try { localStorage.setItem('library-sidebar', root.dataset.sidebar); } catch (_) { /* Bu sayfada uygulanır. */ }
    updateSidebar();
  });
  updateSidebar();
  function closeMenu() { root.classList.remove('sidebar-open'); if (menu) menu.setAttribute('aria-expanded', 'false'); if (backdrop) backdrop.hidden = true; }
  if (menu) menu.addEventListener('click', () => { const open = !root.classList.contains('sidebar-open'); root.classList.toggle('sidebar-open', open); menu.setAttribute('aria-expanded', String(open)); backdrop.hidden = !open; if (open) document.querySelector('.sidebar-nav a')?.focus(); });
  backdrop?.addEventListener('click', closeMenu);
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && root.classList.contains('sidebar-open')) { closeMenu(); menu?.focus(); } });
  matchMedia('(min-width: 981px)').addEventListener('change', closeMenu);
  // Mobil çekmecede klavye odağı arka plandaki kontrollerden uzak tutulur.
  document.addEventListener('keydown', event => {
    if (event.key !== 'Tab' || !root.classList.contains('sidebar-open')) return;
    const links = Array.from(document.querySelectorAll('#sidebar a, #sidebar button'));
    const first = links[0], last = links[links.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  });
  document.querySelectorAll('.dismiss-notice').forEach(button => button.addEventListener('click', () => button.closest('.notice').remove()));
  const dialog = document.getElementById('confirm-dialog');
  let pendingForm = null;
  let pendingButton = null;
  document.addEventListener('submit', event => {
    const form = event.target;
    const message = event.submitter?.dataset.confirm || form.dataset.confirm;
    if (!message) return;
    if (form.dataset.confirmed === 'yes') return;
    if (!dialog?.showModal) { if (!window.confirm(message)) event.preventDefault(); return; }
    event.preventDefault(); pendingForm = form; pendingButton = event.submitter;
    document.getElementById('confirm-message').textContent = message;
    dialog.showModal(); document.getElementById('confirm-no').focus();
  });
  document.getElementById('confirm-yes')?.addEventListener('click', () => {
    if (!pendingForm) return;
    pendingForm.dataset.confirmed = 'yes';
    dialog.close();
    pendingForm.requestSubmit(pendingButton || undefined);
    delete pendingForm.dataset.confirmed;
    pendingForm = null;
    pendingButton = null;
  });
  document.getElementById('confirm-no')?.addEventListener('click', () => { dialog.close(); pendingForm = null; pendingButton = null; });
  dialog?.addEventListener('cancel', () => { pendingForm = null; pendingButton = null; });
  document.addEventListener('submit', event => {
    if (!event.defaultPrevented) event.submitter?.setAttribute('aria-busy', 'true');
  });
  window.addEventListener('pageshow', () => {
    document.querySelectorAll('button[aria-busy=true]').forEach(button => button.removeAttribute('aria-busy'));
  });
  // Grafik değerleri SVG title/aria etiketleri ve erişilebilir tabloyla da sunulur.
  document.querySelectorAll('[data-chart-value]').forEach(bar => {
    const show = () => { const target = document.getElementById('chart-readout'); if (target) target.textContent = bar.dataset.chartValue; };
    bar.addEventListener('mouseenter', show); bar.addEventListener('focus', show);
  });
})();
