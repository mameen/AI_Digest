(function () {
  var STORAGE_KEY = 'aidigest-theme';

  function preferredTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY) || 'dark';
    } catch (e) {
      return 'dark';
    }
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme === 'light' ? 'light' : 'dark');
  }

  applyTheme(preferredTheme());

  window.addEventListener('storage', function (e) {
    if (e.key === STORAGE_KEY) {
      applyTheme(e.newValue || 'dark');
    }
  });

  window.addEventListener('message', function (e) {
    if (e.data && e.data.type === 'aidigest-theme') {
      applyTheme(e.data.theme);
    }
  });
})();
