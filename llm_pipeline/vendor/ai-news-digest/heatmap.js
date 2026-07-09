(function (global) {
  function cssVar(name, fallback) {
    try {
      var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      return v || fallback;
    } catch (e) {
      return fallback;
    }
  }

  function palette() {
    return {
      empty: cssVar('--hm-empty', '#21262d'),
      l1: cssVar('--hm-1', '#1a3a5c'),
      l2: cssVar('--hm-2', '#1a4a7a'),
      l3: cssVar('--hm-3', '#1a6fa0'),
      l4: cssVar('--hm-4', '#58a6ff'),
      label: cssVar('--hm-label', '#8b949e'),
      selection: cssVar('--hm-selection', '#58a6ff'),
      hover: cssVar('--hm-hover', '#8b949e')
    };
  }

  function fillForSig(sig) {
    var p = palette();
    if (sig >= 4.5) return p.l4;
    if (sig >= 3.5) return p.l3;
    if (sig >= 2.5) return p.l2;
    return p.l1;
  }

  function fillForIntensity(intensity) {
    var p = palette();
    if (intensity >= 0.85) return p.l4;
    if (intensity >= 0.65) return p.l3;
    if (intensity >= 0.45) return p.l2;
    if (intensity >= 0.25) return p.l1;
    return p.empty;
  }

  function emptyFill() {
    return palette().empty;
  }

  global.AIDigestHeatmap = {
    palette: palette,
    fillForSig: fillForSig,
    fillForIntensity: fillForIntensity,
    emptyFill: emptyFill
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = global.AIDigestHeatmap;
  }
})(typeof window !== 'undefined' ? window : globalThis);
