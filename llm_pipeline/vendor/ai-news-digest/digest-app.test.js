// Tests for the leaderboard widget logic in digest-app.js.
// Run with:  node --test vendor/ai-news-digest/
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const { PROVIDER_COLORS, resolveLbColumns, renderLbLinks, lbTooltip, sourceLinkHtml, provenanceHtml, escHtml, storyCopyFormats, reportSourceSealMarkup } = require('./digest-app.js');

// ── Extract the `const leaderboards = {…}` object literal from a template ──
function extractLeaderboards(html) {
  const marker = 'const leaderboards = ';
  const start = html.indexOf(marker);
  assert.ok(start >= 0, 'leaderboards marker not found');
  const objStart = start + marker.length;
  let depth = 0, inStr = false, quote = '', esc = false;
  for (let i = objStart; i < html.length; i++) {
    const ch = html[i];
    if (inStr) {
      if (esc) esc = false;
      else if (ch === '\\') esc = true;
      else if (ch === quote) inStr = false;
    } else if (ch === '"' || ch === "'" || ch === '`') { inStr = true; quote = ch; }
    else if (ch === '{') depth++;
    else if (ch === '}' && --depth === 0) return html.slice(objStart, i + 1);
  }
  throw new Error('unbalanced leaderboards object');
}

const templateHtml = fs.readFileSync(path.join(__dirname, 'template.html'), 'utf8');
const leaderboards = eval('(' + extractLeaderboards(templateHtml) + ')');

// ── resolveLbColumns: defaults per active tab + explicit overrides ──
test('resolveLbColumns defaults for aa', () => {
  assert.deepStrictEqual(resolveLbColumns({}, 'aa'), { providerCol: 2, scoreCol: 3, scoreMax: 60 });
});
test('resolveLbColumns defaults for open-weight', () => {
  assert.deepStrictEqual(resolveLbColumns({}, 'open'), { providerCol: 2, scoreCol: -1, scoreMax: 100 });
});
test('resolveLbColumns defaults for other tabs (vellum)', () => {
  assert.deepStrictEqual(resolveLbColumns({}, 'vellum'), { providerCol: 1, scoreCol: -1, scoreMax: 100 });
});
test('resolveLbColumns honours explicit overrides regardless of tab', () => {
  const lb = { providerCol: 2, scoreCol: 3, scoreMax: 1600 };
  assert.deepStrictEqual(resolveLbColumns(lb, 'arena_video'), lb);
  assert.deepStrictEqual(resolveLbColumns(lb, 'aa'), lb);
});
test('resolveLbColumns treats 0 as a valid override (not null)', () => {
  assert.deepStrictEqual(
    resolveLbColumns({ providerCol: 0, scoreCol: 0, scoreMax: 0 }, 'aa'),
    { providerCol: 0, scoreCol: 0, scoreMax: 0 }
  );
});

// ── lbTooltip: plain-language glossary for column headers ──
test('lbTooltip explains the T2I Elo metric (mentions preference votes)', () => {
  const tip = lbTooltip('Elo');
  assert.ok(tip.length > 0, 'Elo must have a tooltip');
  assert.match(tip, /preference|head-to-head/i);
});
test('lbTooltip covers common metric labels', () => {
  for (const label of ['Intelligence', 'HumanEval+', 'Resolved %', 'Score', 'Votes']) {
    assert.ok(lbTooltip(label).length > 0, `missing tooltip for "${label}"`);
  }
});
test('lbTooltip returns empty string for unknown labels', () => {
  assert.strictEqual(lbTooltip('Totally Unknown Column'), '');
});

// ── renderLbLinks: pure markup, no tabs, correct anchors ──
test('renderLbLinks renders one anchor per item with name/url/source', () => {
  const lb = { groups: [{ label: 'Group A', items: [
    { name: 'Alpha', source: 'a.com', url: 'https://a.com/x' },
    { name: 'Beta', source: 'b.com', url: 'https://b.com/y' },
  ] }] };
  const html = renderLbLinks(lb);
  assert.match(html, /Group A/);
  assert.match(html, /href="https:\/\/a\.com\/x"/);
  assert.match(html, /href="https:\/\/b\.com\/y"/);
  assert.match(html, /Alpha/);
  assert.match(html, /a\.com \u2197/);
  assert.strictEqual((html.match(/<a /g) || []).length, 2);
  assert.ok(!html.includes('lb-tab'), 'links markup must not include tab buttons');
});

