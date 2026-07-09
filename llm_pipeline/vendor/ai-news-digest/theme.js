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
    document.querySelectorAll('.theme-toggle').forEach(function (btn) {
      var isLight = theme === 'light';
      btn.setAttribute('aria-label', isLight ? 'Switch to dark mode' : 'Switch to light mode');
      btn.textContent = isLight ? '\u263E' : '\u2600';
      btn.title = isLight ? 'Dark mode' : 'Light mode';
    });
    try {
      document.dispatchEvent(new CustomEvent('aidigest-theme-change', {
        detail: { theme: theme === 'light' ? 'light' : 'dark' }
      }));
    } catch (e) {}
    syncEmbeddedThemes(theme);
  }

  function syncEmbeddedThemes(theme) {
    var value = theme === 'light' ? 'light' : 'dark';
    document.querySelectorAll('iframe').forEach(function (frame) {
      try {
        if (frame.contentDocument && frame.contentDocument.documentElement) {
          frame.contentDocument.documentElement.setAttribute('data-theme', value);
        }
        if (frame.contentWindow) {
          frame.contentWindow.postMessage({ type: 'aidigest-theme', theme: value }, '*');
        }
      } catch (e) {}
    });
  }

  function authorCards() {
    return Array.prototype.slice.call(document.querySelectorAll('.frame-author'));
  }

  function authorExpanded() {
    var cards = authorCards();
    return cards.length === 0 || !cards[0].classList.contains('is-collapsed');
  }

  function setAuthorExpanded(expanded) {
    authorCards().forEach(function (card) {
      card.classList.toggle('is-collapsed', !expanded);
      card.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    });
    document.querySelectorAll('.author-toggle').forEach(function (btn) {
      btn.classList.toggle('is-active', expanded);
      btn.setAttribute('aria-pressed', expanded ? 'true' : 'false');
      btn.setAttribute('aria-label', expanded ? 'Hide author info' : 'Show author info');
      btn.title = expanded ? 'Hide author info' : 'Show author info';
    });
  }

  function toggleAuthor() {
    setAuthorExpanded(!authorExpanded());
  }

  function mountThemeToggle(container) {
    if (!container || container.querySelector('.theme-toggle')) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'theme-toggle';
    btn.addEventListener('click', function () {
      var next = preferredTheme() === 'light' ? 'dark' : 'light';
      try { localStorage.setItem(STORAGE_KEY, next); } catch (e) {}
      applyTheme(next);
    });
    container.appendChild(btn);
    applyTheme(preferredTheme());
  }

  function mountAuthorToggle(container) {
    if (!container || container.querySelector('.author-toggle')) return;
    if (!authorCards().length) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'author-toggle';
    btn.innerHTML = '<span class="author-toggle-i">i</span>';
    btn.addEventListener('click', toggleAuthor);
    var themeBtn = container.querySelector('.theme-toggle');
    if (themeBtn) container.insertBefore(btn, themeBtn);
    else container.appendChild(btn);
  }

  function wireAuthorCard() {
    authorCards().forEach(function (card) {
      if (card.dataset.authorWired === '1') return;
      card.dataset.authorWired = '1';
      card.setAttribute('aria-expanded', 'true');

      var dismiss = card.querySelector('.frame-author-dismiss');
      if (dismiss) {
        dismiss.addEventListener('click', function (ev) {
          ev.stopPropagation();
          setAuthorExpanded(false);
        });
      }

      card.addEventListener('click', function (ev) {
        ev.stopPropagation();
      });
    });
    setAuthorExpanded(true);
  }

  function isEmbeddedView() {
    try {
      return window.self !== window.top;
    } catch (e) {
      return true;
    }
  }

  function mountControls() {
    applyTheme(preferredTheme());
    if (isEmbeddedView()) return;

    var host = document.querySelector('.frame-controls');
    if (!host) {
      host = document.createElement('div');
      host.className = 'frame-controls';
      document.body.insertBefore(host, document.body.firstChild);
    }
    mountAuthorToggle(host);
    mountThemeToggle(host);
    wireAuthorCard();
  }

  applyTheme(preferredTheme());
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mountControls);
  } else {
    mountControls();
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      preferredTheme: preferredTheme,
      applyTheme: applyTheme,
      setAuthorExpanded: setAuthorExpanded,
      authorExpanded: authorExpanded
    };
  }
})();
