// Tercih yalnızca bu tarayıcıda saklanır; sunucuya gönderilmez.
(() => {
  let theme = 'system';
  let density = 'comfortable';
  let sidebar = 'expanded';
  try {
    theme = localStorage.getItem('library-theme') || theme;
    density = localStorage.getItem('library-density') || density;
    sidebar = localStorage.getItem('library-sidebar') || sidebar;
  } catch (_) { /* Depolama kapalıysa sistem tercihi. */ }
  const dark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  document.documentElement.dataset.themePreference = theme;
  document.documentElement.dataset.density = density;
  document.documentElement.dataset.sidebar = sidebar;
})();