// ── provenanceHtml: light (i) affordance + hidden trace popover ──
test('provenanceHtml emits an (i) button and a trace block keyed by story id', () => {
  const html = provenanceHtml({ id: 'lb-gpt5', provenance: 'crawl:leaderboard', source: 'Artificial Analysis', url: 'https://x/y' });
  assert.match(html, /class="card-info"/);
  assert.match(html, /id="trace-lb-gpt5"/);
  assert.match(html, /hidden/);                       // popover starts hidden
  assert.match(html, /crawl:leaderboard/);            // the origin token is shown
  assert.match(html, /Artificial Analysis/);
  assert.match(html, /href|https:\/\/x\/y/);          // url row present when url exists
});
test('provenanceHtml omits the url row when there is no url, and marks unknown origin', () => {
  const html = provenanceHtml({ id: 's1', source: 'Src' });
  assert.doesNotMatch(html, /trace-k">url/);          // no url row
  assert.match(html, /unknown/);                      // missing provenance -> "unknown"
});
test('provenanceHtml shows a carried flag only when carried_forward is set', () => {
  const carried = provenanceHtml({ id: 's2', provenance: 'carry:20260101120000', source: 'Src', carried_forward: true });
  assert.match(carried, /carried/);
  const fresh = provenanceHtml({ id: 's3', provenance: 'gap:rag', source: 'Src' });
  assert.doesNotMatch(fresh, /trace-k">carried/);
});
test('escHtml neutralises angle brackets and quotes so trace values cannot inject markup', () => {
  const html = provenanceHtml({ id: 'x', provenance: 'gap:rag', source: '<img src=x onerror=alert(1)>' });
  assert.doesNotMatch(html, /<img /);
  assert.match(html, /&lt;img/);
  assert.strictEqual(escHtml('a&b"<>'), 'a&amp;b&quot;&lt;&gt;');
});

// ── storyCopyFormats: one copy action → rich HTML + Markdown fallback ──
const COPY_STORY = {
  id: 'lb-x', title: 'GPT-5 tops the board', summary: 'A big jump on reasoning.',
  source: 'Artificial Analysis', catLabel: '🏅 Leaderboards', tags: ['reasoning', 'model release'],
  url: 'https://example.com/gpt5', significance: 5
};

test('storyCopyFormats builds a linked, formatted HTML fragment', () => {
  const { html } = storyCopyFormats(COPY_STORY);
  assert.match(html, /<h3><a href="https:\/\/example\.com\/gpt5">GPT-5 tops the board<\/a><\/h3>/);
  assert.match(html, /<em>Artificial Analysis \u00b7 🏅 Leaderboards<\/em>/);
  assert.match(html, /<p>A big jump on reasoning\.<\/p>/);
  assert.match(html, /#reasoning #modelrelease/);         // spaces stripped inside a tag
  assert.match(html, /Read source \u2192<\/a>/);
});

test('storyCopyFormats builds Markdown with heading, meta, tags and link', () => {
  const { markdown } = storyCopyFormats(COPY_STORY);
  assert.match(markdown, /^## GPT-5 tops the board/);
  assert.match(markdown, /_Artificial Analysis \u00b7 🏅 Leaderboards_/);
  assert.match(markdown, /A big jump on reasoning\./);
  assert.match(markdown, /#reasoning #modelrelease/);
  assert.match(markdown, /\[Read source \u2192\]\(https:\/\/example\.com\/gpt5\)/);
});

test('storyCopyFormats omits the link when a story has no url and escapes HTML', () => {
  const { html, markdown } = storyCopyFormats({ id: 's', title: 'No <b>link</b>', summary: '', source: 'Src', tags: [] });
  assert.doesNotMatch(html, /<a /);                       // no dead link
  assert.doesNotMatch(markdown, /Read source/);
  assert.match(html, /<h3>No &lt;b&gt;link&lt;\/b&gt;<\/h3>/);   // title escaped, not injected
});

// ── sourceLinkHtml: real link vs. kept-topic "Source pending" ──
test('sourceLinkHtml renders a Read source anchor for a real url', () => {
  const html = sourceLinkHtml('https://www.figure.ai/news/project-go-big');
  assert.match(html, /^<a /);
  assert.match(html, /href="https:\/\/www\.figure\.ai\/news\/project-go-big"/);
  assert.match(html, /Read source/);
});
test('sourceLinkHtml degrades to a non-link Source pending span when url is missing', () => {
  for (const url of [null, undefined, '']) {
    const html = sourceLinkHtml(url);
    assert.ok(!html.includes('<a '), 'must not emit an anchor (no dead link)');
    assert.match(html, /Source pending/);
    assert.match(html, /card-link-pending/);
  }
});

// ── Data-contract checks on the shipped leaderboards object ──
test('new T2I/T2V/links tabs exist', () => {
  for (const key of ['arena_t2i', 'arena_video', 'links']) {
    assert.ok(leaderboards[key], `missing leaderboards.${key}`);
  }
});

test('structured-API tabs (swe, coding) exist and disable provider dots', () => {
  for (const key of ['swe', 'coding']) {
    const lb = leaderboards[key];
    assert.ok(lb, `missing leaderboards.${key}`);
    assert.strictEqual(lb.providerCol, -1, `${key} should set providerCol:-1`);
    assert.strictEqual(typeof lb.scoreCol, 'number', `${key}.scoreCol must be a number`);
    assert.ok(Array.isArray(lb.rows) && lb.rows.length > 0, `${key} needs seed rows`);
  }
});

test('arena tabs declare numeric column config', () => {
  for (const key of ['arena_image', 'arena_t2i', 'arena_video']) {
    const lb = leaderboards[key];
    for (const f of ['providerCol', 'scoreCol', 'scoreMax']) {
      assert.strictEqual(typeof lb[f], 'number', `${key}.${f} must be a number`);
    }
  }
});

test('every table row matches its column count', () => {
  for (const [key, lb] of Object.entries(leaderboards)) {
    if (!Array.isArray(lb.rows) || !Array.isArray(lb.cols)) continue;
    lb.rows.forEach((row, i) =>
      assert.strictEqual(row.length, lb.cols.length, `${key} row ${i} arity != cols`));
  }
});

test('every table row provider has a PROVIDER_COLORS entry', () => {
  for (const [key, lb] of Object.entries(leaderboards)) {
    if (!Array.isArray(lb.rows) || !Array.isArray(lb.cols)) continue;
    const { providerCol } = resolveLbColumns(lb, key);
    if (providerCol < 0) continue; // tabs without a provider column render no dots
    lb.rows.forEach((row) => {
      const provider = row[providerCol];
      assert.ok(PROVIDER_COLORS[provider], `no color for provider "${provider}" in ${key}`);
    });
  }
});

test('every table tab\'s score-column label has a glossary tooltip', () => {
  for (const [key, lb] of Object.entries(leaderboards)) {
    if (!Array.isArray(lb.cols)) continue;
    const { scoreCol } = resolveLbColumns(lb, key);
    if (scoreCol < 0) continue; // tabs without a primary score column
    const label = lb.cols[scoreCol];
    assert.ok(lbTooltip(label).length > 0, `no tooltip for score column "${label}" in ${key}`);
  }
});

test('links tab is well-formed with resolvable URLs', () => {
  const lb = leaderboards.links;
  assert.strictEqual(lb.type, 'links');
  assert.ok(Array.isArray(lb.groups) && lb.groups.length > 0);
  for (const g of lb.groups) {
    assert.strictEqual(typeof g.label, 'string');
    assert.ok(Array.isArray(g.items) && g.items.length > 0);
    for (const it of g.items) {
      assert.strictEqual(typeof it.name, 'string');
      assert.ok(/^https?:\/\//.test(it.url), `bad url: ${it.url}`);
    }
  }
});

test('reportSourceSealMarkup renders badge img with escaped attrs and tooltip', () => {
  const html = reportSourceSealMarkup({
    report_source_badge: '../../docs/img/llm_pipeline/llm_pipeline.png',
    report_source_label: 'LLM Pipeline',
  });
  assert.match(html, /src="\.\.\/\.\.\/docs\/img\/llm_pipeline\/llm_pipeline\.png"/);
  assert.match(html, /title="Produced by LLM Pipeline"/);
});

test('reportSourceSealMarkup returns empty without badge href', () => {
  assert.strictEqual(reportSourceSealMarkup({ report_source: 'llm-pipeline' }), '');
});
