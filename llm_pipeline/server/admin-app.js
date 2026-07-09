(function () {
  'use strict';

  var API = (typeof window !== 'undefined' && window.__ADMIN_API__) || '';
  var TUNING_TABS = [
    { id: 'pipeline', label: 'Pipeline & ingest', kind: 'config' },
    { id: 'enrich', label: 'Enrich & LLM', kind: 'config' },
    { id: 'publish', label: 'Validation & site', kind: 'config' },
    { id: 'brief', label: 'Editorial brief', kind: 'brief' },
    { id: 'prompts', label: 'Prompt passes', kind: 'reference' }
  ];
  var PROMPT_REFERENCE =
    'LLM enrich passes (pipeline/enrich.py)\n\n' +
    'Every pass prepends pipeline/editorial_brief.md, then adds a task block:\n\n' +
    '1. Skeleton enrich (_llm_category_enrich)\n' +
    '   aisearch, youtube, research, typography, robotics\n' +
    '   Extra rules per category in _skeleton_rules()\n\n' +
    '2. Curation (_llm_curate_category)\n' +
    '   Trims to enrich.category_targets (aisearch default 10; youtube null = keep all)\n\n' +
    '3. Leaderboard (_llm_leaderboard)\n' +
    '   6 stories from crawled leaderboard markdown + llm-stats\n\n' +
    '4. Gap fill (_llm_gap_fill)\n' +
    '   analytics, agentic-ai, llm, rag, image-gen, design-ai\n' +
    '   Strict URL grounding from ingestion context\n\n' +
    '5. Daily summary (_llm_summary)\n' +
    '   One-sentence masthead + aisearch video label\n\n' +
    'Optional: enrich.tool_loop.enabled — agentic URL verify (default off)\n\n' +
    'See docs/TUNING.md for source knobs (YouTube channels, link_extract, etc.)';

  var SECTION_KEYS = {
    pipeline: ['run', 'output', 'diagnostics', 'ingestion'],
    enrich: ['llm', 'enrich'],
    publish: ['validation', 'render', 'site']
  };

  var SECTION_META = {
    pipeline: {
      label: 'Pipeline & ingest',
      hint: 'Run window, doctor, output dirs, crawl4ai, structured sources.'
    },
    enrich: {
      label: 'Enrich & LLM',
      hint: 'Model, batch sizes, category targets, tool loop, carry-forward.'
    },
    publish: {
      label: 'Validation & site',
      hint: 'Story minimums, required categories, render flags, footer links.'
    }
  };

  function splitConfigYaml(yaml) {
    var blocks = {};
    var currentKey = null;
    var currentLines = [];
    var lines = String(yaml || '').split('\n');

    function flush() {
      if (currentKey) blocks[currentKey] = currentLines.join('\n').replace(/\n+$/, '');
    }

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      var match = /^([a-z_][\w-]*):\s*(.*)$/i.exec(line);
      if (match && line.charAt(0) !== ' ' && line.charAt(0) !== '\t') {
        flush();
        currentKey = match[1];
        currentLines = [line];
      } else if (currentKey) {
        currentLines.push(line);
      }
    }
    flush();

    var sections = { pipeline: '', enrich: '', publish: '' };
    Object.keys(SECTION_KEYS).forEach(function (sectionId) {
      var parts = [];
      SECTION_KEYS[sectionId].forEach(function (key) {
        if (blocks[key]) parts.push(blocks[key]);
      });
      sections[sectionId] = parts.join('\n');
    });
    return sections;
  }

  var state = {
    readonly: true,
    deploy: 'unknown',
    apiLive: false,
    precheckOk: false,
    git: null,
    digests: [],
    jobs: [],
    configSections: { pipeline: '', enrich: '', publish: '' },
    tuningMeta: {},
    editorialBrief: '',
    activeTab: 'pipeline'
  };

  function pageLocation() {
    if (typeof location !== 'undefined') return location;
    if (typeof window !== 'undefined' && window.location) return window.location;
    return {};
  }

  function deployMode(loc) {
    var L = loc || pageLocation();
    var h = (L.hostname || '').toLowerCase();
    if (h === 'mameen.github.io' || h.endsWith('.github.io')) return 'pages';
    if (L.protocol === 'file:') return 'file';
    if (h === '127.0.0.1' || h === 'localhost') return 'local';
    return 'unknown';
  }

  function isDeployedViewOnly() {
    return deployMode() === 'pages' || (typeof window !== 'undefined' && window.__ADMIN_READONLY__ === true);
  }

  function isFullControl() {
    return !isDeployedViewOnly() && state.apiLive;
  }

  function isPagesReadonly() {
    return isDeployedViewOnly();
  }

  function resolveReadonly() {
    return !isFullControl();
  }

  function canTune() {
    return !state.readonly && state.git && !state.git.on_main;
  }

  function tuningLocked() {
    return !state.readonly && state.git && state.git.on_main;
  }

  function activeTabMeta() {
    for (var i = 0; i < TUNING_TABS.length; i++) {
      if (TUNING_TABS[i].id === state.activeTab) return TUNING_TABS[i];
    }
    return TUNING_TABS[0];
  }

  function editorValue() {
    var tab = activeTabMeta();
    if (tab.kind === 'brief') return state.editorialBrief;
    if (tab.kind === 'reference') return PROMPT_REFERENCE;
    return state.configSections[tab.id] || '';
  }

  function persistEditorValue() {
    if (state.readonly || !canTune()) return;
    var editor = $('tuning-editor');
    if (!editor) return;
    var tab = activeTabMeta();
    if (tab.kind === 'brief') state.editorialBrief = editor.value;
    else if (tab.kind === 'config') state.configSections[tab.id] = editor.value;
  }

  function $(id) { return document.getElementById(id); }

  function esc(s) {
    return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
  }

  function apiUrl(path) {
    var base = API || '';
    if (base && base.charAt(base.length - 1) === '/') base = base.slice(0, -1);
    return base + path;
  }

  function fetchJson(path, opts) {
    opts = opts || {};
    return fetch(apiUrl(path), opts).then(function (r) {
      if (!r.ok) return r.json().then(function (j) { throw new Error(j.error || r.statusText); });
      return r.json();
    });
  }

  function fetchText(path) {
    return fetch(path).then(function (r) {
      if (!r.ok) throw new Error('Failed to load ' + path);
      return r.text();
    });
  }

  function setPill(id, text, cls) {
    var el = $(id);
    if (!el) return;
    el.textContent = text;
    el.className = 'admin-pill' + (cls ? ' ' + cls : '');
  }

  function updateChrome() {
    state.readonly = resolveReadonly();
    var banner = $('admin-readonly-banner');
    if (banner) {
      if (state.readonly) {
        banner.classList.remove('hidden');
        if (isDeployedViewOnly()) {
          banner.innerHTML =
            '<strong>View only</strong> — deployed on GitHub Pages. Browse config, prompts, and digests. ' +
            'For pipeline runs, git, and edits: <code>python run.py --server</code> on your machine.';
        } else if (state.deploy === 'file') {
          banner.innerHTML =
            '<strong>Read-only</strong> — open via <code>python run.py --server</code> for local API control.';
        } else {
          banner.innerHTML =
            '<strong>Read-only</strong> — local admin API offline. Start <code>python run.py --server</code>.';
        }
      } else {
        banner.classList.add('hidden');
      }
    }
    if (state.readonly) {
      if (isDeployedViewOnly()) {
        setPill('admin-api-pill', 'view only', 'admin-pill-readonly');
      } else {
        setPill('admin-api-pill', 'view only', 'admin-pill-warn');
      }
    } else {
      setPill('admin-api-pill', 'full control', 'admin-pill-ok');
    }
    if (state.git) {
      var g = state.git.branch + (state.git.dirty ? ' *' : '');
      setPill('admin-git-pill', g, state.git.on_main && state.git.dirty ? 'admin-pill-warn' : '');
    }
    if (state.readonly) {
      setPill('admin-precheck-pill', 'view only', 'admin-pill-readonly');
    } else if (state.precheckOk) {
      setPill('admin-precheck-pill', 'precheck ok', 'admin-pill-ok');
    } else {
      setPill('admin-precheck-pill', 'precheck pending', 'admin-pill-warn');
    }
    render();
  }

  function probeApi() {
    if (isPagesReadonly()) {
      state.apiLive = false;
      state.deploy = 'pages';
      return loadStaticData().then(updateChrome);
    }
    return fetchJson('/api/health').then(function () {
      state.apiLive = true;
      state.deploy = 'local';
      return refreshAll();
    }).catch(function () {
      state.apiLive = false;
      state.deploy = deployMode();
      return loadStaticData();
    }).then(updateChrome);
  }

  function applyConfigBundle(c) {
    state.editorialBrief = c.editorial_brief || '';
    if (c.config_sections) {
      state.configSections = c.config_sections;
    } else if (c.config_yaml) {
      state.configSections = splitConfigYaml(c.config_yaml);
    }
    state.tuningMeta = c.tuning_sections || SECTION_META;
  }

  function loadStaticData() {
    return Promise.all([
      fetchText('../config.yaml').catch(function () { return '# config.yaml unavailable'; }),
      fetchText('../pipeline/editorial_brief.md').catch(function () { return '# editorial brief unavailable'; }),
      fetch('../reports/index.json').then(function (r) { return r.ok ? r.json() : { digests: [] }; }).catch(function () { return { digests: [] }; })
    ]).then(function (parts) {
      applyConfigBundle({ config_yaml: parts[0], editorial_brief: parts[1] });
      state.digests = (parts[2].digests || []).map(function (d) {
        return {
          prefix: d.prefix,
          display_date: d.display_date,
          story_count: d.story_count,
          has_html: true,
          has_json: true,
          has_diagnostics: true
        };
      });
    });
  }

  function refreshAll() {
    return Promise.all([
      fetchJson('/api/git/status').then(function (g) { state.git = g; }),
      fetchJson('/api/config').then(function (c) {
        applyConfigBundle(c);
        if (c.git) state.git = c.git;
      }),
      fetchJson('/api/digests').then(function (d) { state.digests = d.digests || []; }),
      fetchJson('/api/jobs').then(function (j) { state.jobs = j.jobs || []; }),
      fetchJson('/api/precheck').then(function (p) { state.precheckOk = !!p.ok; })
    ]).catch(function (e) {
      console.warn(e);
    });
  }

  function disabledAttr() { return state.readonly ? ' disabled' : ''; }

  function tuningHintHtml() {
    if (state.readonly) {
      return '<p class="hint">Browse tuning files read-only. Local server required to edit.</p>';
    }
    if (tuningLocked()) {
      return '<p class="hint admin-tuning-locked">' +
        'Tuning is <strong>locked on main</strong>. Use <em>Create tuning branch</em> above before editing or saving.' +
        '</p>';
    }
    var meta = state.tuningMeta[state.activeTab];
    if (meta && meta.hint) {
      return '<p class="hint">' + esc(meta.hint) + '</p>';
    }
    if (state.activeTab === 'brief') {
      return '<p class="hint">Shared editorial voice — prepended to every enrich LLM call.</p>';
    }
    if (state.activeTab === 'prompts') {
      return '<p class="hint">Read-only map of enrich passes. Edit task rules in <code>pipeline/enrich.py</code> or <code>docs/TUNING.md</code>.</p>';
    }
    return '<p class="hint">Edit this section, then save. Other config sections stay unchanged.</p>';
  }

  function render() {
    var root = $('admin-root');
    if (!root) return;
    var ro = state.readonly;
    var runDisabled = ro || !state.precheckOk ? ' disabled' : '';
    var tune = canTune();
    var tab = activeTabMeta();
    var editorReadonly = ro || !tune || tab.kind === 'reference';
    var saveDisabled = ro || !tune || tab.kind === 'reference' ? ' disabled' : '';

    root.innerHTML =
      '<section class="admin-card">' +
        '<h2>Deployment precheck</h2>' +
        '<p class="hint">Lint + tests must pass before pipeline runs (local admin only).</p>' +
        '<div class="admin-row">' +
          '<button type="button" class="admin-btn admin-btn-primary" id="btn-precheck"' + disabledAttr() + '>Run lint &amp; test</button>' +
          '<span id="precheck-msg" style="font-size:11px;color:var(--muted)"></span>' +
        '</div>' +
        '<pre class="admin-log" id="precheck-log"></pre>' +
      '</section>' +

      '<section class="admin-card">' +
        '<h2>Pipeline</h2>' +
        '<p class="hint">Full run, ingest-only, skeleton, or frontend rebuild.</p>' +
        '<div class="admin-row"><label>Start</label><input class="admin-input" id="pipe-start" type="date" value="2026-07-03"' + (ro ? ' readonly' : '') + '></div>' +
        '<div class="admin-row"><label>History</label><input class="admin-input" id="pipe-history" type="number" min="1" max="30" value="10" style="width:72px"' + (ro ? ' readonly' : '') + '></div>' +
        '<div class="admin-row"><label>Mode</label>' +
          '<select class="admin-select" id="pipe-mode"' + disabledAttr() + '>' +
            '<option value="full">Full pipeline</option>' +
            '<option value="fetch-only">Fetch only</option>' +
            '<option value="skeleton-only">Skeleton only</option>' +
            '<option value="archives-only">Frontend / archives only</option>' +
          '</select>' +
        '</div>' +
        '<div class="admin-row">' +
          '<button type="button" class="admin-btn admin-btn-primary" id="btn-pipeline"' + runDisabled + '>Launch pipeline</button>' +
        '</div>' +
        '<pre class="admin-log" id="job-log"></pre>' +
      '</section>' +

      '<section class="admin-card">' +
        '<h2>Git workflow</h2>' +
        '<p class="hint">Create a tuning branch before editing config or prompts.</p>' +
        '<div class="admin-row">' +
          '<button type="button" class="admin-btn admin-btn-primary" id="btn-branch"' + disabledAttr() + '>Create tuning branch</button>' +
          '<button type="button" class="admin-btn" id="btn-commit"' + disabledAttr() + '>Commit</button>' +
          '<button type="button" class="admin-btn" id="btn-push"' + disabledAttr() + '>Push branch</button>' +
          '<button type="button" class="admin-btn admin-btn-danger" id="btn-merge"' + disabledAttr() + '>Merge → main</button>' +
        '</div>' +
      '</section>' +

      '<section class="admin-card admin-card-wide">' +
        '<h2>Tuning</h2>' +
        tuningHintHtml() +
        '<div class="admin-tabs">' +
        TUNING_TABS.map(function (t) {
          return '<button type="button" class="admin-tab' + (state.activeTab === t.id ? ' active' : '') +
            '" data-tab="' + t.id + '">' + esc(t.label) + '</button>';
        }).join('') +
        '</div>' +
        '<textarea class="admin-textarea' + (editorReadonly ? ' is-locked' : '') + '" id="tuning-editor"' +
          (editorReadonly ? ' readonly' : '') + '>' +
          esc(editorValue()) +
        '</textarea>' +
        '<div class="admin-row" style="margin-top:10px">' +
          '<button type="button" class="admin-btn admin-btn-primary" id="btn-save-config"' + saveDisabled + '>Save section</button>' +
        '</div>' +
      '</section>' +

      '<section class="admin-card admin-card-wide">' +
        '<h2>Digests</h2>' +
        '<div class="admin-table-wrap"><table class="admin-table"><thead><tr>' +
          '<th>Prefix</th><th>Date</th><th>Stories</th><th>Actions</th>' +
        '</tr></thead><tbody>' +
        state.digests.map(function (d) {
          return '<tr><td><code>' + esc(d.prefix) + '</code></td><td>' + esc(d.display_date || '') + '</td><td>' +
            esc(d.story_count != null ? d.story_count : '—') + '</td><td>' +
            '<button type="button" class="admin-btn" data-render="' + esc(d.prefix) + '"' + disabledAttr() + '>Re-render</button> ' +
            '<button type="button" class="admin-btn admin-btn-danger" data-delete="' + esc(d.prefix) + '"' + disabledAttr() + '>Delete</button>' +
            '</td></tr>';
        }).join('') +
        '</tbody></table></div>' +
      '</section>' +

      '<section class="admin-card">' +
        '<h2>Local server</h2>' +
        '<p class="hint"><code>run.py --server</code> keeps running until you stop it (Ctrl+C in the terminal, or here).</p>' +
        '<div class="admin-row">' +
          '<button type="button" class="admin-btn admin-btn-danger" id="btn-shutdown"' + disabledAttr() + '>Stop server</button>' +
          '<span id="shutdown-msg" style="font-size:11px;color:var(--muted)"></span>' +
        '</div>' +
      '</section>';

    wireEvents();
  }

  function wireEvents() {
    var pre = $('btn-precheck');
    if (pre) pre.onclick = runPrecheck;
    var pipe = $('btn-pipeline');
    if (pipe) pipe.onclick = launchPipeline;
    var branch = $('btn-branch');
    if (branch) branch.onclick = createBranch;
    var commit = $('btn-commit');
    if (commit) commit.onclick = gitCommit;
    var push = $('btn-push');
    if (push) push.onclick = gitPush;
    var merge = $('btn-merge');
    if (merge) merge.onclick = gitMerge;
    var save = $('btn-save-config');
    if (save) save.onclick = saveConfig;
    var shutdown = $('btn-shutdown');
    if (shutdown) shutdown.onclick = shutdownServer;

    document.querySelectorAll('.admin-tab').forEach(function (btn) {
      btn.onclick = function () {
        persistEditorValue();
        state.activeTab = btn.getAttribute('data-tab');
        render();
      };
    });

    document.querySelectorAll('[data-render]').forEach(function (btn) {
      btn.onclick = function () {
        renderOnly(btn.getAttribute('data-render'));
      };
    });
    document.querySelectorAll('[data-delete]').forEach(function (btn) {
      btn.onclick = function () {
        deleteDigest(btn.getAttribute('data-delete'));
      };
    });
  }

  function runPrecheck() {
    if (state.readonly) return;
    var log = $('precheck-log');
    if (log) log.textContent = 'Running compileall + run_tests.py…';
    fetchJson('/api/precheck', { method: 'POST' }).then(function (r) {
      state.precheckOk = !!r.ok;
      if (log) log.textContent = (r.log || []).join('\n');
      var msg = $('precheck-msg');
      if (msg) msg.textContent = r.ok ? 'All green — pipeline enabled.' : 'Fix failures before running.';
      updateChrome();
    }).catch(function (e) {
      if (log) log.textContent = String(e.message || e);
    });
  }

  function launchPipeline() {
    if (state.readonly || !state.precheckOk) return;
    var start = ($('pipe-start') || {}).value;
    var history = parseInt(($('pipe-history') || {}).value, 10) || 10;
    var mode = ($('pipe-mode') || {}).value || 'full';
    fetchJson('/api/pipeline/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: mode, start: start, history: history })
    }).then(function (job) {
      pollJob(job.id);
    }).catch(function (e) { alert(e.message || e); });
  }

  function renderOnly(prefix) {
    if (state.readonly) return;
    fetchJson('/api/pipeline/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'render-only', prefix: prefix })
    }).then(function (job) { pollJob(job.id); }).catch(function (e) { alert(e.message || e); });
  }

  function deleteDigest(prefix) {
    if (state.readonly) return;
    if (!confirm('Delete digest ' + prefix + ' and its artifacts?')) return;
    fetchJson('/api/digests/' + prefix, { method: 'DELETE' }).then(function () {
      return refreshAll();
    }).then(updateChrome).catch(function (e) { alert(e.message || e); });
  }

  function pollJob(id) {
    var log = $('job-log');
    var tick = function () {
      fetchJson('/api/jobs/' + id).then(function (job) {
        if (log) log.textContent = (job.log || []).join('\n');
        if (job.state === 'running' || job.state === 'queued') {
          setTimeout(tick, 1500);
        } else {
          refreshAll().then(updateChrome);
        }
      });
    };
    tick();
  }

  function createBranch() {
    if (state.readonly) return;
    fetchJson('/api/git/branch', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      .then(function (r) {
        alert(r.created ? 'Created ' + r.branch : 'On ' + r.branch);
        return refreshAll();
      })
      .then(updateChrome).catch(function (e) { alert(e.message || e); });
  }

  function gitCommit() {
    if (state.readonly) return;
    var msg = prompt('Commit message:');
    if (!msg) return;
    fetchJson('/api/git/commit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    }).then(function () { return refreshAll(); }).then(updateChrome).catch(function (e) { alert(e.message || e); });
  }

  function gitPush() {
    if (state.readonly) return;
    fetchJson('/api/git/push', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      .then(function () { alert('Pushed.'); }).catch(function (e) { alert(e.message || e); });
  }

  function gitMerge() {
    if (state.readonly) return;
    if (!confirm('Merge current branch into main locally? Review changes first.')) return;
    fetchJson('/api/git/merge-main', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      .then(function (r) { alert('Merged ' + r.merged); return refreshAll(); }).then(updateChrome)
      .catch(function (e) { alert(e.message || e); });
  }

  function saveConfig() {
    if (!canTune()) {
      alert('Create a tuning branch before saving.');
      return;
    }
    var editor = $('tuning-editor');
    if (!editor) return;
    var tab = activeTabMeta();
    if (tab.kind === 'reference') return;

    var body = {};
    if (tab.kind === 'brief') body.editorial_brief = editor.value;
    else {
      body.config_section = tab.id;
      body.section_yaml = editor.value;
    }

    fetchJson('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function () {
      alert('Saved ' + tab.label + '.');
      return refreshAll();
    }).then(updateChrome).catch(function (e) { alert(e.message || e); });
  }

  function shutdownServer() {
    if (state.readonly) return;
    if (!confirm('Stop the local server on this machine?')) return;
    var msg = $('shutdown-msg');
    if (msg) msg.textContent = 'Shutting down…';
    fetchJson('/api/shutdown', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      .then(function () {
        state.apiLive = false;
        if (msg) msg.textContent = 'Server stopped.';
        setPill('admin-api-pill', 'server stopped', 'admin-pill-warn');
      })
      .catch(function (e) {
        if (msg) msg.textContent = String(e.message || e);
      });
  }

  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', probeApi);
    } else {
      probeApi();
    }
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
      deployMode: deployMode,
      isPagesReadonly: isPagesReadonly,
      isDeployedViewOnly: isDeployedViewOnly,
      isFullControl: isFullControl,
      canTune: canTune,
      tuningLocked: tuningLocked,
      splitConfigYaml: splitConfigYaml,
      pageLocation: pageLocation
    };
  }
})();
